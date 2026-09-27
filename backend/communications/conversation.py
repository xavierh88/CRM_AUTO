"""Conversation repository for multi-channel inbox."""
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import Channel, Conversation, Direction, Delivery, Message


async def create_conversation(
    db: AsyncIOMotorDatabase,
    customer_id: str,
    channel: Channel,
    assigned_to: str | None = None,
    metadata: dict | None = None,
) -> Conversation:
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=str(uuid4()),
        customer_id=customer_id,
        channel=channel,
        status='active',
        last_message='',
        last_message_at=now,
        unread_count=0,
        created_at=now,
        updated_at=now,
        assigned_to=assigned_to,
        metadata=metadata or {},
    )
    await db.conversations.insert_one(asdict(conv))
    return conv


async def get_conversation(db: AsyncIOMotorDatabase, conversation_id: str) -> Conversation | None:
    doc = await db.conversations.find_one({'id': conversation_id})
    if not doc:
        return None
    doc.pop('_id', None)
    return Conversation(**doc)


async def get_conversations(
    db: AsyncIOMotorDatabase,
    query: dict,
    sort: list[tuple[str, int]] | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[Conversation]:
    cursor = db.conversations.find(query).skip(skip).limit(limit)
    if sort:
        cursor = cursor.sort(sort)
    results = []
    async for doc in cursor:
        doc.pop('_id', None)
        results.append(Conversation(**doc))
    return results


async def update_conversation_last_message(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    last_message: str,
    last_message_at: datetime,
    direction: Direction,
    is_read: bool = False,
) -> None:
    update = {
        'last_message': last_message[:200],
        'last_message_at': last_message_at,
        'updated_at': last_message_at,
    }
    if direction == Direction.INBOUND and not is_read:
        await db.conversations.update_one(
            {'id': conversation_id},
            {'$set': update, '$inc': {'unread_count': 1}},
        )
    else:
        await db.conversations.update_one({'id': conversation_id}, {'$set': update})


async def mark_conversation_read(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
) -> None:
    await db.conversations.update_one(
        {'id': conversation_id},
        {'$set': {'unread_count': 0}},
    )


async def close_conversation(db: AsyncIOMotorDatabase, conversation_id: str) -> None:
    await db.conversations.update_one(
        {'id': conversation_id},
        {'$set': {'status': 'closed', 'updated_at': datetime.now(timezone.utc)}},
    )


async def get_or_create_conversation(
    db: AsyncIOMotorDatabase,
    customer_id: str,
    channel: Channel,
    assigned_to: str | None = None,
) -> Conversation:
    existing = await db.conversations.find_one(
        {'customer_id': customer_id, 'channel': channel.value, 'status': 'active'}
    )
    if existing:
        existing.pop('_id', None)
        return Conversation(**existing)
    return await create_conversation(db, customer_id, channel, assigned_to)


async def store_message(
    db: AsyncIOMotorDatabase,
    message: Message,
) -> None:
    doc = {
        'id': message.id,
        'conversation_id': message.metadata.get('conversation_id') if hasattr(message, 'metadata') else None,
        'customer_id': message.customer_id,
        'channel': message.channel.value,
        'direction': message.direction.value,
        'actor': message.actor.value,
        'text': message.text,
        'timestamp': message.timestamp,
        'delivery_status': message.delivery_status.value,
        'provider_message_id': message.provider_message_id,
        'created_at': datetime.now(timezone.utc),
    }
    await db.messages.insert_one(doc)


async def get_messages(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    limit: int = 100,
    before: datetime | None = None,
) -> list[dict]:
    query = {'conversation_id': conversation_id}
    if before:
        query['timestamp'] = {'$lt': before}
    cursor = db.messages.find(query).sort('timestamp', -1).limit(limit)
    results = []
    async for doc in cursor:
        doc.pop('_id', None)
        results.append(doc)
    return list(reversed(results))


async def count_unread_conversations(
    db: AsyncIOMotorDatabase,
    query: dict,
) -> int:
    return await db.conversations.count_documents({**query, 'unread_count': {'$gt': 0}})