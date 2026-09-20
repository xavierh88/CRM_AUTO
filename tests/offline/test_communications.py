"""Offline contract tests. All identifiers and content are synthetic."""
import unittest
from datetime import datetime, timedelta, timezone

from backend.communications.models import Actor, Channel, Delivery, Direction, Message
from backend.communications.adapters import AndroidSmsGateway, WhatsAppAdapter, SocialInboundAdapter
from backend.communications.service import CommunicationService
from backend.communications.policy import ContactPolicy
from backend.communications.prequalify import MockPrequalifyProvider
from backend.communications.handoff import WhatsAppHandoff

NOW = datetime(2026, 9, 20, 15, tzinfo=timezone.utc)


def message(**changes):
    values = dict(customer_id='synthetic-customer', channel=Channel.SMS,
                  direction=Direction.OUTBOUND, actor=Actor.HUMAN,
                  text='Synthetic message', timestamp=NOW, id='synthetic-message')
    values.update(changes)
    return Message(**values)


class CommunicationTests(unittest.TestCase):
    def test_message_validation(self):
        for changes in ({'text': ''}, {'timestamp': NOW.replace(tzinfo=None)},
                        {'actor': Actor.CLIENT}, {'channel': 'invalid'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                message(**changes)

    def test_gateway_health_boundaries_and_reordered_heartbeat(self):
        gateway = AndroidSmsGateway()
        self.assertEqual(gateway.health(NOW).state, 'OFFLINE')
        gateway.heartbeat(NOW)
        self.assertEqual(gateway.health(NOW).state, 'ONLINE')
        self.assertEqual(gateway.health(NOW + timedelta(seconds=60)).state, 'DEGRADED')
        self.assertEqual(gateway.health(NOW + timedelta(seconds=180)).state, 'OFFLINE')
        with self.assertRaises(ValueError):
            gateway.heartbeat(NOW - timedelta(seconds=1))
        gateway.heartbeat(NOW, last_error='synthetic failure')
        self.assertEqual(gateway.health(NOW).state, 'DEGRADED')
        gateway.heartbeat(NOW)
        self.assertIsNone(gateway.health(NOW).last_error)

    def test_offline_blocks_and_records_event(self):
        service = CommunicationService(AndroidSmsGateway())
        result = service.send(message(), ContactPolicy(consent=True), NOW)
        self.assertEqual(result.delivery_status, Delivery.BLOCKED)
        self.assertEqual(service.events[-1].reason, 'GATEWAY_OFFLINE')

    def test_mock_send_idempotency_and_cap(self):
        gateway = AndroidSmsGateway()
        gateway.heartbeat(NOW)
        service = CommunicationService(gateway)
        policy = ContactPolicy(consent=True, frequency_cap=1)
        first = service.send(message(), policy, NOW)
        self.assertEqual(first.delivery_status, Delivery.SIMULATED)
        self.assertEqual(service.send(message(), policy, NOW), first)
        with self.assertRaises(ValueError):
            service.send(message(text='different'), policy, NOW)
        second = service.send(message(id='second'), policy, NOW)
        self.assertEqual(second.delivery_status, Delivery.BLOCKED)
        self.assertEqual(service.events[-1].reason, 'FREQUENCY_CAP')

    def test_policy_boundaries(self):
        self.assertEqual(ContactPolicy().reason(NOW, []), 'CONSENT_REQUIRED')
        self.assertEqual(ContactPolicy(consent=True, opted_out=True).reason(NOW, []), 'OPTED_OUT')
        policy = ContactPolicy(consent=True, timezone_name='America/New_York')
        self.assertEqual(policy.reason(NOW.replace(hour=2), []), 'QUIET_HOURS')
        self.assertIsNone(policy.reason(NOW.replace(hour=12), []))
        self.assertIsNone(policy.reason(NOW, [NOW - timedelta(days=1)]))
        with self.assertRaises(ValueError):
            ContactPolicy(frequency_cap=0)

    def test_inbound_normalization_replay_and_stop(self):
        adapter = AndroidSmsGateway()
        payload = dict(provider_message_id='synthetic-inbound', text=' STOP ', timestamp=NOW.isoformat())
        service = CommunicationService(adapter)
        inbound = service.receive(payload, 'synthetic-customer')
        self.assertEqual(inbound.actor, Actor.CLIENT)
        self.assertEqual(inbound.direction, Direction.INBOUND)
        self.assertEqual(inbound.delivery_status, Delivery.RECEIVED)
        self.assertEqual(service.receive(payload, 'synthetic-customer'), inbound)
        adapter.heartbeat(NOW)
        result = service.send(message(), ContactPolicy(consent=True), NOW)
        self.assertEqual(result.delivery_status, Delivery.BLOCKED)
        self.assertEqual(service.events[-1].reason, 'OPTED_OUT')
        with self.assertRaises(ValueError):
            service.receive(dict(payload, text='conflicting replay'), 'synthetic-customer')
        with self.assertRaises(ValueError):
            adapter.normalize_inbound({'text': 'missing fields'}, 'synthetic-customer')

    def test_waiting_config_and_social_contract(self):
        adapter = WhatsAppAdapter()
        self.assertEqual(adapter.status, 'WAITING_CONFIG')
        service = CommunicationService(adapter)
        result = service.send(message(channel=Channel.WHATSAPP), ContactPolicy(consent=True), NOW)
        self.assertEqual(result.delivery_status, Delivery.BLOCKED)
        for channel in (Channel.FACEBOOK, Channel.INSTAGRAM):
            social = SocialInboundAdapter(channel)
            inbound = social.normalize_inbound(dict(provider_message_id='fake-social', text='Hello', timestamp=NOW.isoformat()), 'synthetic-customer')
            self.assertEqual(inbound.channel, channel)
            self.assertEqual(social.send(message(channel=channel), NOW).reason, 'INBOUND_ONLY')
        with self.assertRaises(ValueError):
            SocialInboundAdapter(Channel.SMS)

    def test_prequalify_never_claims_approval(self):
        provider = MockPrequalifyProvider()
        self.assertEqual(provider.submit('synthetic-customer', 'synthetic-request', True).status, 'PENDING_PROVIDER_INTEGRATION')
        with self.assertRaises(ValueError):
            provider.submit('synthetic-customer', 'synthetic-request', False)

    def test_human_takeover(self):
        handoff = WhatsAppHandoff()
        self.assertFalse(handoff.ai_allowed(NOW))
        handoff.inbound(NOW)
        self.assertFalse(handoff.ai_allowed(NOW + timedelta(seconds=59)))
        self.assertTrue(handoff.ai_allowed(NOW + timedelta(seconds=60)))
        handoff.human_takeover()
        self.assertFalse(handoff.ai_allowed(NOW + timedelta(hours=1)))
        handoff.inbound(NOW + timedelta(hours=2))
        self.assertFalse(handoff.ai_allowed(NOW + timedelta(hours=3)))

    def test_contract_rejections_and_channel_isolation(self):
        from backend.communications.adapters import MockProvider
        provider = MockProvider(Channel.EMAIL)
        service = CommunicationService(provider)
        with self.assertRaises(ValueError):
            service.send(message(), ContactPolicy(), NOW)
        with self.assertRaises(ValueError):
            provider.send(message(), NOW)
        with self.assertRaises(ValueError):
            service.send(message(channel=Channel.EMAIL, delivery_status=Delivery.SENT), ContactPolicy(), NOW)
        inbound = message(channel=Channel.EMAIL, direction=Direction.INBOUND,
                          actor=Actor.CLIENT, delivery_status=Delivery.RECEIVED)
        with self.assertRaises(ValueError):
            service.send(inbound, ContactPolicy(), NOW)
        for changes in ({'direction': Direction.INBOUND, 'actor': Actor.CLIENT},
                        {'delivery_status': Delivery.RECEIVED}, {'provider_message_id': ''}):
            with self.assertRaises(ValueError):
                message(**changes)
        result = service.send(message(channel=Channel.EMAIL), ContactPolicy(consent=True), NOW)
        self.assertEqual(result.delivery_status, Delivery.SIMULATED)
        self.assertEqual(len(service.messages), 1)

    def test_daytime_quiet_window_and_invalid_policy(self):
        policy = ContactPolicy(consent=True, quiet_start=12, quiet_end=16)
        self.assertEqual(policy.reason(NOW, []), 'QUIET_HOURS')
        self.assertIsNone(policy.reason(NOW.replace(hour=17), []))
        for changes in ({'consent': 'true'}, {'quiet_start': 24}, {'frequency_cap': True}):
            with self.assertRaises(ValueError):
                ContactPolicy(**changes)

    def test_gateway_future_heartbeat_and_degraded_send(self):
        gateway = AndroidSmsGateway()
        gateway.heartbeat(NOW)
        self.assertEqual(gateway.health(NOW - timedelta(seconds=1)).state, 'OFFLINE')
        self.assertEqual(gateway.send(message(), NOW + timedelta(seconds=60)).delivery_status, Delivery.SIMULATED)

    def test_handoff_release_and_reordered_events(self):
        with self.assertRaises(ValueError):
            WhatsAppHandoff(0)
        handoff = WhatsAppHandoff()
        handoff.inbound(NOW)
        with self.assertRaises(ValueError):
            handoff.inbound(NOW - timedelta(seconds=1))
        handoff.human_takeover()
        handoff.release_to_ai(NOW)
        self.assertTrue(handoff.ai_allowed(NOW + timedelta(seconds=60)))

    def test_mock_send_serializes_frequency_cap(self):
        from concurrent.futures import ThreadPoolExecutor
        gateway = AndroidSmsGateway()
        gateway.heartbeat(NOW)
        service = CommunicationService(gateway)
        policy = ContactPolicy(consent=True, frequency_cap=1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: service.send(message(id=f'concurrent-{i}'), policy, NOW), range(12)))
        self.assertEqual(sum(item.delivery_status == Delivery.SIMULATED for item in results), 1)
        self.assertEqual(len(service.events), 12)
