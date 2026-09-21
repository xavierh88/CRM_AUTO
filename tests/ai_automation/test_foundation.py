import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from pydantic import ValidationError
from backend.ai_automation.foundation import (
    Jarvis, MatchRequest, UpdateAppointment, match_vehicles, guardian, recovery,
)
from backend.commercial.inventory import mock_inventory, VehiclePreference


class FoundationTests(unittest.TestCase):
    def test_matching_filters_and_explains_pending_finance(self):
        result = match_vehicles(mock_inventory(), VehiclePreference(budget='23000', body_type='suv', payment_preference='300'))
        self.assertEqual([m.vehicle_id for m in result], ['mock-vehicle-2'])
        self.assertIn('FINANCING_REVIEW_REQUIRED', result[0].reasons)
        self.assertEqual(match_vehicles(mock_inventory(), VehiclePreference(budget='1')), ())

    def test_unavailable_and_year_filter(self):
        cars = mock_inventory()
        self.assertEqual(match_vehicles(cars, VehiclePreference(min_year=2030)), ())
        sold = cars[0].model_validate({**cars[0].model_dump(), 'availability': 'SOLD'})
        self.assertEqual(match_vehicles([sold], VehiclePreference()), ())

    def test_guardian_and_recovery(self):
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(guardian('SCHEDULED', now + timedelta(hours=1), now), 'REMIND')
        self.assertEqual(guardian('SCHEDULED', now - timedelta(hours=1), now), 'REVIEW_NO_SHOW')
        self.assertEqual(guardian('CANCELLED', now, now), 'NONE')
        self.assertEqual(recovery(now, no_show=True).priority, 'HOT')
        self.assertIn('NO_ACTIVITY', recovery(now).reasons)
        self.assertIn('STALE', recovery(now, last_activity=now-timedelta(days=20)).reasons)
        with self.assertRaises(ValueError):
            guardian('SCHEDULED', now.replace(tzinfo=None), now)

    def test_contract_rejects_authority_and_arbitrary_writes(self):
        for payload in [dict(tool='database_write', query={}), dict(tool='match_vehicle', role='admin'), dict(tool='update_appointment', appointment_id='x', status='DROP')]:
            with self.assertRaises(ValidationError):
                Jarvis.parse(payload)

    def test_permission_precedes_typed_api(self):
        events = []
        permissions = Mock()
        permissions.require.side_effect = lambda *a: events.append('permission')
        api = Mock()
        api.match_vehicle.side_effect = lambda *a: events.append('api') or ()
        audit = Mock()
        jarvis = Jarvis(permissions, api, audit)
        actor = object()
        jarvis.execute(actor, {'tool': 'match_vehicle'})
        self.assertEqual(events, ['permission', 'api'])
        permissions.require.assert_called_once_with(actor, MatchRequest())
        permissions.require.side_effect = PermissionError('Denied')
        with self.assertRaises(PermissionError):
            jarvis.execute(actor, {'tool': 'match_vehicle'})
        self.assertEqual(api.match_vehicle.call_count, 1)

    def test_mutation_requires_trusted_confirmation(self):
        permissions, api, audit = Mock(), Mock(), Mock()
        permissions.consume_confirmation.return_value = False
        jarvis = Jarvis(permissions, api, audit)
        payload = dict(tool='update_appointment', appointment_id='fictional', status='CANCELLED')
        with self.assertRaises(PermissionError):
            jarvis.execute(object(), payload)
        api.update_appointment.assert_not_called()
        permissions.consume_confirmation.return_value = True
        jarvis.execute(object(), payload)
        api.update_appointment.assert_called_once()
        self.assertIsInstance(api.update_appointment.call_args.args[1], UpdateAppointment)

    def test_audit_failure_blocks_execution(self):
        audit = Mock(side_effect=RuntimeError('audit unavailable'))
        api = Mock()
        with self.assertRaises(RuntimeError):
            Jarvis(Mock(), api, audit).execute(object(), {'tool': 'match_vehicle'})
        api.match_vehicle.assert_not_called()

    def test_permission_engine_scopes_and_consumes_exact_intent(self):
        from backend.ai_automation.foundation import PermissionEngine, TrustedContext
        context = TrustedContext('fictional-user', 'fictional-tenant', 'session',
                                 frozenset({('update_appointment', 'a')}))
        engine = PermissionEngine()
        request = UpdateAppointment(appointment_id='a', status='CANCELLED')
        engine.require(context, request)
        with self.assertRaises(PermissionError):
            engine.require(context, UpdateAppointment(appointment_id='b', status='CANCELLED'))
        self.assertFalse(engine.consume_confirmation(context, request))
        engine.confirm(context, request)
        self.assertTrue(engine.consume_confirmation(context, request))
        self.assertFalse(engine.consume_confirmation(context, request))
        with self.assertRaises(PermissionError):
            engine.require({}, request)

    def test_remaining_recommendations_and_failures(self):
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(guardian('NO_SHOW', now, now), 'RECOVERY_REVIEW')
        self.assertEqual(guardian('SCHEDULED', now+timedelta(days=2), now), 'NONE')
        self.assertEqual(recovery(now, last_activity=now).action, 'NONE')
        with self.assertRaises(ValueError):
            guardian('unknown', now, now)
        with self.assertRaises(ValueError):
            recovery(now, no_reply='true')
        with self.assertRaises(ValueError):
            recovery(now, last_activity=now+timedelta(days=1))
        self.assertEqual(match_vehicles(mock_inventory(), VehiclePreference(max_year=1900)), ())
        api, audit = Mock(), Mock()
        api.match_vehicle.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            Jarvis(Mock(), api, audit).execute(object(), {'tool': 'match_vehicle'})
        self.assertEqual(audit.call_args.args[2], 'FAILED_REQUIRES_REVIEW')

    def test_confirmation_expiry_and_binding(self):
        from backend.ai_automation.foundation import PermissionEngine, TrustedContext
        clock = Mock(return_value=0)
        engine = PermissionEngine(clock)
        grants = frozenset({('update_appointment', 'a')})
        actor = TrustedContext('u', 't', 's', grants)
        other = TrustedContext('u', 'other-tenant', 's', grants)
        request = UpdateAppointment(appointment_id='a', status='CANCELLED')
        engine.confirm(actor, request)
        self.assertFalse(engine.consume_confirmation(other, request))
        self.assertFalse(engine.consume_confirmation(actor, UpdateAppointment(appointment_id='a', status='CONFIRMED')))
        clock.return_value = 120
        self.assertFalse(engine.consume_confirmation(actor, request))
