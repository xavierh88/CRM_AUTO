"""In-memory mock orchestration. Construct one instance per tenant/provider.

The integrator supplies authorized customer IDs; this is not an HTTP/auth boundary.
"""
from dataclasses import replace
from datetime import datetime
from threading import RLock
from typing import Mapping

from .adapters import CommunicationProvider
from .models import CommunicationEvent, Delivery, Direction, Message, aware
from .policy import ContactPolicy


class CommunicationService:
    def __init__(self, provider: CommunicationProvider):
        self.provider = provider
        self._messages: dict[str, Message] = {}
        self._requests: dict[str, Message] = {}
        self._opted_out: set[str] = set()
        self._events: list[CommunicationEvent] = []
        self._lock = RLock()

    @property
    def messages(self) -> tuple[Message, ...]:
        with self._lock:
            return tuple(self._messages.values())

    @property
    def events(self) -> tuple[CommunicationEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def send(self, message: Message, policy: ContactPolicy, now: datetime) -> Message:
        aware(now)
        if message.direction != Direction.OUTBOUND or message.channel != self.provider.channel:
            raise ValueError('Outbound message must match provider channel')
        if message.delivery_status != Delivery.QUEUED or message.provider_message_id is not None:
            raise ValueError('New outbound request must be QUEUED without provider ID')
        with self._lock:
            if message.id in self._requests:
                if self._requests[message.id] != message:
                    raise ValueError('Idempotency key reused with different request')
                return self._messages[message.id]
            if message.id in self._messages:
                raise ValueError('Message ID collision')
            policy = replace(policy, opted_out=policy.opted_out or message.customer_id in self._opted_out)
            history = [item.timestamp for item in self._messages.values()
                       if item.customer_id == message.customer_id
                       and item.delivery_status in (Delivery.SIMULATED, Delivery.SENT, Delivery.DELIVERED)]
            reason = policy.reason(now, history)
            if reason:
                result = replace(message, timestamp=now, delivery_status=Delivery.BLOCKED)
            else:
                response = self.provider.send(message, now)
                reason = response.reason
                result = replace(message, timestamp=now, delivery_status=response.delivery_status,
                                 provider_message_id=response.provider_message_id)
            self._requests[message.id] = message
            self._messages[message.id] = result
            self._events.append(CommunicationEvent(message.id, now, reason or result.delivery_status.value))
            return result

    def receive(self, payload: Mapping, customer_id: str) -> Message:
        message = self.provider.normalize_inbound(payload, customer_id)
        with self._lock:
            if message.id in self._messages:
                if self._messages[message.id] != message:
                    raise ValueError('Conflicting inbound replay')
                return self._messages[message.id]
            self._messages[message.id] = message
            if message.text.strip().upper() in {'STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT'}:
                self._opted_out.add(customer_id)
            self._events.append(CommunicationEvent(message.id, message.timestamp, 'RECEIVED'))
            return message
