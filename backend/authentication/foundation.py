"""Offline foundation. Actor facts must come from a trusted host, never request JSON."""
from dataclasses import dataclass
import math
import re
import secrets
from threading import Lock
import time

import bcrypt


def _password_bytes(password):
    try:
        encoded = password.encode('utf-8') if isinstance(password, str) else b''
    except UnicodeError:
        raise ValueError('Invalid password') from None
    # Existing bcrypt hashes must never silently truncate a supplied password.
    if not 1 <= len(encoded) <= 72:
        raise ValueError('Password must contain 1 to 72 UTF-8 bytes')
    return encoded


def hash_password(password):
    """Legacy-compatible hashing; enrollment strength is a separate host policy."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=12)).decode('ascii')


def verify_password(password, encoded_hash):
    """Corrupt, unsupported, or oversized values fail closed without bcrypt truncation."""
    try:
        raw = _password_bytes(password)
        if not isinstance(encoded_hash, str) or not re.fullmatch(
                r'\$2[aby]\$(0[4-9]|1[0-4])\$[./A-Za-z0-9]{53}', encoded_hash):
            return False
        return bcrypt.checkpw(raw, encoded_hash.encode('ascii'))
    except (ValueError, TypeError, UnicodeError):
        return False


class PasskeysPending(RuntimeError):
    pass


def passkey_options():
    return {'status': 'PENDING_EXTERNAL', 'available': False, 'password_fallback': True}


def verify_passkey(response):
    """No input inspection, persistence, or simulated successful authentication."""
    raise PasskeysPending('WebAuthn verifier integration is pending')


@dataclass(frozen=True)
class Actor:
    user_id: str
    tenant_id: str
    session_id: str
    role: str
    active: bool
    human: bool
    reauthenticated_at: float | None


@dataclass(frozen=True)
class _Preview:
    binding: tuple
    created_at: float


class ConfirmationGate:
    """Bounded process-local one-shot intent gate; never executes an action.

    Trusted host owns role, session, reauthentication, target authorization and
    human confirmation. A ticket is a binding token, not proof of authentication.
    """
    _roles = {'manage_users': frozenset({'admin'}),
              'edit_schema': frozenset({'SYSTEM_DEVELOPER'}),
              'manage_passkeys': frozenset({'admin', 'bdc_manager', 'bdc',
                                           'salesperson', 'telemarketer',
                                           'SYSTEM_DEVELOPER'})}

    def __init__(self, *, clock=time.time, capacity=1000):
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError('Invalid preview capacity')
        self._clock = clock
        self._capacity = capacity
        self._pending = {}
        self._lock = Lock()

    def _authorize(self, actor, action, now):
        if not isinstance(actor, Actor):
            raise PermissionError('Verified actor required')
        if (not all(isinstance(value, str) and 0 < len(value) <= 256 for value in
                    (actor.user_id, actor.tenant_id, actor.session_id, actor.role))
                or actor.active is not True or actor.human is not True
                or not isinstance(action, str)
                or actor.role not in self._roles.get(action, ())
                or type(actor.reauthenticated_at) not in (int, float)
                or not math.isfinite(actor.reauthenticated_at)
                or not math.isfinite(now)
                or not 0 <= now - actor.reauthenticated_at < 300):
            raise PermissionError('Permission and recent human reauthentication required')

    def _binding(self, actor, action, target, digest):
        if (not isinstance(target, str) or not 0 < len(target) <= 256
                or not isinstance(digest, str)
                or not re.fullmatch('[a-f0-9]{64}', digest)
                or (action == 'manage_passkeys' and target != actor.user_id)):
            raise PermissionError('Invalid action binding')
        return (actor.user_id, actor.tenant_id, actor.session_id, actor.role,
                action, target, digest)

    def preview(self, actor, action, target, digest):
        with self._lock:
            now = self._clock()
            self._authorize(actor, action, now)
            binding = self._binding(actor, action, target, digest)
            self._pending = {key: value for key, value in self._pending.items()
                             if 0 <= now - value.created_at < 300}
            if len(self._pending) >= self._capacity:
                raise PermissionError('Preview capacity exceeded')
            ticket = secrets.token_urlsafe(32)
            self._pending[ticket] = _Preview(binding, now)
            return ticket

    def confirm(self, actor, ticket, action, target, digest, *, human_confirmed):
        with self._lock:
            now = self._clock()
            self._authorize(actor, action, now)
            binding = self._binding(actor, action, target, digest)
            preview = self._pending.get(ticket) if isinstance(ticket, str) else None
            if (human_confirmed is not True or preview is None
                    or preview.binding != binding
                    or not 0 <= now - preview.created_at < 300):
                raise PermissionError('Confirmation denied')
            del self._pending[ticket]
