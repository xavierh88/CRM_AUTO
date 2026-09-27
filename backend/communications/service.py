"""Communication orchestration. Supports both in-memory mock (legacy) and DB-backed modes."""
from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping, Union, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .adapters import CommunicationProvider, get_provider
from .conversation import (
    create_conversation,
    get_or_create_conversation,
    mark_conversation_read,
    store_message,
    update_conversation_last_message,
)
from .models import (
    Actor,
    Channel,
    CommunicationEvent,
    Delivery,
    Direction,
    Message,
    aware,
)
from .policy import ContactPolicy


class CommunicationService:
    """
    Construct one instance per tenant/provider.
    
    Legacy API: CommunicationService(provider) - for in-memory mock testing
    New API: CommunicationService(db, channel) - for database-backed operations
    """
    def __init__(self, db_or_provider: Union[AsyncIOMotorDatabase, CommunicationProvider], channel: Optional[Channel] = None):
        # Legacy mode: first arg is a CommunicationProvider (duck typing)
        # Check if it has the provider methods
        if hasattr(db_or_provider, 'send') and hasattr(db_or_provider, 'normalize_inbound'):
            self._legacy_mode = True
            self.provider = db_or_provider
            self.channel = channel or getattr(db_or_provider, 'channel', Channel.SMS)
            self._messages: dict[str, Message] = {}
            self._requests: dict[str, Message] = {}
            self._opted_out: set[str] = set()
            self._events: list[CommunicationEvent] = []
        else:
            # New mode: first arg is AsyncIOMotorDatabase
            self._legacy_mode = False
            self.db = db_or_provider
            self.channel = channel
            self.provider = get_provider(channel)

    # Legacy in-memory methods
    @property
    def messages(self) -> tuple[Message, ...]:
        if not self._legacy_mode:
            raise RuntimeError("messages property only available in legacy mode")
        return tuple(self._messages.values())

    @property
    def events(self) -> tuple[CommunicationEvent, ...]:
        if not self._legacy_mode:
            raise RuntimeError("events property only available in legacy mode")
        return tuple(self._events)

    def send(self, message: Message, policy: ContactPolicy, now: datetime) -> Message:
        """Legacy in-memory send method."""
        if not self._legacy_mode:
            raise RuntimeError("Use async send() method in new mode")
        aware(now)
        if message.direction != Direction.OUTBOUND or message.channel != self.provider.channel:
            raise ValueError('Outbound message must match provider channel')
        if message.delivery_status != Delivery.QUEUED or message.provider_message_id is not None:
            raise ValueError('New outbound request must be QUEUED without provider ID')
        
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
        """Legacy in-memory receive method."""
        if not self._legacy_mode:
            raise RuntimeError("Use async receive() method in new mode")
        message = self.provider.normalize_inbound(payload, customer_id)
        if message.id in self._messages:
            if self._messages[message.id] != message:
                raise ValueError('Conflicting inbound replay')
            return self._messages[message.id]
        self._messages[message.id] = message
        if message.text.strip().upper() in {'STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT'}:
            self._opted_out.add(customer_id)
        self._events.append(CommunicationEvent(message.id, message.timestamp, 'RECEIVED'))
        return message

    # New async database-backed methods
    async def async_send(
        self,
        customer_id: str,
        text: str,
        actor: Actor,
        assigned_to: str | None = None,
        policy: ContactPolicy | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        if self._legacy_mode:
            raise RuntimeError("Use legacy send() method in legacy mode")
        now = datetime.now(timezone.utc)
        aware(now)

        if policy is None:
            policy = ContactPolicy(consent=True)

        conversation = await get_or_create_conversation(
            self.db, customer_id, self.channel, assigned_to
        )

        message = Message(
            customer_id=customer_id,
            channel=self.channel,
            direction=Direction.OUTBOUND,
            actor=actor,
            text=text,
            timestamp=now,
            delivery_status=Delivery.QUEUED,
        )
        if idempotency_key:
            message = replace(message, id=idempotency_key)

        existing = await self.db.messages.find_one({'id': message.id})
        if existing:
            existing.pop('_id', None)
            return Message(**existing)

        policy = replace(policy, opted_out=policy.opted_out)
        history_cursor = self.db.messages.find({
            'customer_id': customer_id,
            'channel': self.channel.value,
            'delivery_status': {'$in': [Delivery.SIMULATED.value, Delivery.SENT.value, Delivery.DELIVERED.value]},
        })
        history = [doc['timestamp'] async for doc in history_cursor]

        reason = policy.reason(now, history)
        if reason:
            result = replace(message, timestamp=now, delivery_status=Delivery.BLOCKED)
        else:
            response = self.provider.send(message, now)
            reason = response.reason
            result = replace(message, timestamp=now, delivery_status=response.delivery_status,
                             provider_message_id=response.provider_message_id)

        await store_message(self.db, result)
        await update_conversation_last_message(
            self.db, conversation.id, text[:200], now, Direction.OUTBOUND
        )
        await self.db.events.insert_one({
            'message_id': result.id,
            'timestamp': now,
            'reason': reason or result.delivery_status.value,
        })
        return result

    async def async_receive(self, payload: Mapping, customer_id: str, assigned_to: str | None = None) -> Message:
        if self._legacy_mode:
            raise RuntimeError("Use legacy receive() method in legacy mode")
        message = self.provider.normalize_inbound(payload, customer_id)
        existing = await self.db.messages.find_one({'id': message.id})
        if existing:
            existing.pop('_id', None)
            return Message(**existing)

        conversation = await get_or_create_conversation(
            self.db, customer_id, self.channel, assigned_to
        )
        message = replace(message, metadata={'conversation_id': conversation.id})

        await store_message(self.db, message)
        is_read = False
        await update_conversation_last_message(
            self.db, conversation.id, message.text[:200], message.timestamp,
            Direction.INBOUND, is_read
        )
        if message.text.strip().upper() in {'STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT'}:
            await self.db.opt_outs.insert_one({
                'customer_id': customer_id,
                'channel': self.channel.value,
                'created_at': datetime.now(timezone.utc),
            })
        await self.db.events.insert_one({
            'message_id': message.id,
            'timestamp': message.timestamp,
            'reason': 'RECEIVED',
        })
        return message

    async def mark_read(self, conversation_id: str) -> None:
        if self._legacy_mode:
            raise RuntimeError("Not available in legacy mode")
        await mark_conversation_read(self.db, conversation_id)
        await self.db.messages.update_many(
            {'conversation_id': conversation_id, 'direction': Direction.INBOUND.value},
            {'$set': {'delivery_status': Delivery.READ.value}},
        )

    async def get_conversation_messages(self, conversation_id: str, limit: int = 100, before: datetime | None = None):
        if self._legacy_mode:
            raise RuntimeError("Not available in legacy mode")
        from .conversation import get_messages
        return await get_messages(self.db, conversation_id, limit, before)

    async def get_conversations(self, query: dict, sort: list = None, limit: int = 100, skip: int = 0):
        if self._legacy_mode:
            raise RuntimeError("Not available in legacy mode")
        from .conversation import get_conversations
        return await get_conversations(self.db, query, sort, limit, skip)

    async def count_unread(self, query: dict) -> int:
        if self._legacy_mode:
            raise RuntimeError("Not available in legacy mode")
        from .conversation import count_unread_conversations
        return await count_unread_conversations(self.db, query)