"""Expiring public appointment capabilities; no legacy token fallback."""
from datetime import datetime, timezone
import re
from fastapi import HTTPException


async def resolve_appointment_token(db, token, now=None):
    def invalid():
        return HTTPException(404, 'Appointment link invalid or expired')
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise invalid()
    link = await db.public_links.find_one({'token': token, 'link_type': 'appointment'}, {'_id': 0})
    if not link or link.get('link_type') != 'appointment' or link.get('revoked') or link.get('used'):
        raise invalid()
    try:
        expiry = datetime.fromisoformat(link['expires_at'].replace('Z', '+00:00'))
        if expiry.tzinfo is None or expiry <= (now or datetime.now(timezone.utc)):
            raise invalid()
    except (KeyError, ValueError, TypeError, AttributeError):
        raise invalid()
    if not all(isinstance(link.get(key), str) and link[key] for key in ('record_id', 'client_id')):
        raise invalid()
    appointment = await db.appointments.find_one({'id': link['record_id']}, {'_id': 0})
    if (not appointment or appointment.get('is_deleted') or appointment.get('client_id') != link['client_id']
            or appointment.get('public_token') != token):
        raise invalid()
    client = await db.clients.find_one({'id': link['client_id'], 'is_deleted': {'$ne': True}}, {'id': 1})
    if not client:
        raise invalid()
    return appointment
