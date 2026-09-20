"""Mock adapters only. Payloads are internal contracts, not vendor webhook schemas."""
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol

from .models import Actor, Channel, Delivery, Direction, Message, SendResult, aware, required


class CommunicationProvider(Protocol):
    name: str
    channel: Channel
    status: str

    def send(self, message: Message, now: datetime) -> SendResult: ...
    def normalize_inbound(self, payload: Mapping, customer_id: str) -> Message: ...


class MockProvider:
    status = 'MOCK'

    def __init__(self, channel: Channel = Channel.SMS):
        self.channel = Channel(channel)
        self.name = f'mock-{self.channel.value.lower()}'

    def send(self, message: Message, now: datetime) -> SendResult:
        aware(now)
        if message.channel != self.channel or message.direction != Direction.OUTBOUND:
            raise ValueError('Provider channel/outbound mismatch')
        return SendResult(Delivery.SIMULATED, f'{self.name}:{message.id}')

    def normalize_inbound(self, payload: Mapping, customer_id: str) -> Message:
        try:
            provider_id = payload['provider_message_id']
            required(provider_id)
            timestamp = datetime.fromisoformat(payload['timestamp'])
            return Message(customer_id=customer_id, channel=self.channel,
                           direction=Direction.INBOUND, actor=Actor.CLIENT,
                           text=payload['text'], timestamp=timestamp,
                           delivery_status=Delivery.RECEIVED,
                           provider_message_id=provider_id,
                           id=f'{self.name}:{provider_id}')
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid normalized inbound payload') from error


@dataclass(frozen=True)
class GatewayHealth:
    state: str
    last_seen: datetime | None
    last_error: str | None
    provider_status: str = 'MOCK'


class AndroidSmsGateway(MockProvider):
    """Fresh <60s, degraded <180s, offline thereafter; no heartbeat means offline."""
    def __init__(self):
        super().__init__(Channel.SMS)
        self.name = 'mock-android-sms'
        self._last_seen = None
        self._last_error = None

    def heartbeat(self, timestamp: datetime, *, last_error: str | None = None):
        aware(timestamp)
        if self._last_seen is not None and timestamp < self._last_seen:
            raise ValueError('Out-of-order heartbeat')
        self._last_seen = timestamp
        self._last_error = last_error

    def health(self, now: datetime) -> GatewayHealth:
        aware(now)
        age = (now - self._last_seen).total_seconds() if self._last_seen else None
        if age is None or age < 0 or age >= 180:
            state = 'OFFLINE'
        elif age >= 60 or self._last_error:
            state = 'DEGRADED'
        else:
            state = 'ONLINE'
        return GatewayHealth(state, self._last_seen, self._last_error)

    def send(self, message: Message, now: datetime) -> SendResult:
        if self.health(now).state == 'OFFLINE':
            return SendResult(Delivery.BLOCKED, reason='GATEWAY_OFFLINE')
        return super().send(message, now)


class WhatsAppAdapter(MockProvider):
    status = 'WAITING_CONFIG'

    def __init__(self):
        super().__init__(Channel.WHATSAPP)

    def send(self, message: Message, now: datetime) -> SendResult:
        return SendResult(Delivery.BLOCKED, reason=self.status)


class SocialInboundAdapter(MockProvider):
    status = 'PENDING_EXTERNAL'

    def __init__(self, channel: Channel):
        if channel not in (Channel.FACEBOOK, Channel.INSTAGRAM):
            raise ValueError('Unsupported social channel')
        super().__init__(channel)

    def send(self, message: Message, now: datetime) -> SendResult:
        return SendResult(Delivery.BLOCKED, reason='INBOUND_ONLY')
