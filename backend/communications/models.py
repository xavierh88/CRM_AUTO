"""Provider-independent, immutable communication records; no application imports."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4
from dataclasses import field


class Channel(StrEnum):
    SMS = 'SMS'
    WHATSAPP = 'WHATSAPP'
    EMAIL = 'EMAIL'
    FACEBOOK = 'FACEBOOK'
    INSTAGRAM = 'INSTAGRAM'


class Actor(StrEnum):
    CLIENT = 'CLIENT'
    HUMAN = 'HUMAN'
    AI = 'AI'
    SYSTEM = 'SYSTEM'


class Direction(StrEnum):
    INBOUND = 'INBOUND'
    OUTBOUND = 'OUTBOUND'


class Delivery(StrEnum):
    RECEIVED = 'RECEIVED'
    QUEUED = 'QUEUED'
    SENT = 'SENT'
    DELIVERED = 'DELIVERED'
    FAILED = 'FAILED'
    BLOCKED = 'BLOCKED'
    SIMULATED = 'SIMULATED'


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('Timezone-aware datetime required')


def required(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Nonempty string required')


@dataclass(frozen=True)
class Message:
    customer_id: str
    channel: Channel
    direction: Direction
    actor: Actor
    text: str
    timestamp: datetime
    delivery_status: Delivery = Delivery.QUEUED
    provider_message_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        for value in (self.customer_id, self.text, self.id):
            required(value)
        aware(self.timestamp)
        for name, enum in (('channel', Channel), ('direction', Direction),
                           ('actor', Actor), ('delivery_status', Delivery)):
            object.__setattr__(self, name, enum(getattr(self, name)))
        if (self.direction == Direction.INBOUND) != (self.actor == Actor.CLIENT):
            raise ValueError('Inbound actor must be CLIENT; outbound actor cannot be CLIENT')
        if self.direction == Direction.INBOUND and self.delivery_status != Delivery.RECEIVED:
            raise ValueError('Inbound message must be RECEIVED')
        if self.direction == Direction.OUTBOUND and self.delivery_status == Delivery.RECEIVED:
            raise ValueError('Outbound message cannot be RECEIVED')
        if self.provider_message_id is not None:
            required(self.provider_message_id)


@dataclass(frozen=True)
class SendResult:
    delivery_status: Delivery
    provider_message_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CommunicationEvent:
    message_id: str
    timestamp: datetime
    reason: str
