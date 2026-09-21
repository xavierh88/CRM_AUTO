"""Shared runtime boundary. Construction performs no I/O or configuration loading."""
import hashlib
import hmac
from pymongo import ReturnDocument
import secrets
import time

from fastapi import HTTPException
import jwt

from authentication.foundation import verify_password
from runtime_security import require_enabled_user

# Public dummy bcrypt value; never an account credential.
_DUMMY = '$2b$12$rPbNRvrPwoVVtQrdIRhd8OwI2XUIdoC6upxDlkWvGcTNzZGuOOvia'
_PUBLIC = ('id', 'email', 'name', 'role', 'phone', 'created_at', 'is_active', 'approved')


class SessionAuth:
    def __init__(self, db, secret, *, hours=24, clock=time.time):
        self.db, self.secret, self.hours, self.clock = db, secret, hours, clock

    async def event(self, outcome, user_id=None):
        # Fixed vocabulary and server-resolved IDs only; no submitted identifiers,
        # passwords, raw bearer tokens, hashes or biometric payloads.
        await self.db.auth_events.insert_one({
            'event': outcome, 'user_id': user_id, 'at': self.clock()})

    async def throttle(self, scope, identifier):
        # HMAC prevents offline enumeration of identifiers from attempt records.
        bucket = int(self.clock() // 300)
        key = hmac.new(self.secret.encode(), f'{scope}:{identifier}:{bucket}'.encode(),
                       hashlib.sha256).hexdigest()
        record = await self.db.auth_attempts.find_one_and_update(
            {'_id': key}, {'$inc': {'count': 1},
                          '$setOnInsert': {'expires_at': (bucket + 1) * 300}},
            upsert=True, return_document=ReturnDocument.AFTER)
        if record['count'] > 10:
            raise HTTPException(429, 'Too many authentication attempts')

    async def login(self, identifier, password):
        await self.throttle('login', identifier)
        user = await self.db.users.find_one({'email': identifier}, {'_id': 0})
        if not verify_password(password, user.get('password', '') if user else _DUMMY):
            await self.event('login_denied')
            raise HTTPException(401, 'Invalid credentials')
        try:
            require_enabled_user(user)
        except HTTPException:
            await self.event('login_denied', user['id'])
            raise
        now = self.clock()
        sid = secrets.token_urlsafe(32)
        token = jwt.encode({'user_id': user['id'], 'sid': sid, 'iat': now,
                            'exp': now + self.hours * 3600}, self.secret, algorithm='HS256')
        # Session lifecycle audit lives in the same atomic document as state.
        await self.db.auth_sessions.insert_one({
            '_id': self.session_key(sid), 'user_id': user['id'], 'created_at': now,
            'expires_at': now + self.hours * 3600, 'revoked_at': None,
            'reauthenticated_at': None})
        return {'token': token, 'user': {k: user[k] for k in _PUBLIC if k in user}}

    @staticmethod
    def session_key(sid):
        return hashlib.sha256(sid.encode()).hexdigest()

    async def session(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'],
                                 options={'require': ['exp', 'user_id', 'sid']})
            if any(not isinstance(payload[k], str) or not 1 <= len(payload[k]) <= 256
                   for k in ('user_id', 'sid')):
                raise ValueError()
        except (jwt.InvalidTokenError, ValueError):
            raise HTTPException(401, 'Invalid or expired session') from None
        session = await self.db.auth_sessions.find_one({
            '_id': self.session_key(payload['sid']), 'user_id': payload['user_id'],
            'revoked_at': None})
        if not session or not self.clock() < session['expires_at']:
            raise HTTPException(401, 'Invalid or expired session')
        return session

    async def current_user(self, token):
        session = await self.session(token)
        user = await self.db.users.find_one({'id': session['user_id']}, {'_id': 0, 'password': 0})
        require_enabled_user(user)
        return {k: user[k] for k in _PUBLIC if k in user}

    async def logout(self, token):
        session = await self.session(token)
        await self.db.auth_sessions.update_one({'_id': session['_id'], 'revoked_at': None},
                                               {'$set': {'revoked_at': self.clock()}})
        return {'status': 'logged_out'}

    async def reauthenticate(self, token, password):
        session = await self.session(token)
        user = await self.db.users.find_one({'id': session['user_id']}, {'_id': 0})
        require_enabled_user(user)
        await self.throttle('reauthentication', user['id'])
        if not verify_password(password, user.get('password', '')):
            await self.event('reauthentication_denied', user['id'])
            raise HTTPException(401, 'Invalid credentials')
        result = await self.db.auth_sessions.update_one(
            {'_id': session['_id'], 'revoked_at': None},
            {'$set': {'reauthenticated_at': self.clock()}})
        if result.matched_count != 1:
            raise HTTPException(401, 'Session revoked')
        return {'status': 'reauthenticated', 'method': 'password'}
