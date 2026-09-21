"""Real HTTP handlers isolated from startup, configuration and providers."""
import ast
import asyncio
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import json
import pytest
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from authentication.foundation import hash_password
from authentication.runtime import SessionAuth

class HTTPClient:
    def __init__(self, app):
        self.app = app

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def request(self, method, path, headers=None, json=None):
        import json as codec
        body = codec.dumps(json).encode() if json is not None else b''
        messages = []
        async def receive():
            return {'type':'http.request', 'body':body, 'more_body':False}
        async def send(message):
            messages.append(message)
        scope = {'type':'http', 'asgi':{'version':'3.0'}, 'http_version':'1.1',
                 'method':method, 'path':path, 'raw_path':path.encode(), 'query_string':b'',
                 'scheme':'http', 'server':('test',80), 'client':('127.0.0.1',123),
                 'headers':[(k.lower().encode(),v.encode()) for k,v in
                            {'content-type':'application/json', **(headers or {})}.items()]}
        await self.app(scope, receive, send)
        data = b''.join(m.get('body',b'') for m in messages)
        return SimpleNamespace(status_code=messages[0]['status'], json=lambda:codec.loads(data))

    async def get(self, path, **kwargs):
        return await self.request('GET', path, **kwargs)

    async def post(self, path, **kwargs):
        return await self.request('POST', path, **kwargs)


class Collection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, row):
        self.rows.append(copy.deepcopy(row))

    async def find_one(self, query, projection=None):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                return copy.deepcopy(row)

    async def find_one_and_update(self, query, update, **kwargs):
        row = next((row for row in self.rows if row['_id'] == query['_id']), None)
        if row is None:
            row = {**query, **update['$setOnInsert'], 'count': 0}
            self.rows.append(row)
        row['count'] += update['$inc']['count']
        return copy.deepcopy(row)

    async def update_one(self, query, update):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                row.update(update.get('$set', {}))
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)

@pytest.fixture
def runtime():
    db = SimpleNamespace(users=Collection(), auth_sessions=Collection(), auth_events=Collection(), auth_attempts=Collection())
    db.users.rows.append(dict(id='synthetic', email='synthetic', password=hash_password('test-password'),
                              role='admin', is_active=True, name='Synthetic', created_at='2026-01-01'))
    return SessionAuth(db, 'synthetic-signing-key-' * 3), db


def app_for(auth):
    source = Path('backend/server.py').read_text()
    tree = ast.parse(source)
    names = {'UserCreate', 'register', 'hash_password', 'UserLogin', 'UserResponse', 'Reauthentication', 'get_current_user', 'login',
             'get_me', 'logout', 'reauthenticate', 'get_passkey_options', 'get_users'}
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef)) and n.name in names]
    from pydantic import ConfigDict, EmailStr
    from datetime import datetime, timezone
    import uuid
    from typing import Optional, List
    ns = dict(EmailStr=EmailStr, datetime=datetime, timezone=timezone, uuid=uuid,
              hash_password=hash_password, safe_hash_password=hash_password, BaseModel=BaseModel, ConfigDict=ConfigDict, Optional=Optional, List=List,
              Depends=Depends, HTTPException=HTTPException, HTTPAuthorizationCredentials=HTTPAuthorizationCredentials,
              security=HTTPBearer(), api_router=APIRouter(prefix='/api'), session_auth=auth, db=auth.db)
    from authentication.foundation import passkey_options
    ns['passkey_options'] = passkey_options
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'runtime-handlers', 'exec'), ns)
    app = FastAPI()
    app.include_router(ns['api_router'])
    return app


def test_http_session_lifecycle(runtime):
    auth, db = runtime
    async def scenario():
        async with HTTPClient(app_for(auth)) as c:
            assert (await c.get('/api/auth/me')).status_code in (401, 403)
            for password in ('wrong', 'x' * 73):
                assert (await c.post('/api/auth/login', json={'email':'synthetic','password':password})).status_code == 401
            r = await c.post('/api/auth/login', json={'email':'synthetic','password':'test-password'})
            assert r.status_code == 200
            assert 'password' not in r.json()['user']
            token = r.json()['token']
            headers = {'Authorization': 'Bearer ' + token}
            assert (await c.get('/api/auth/me', headers=headers)).status_code == 200
            db.users.rows[0]['role'] = 'salesperson'
            assert (await c.get('/api/users', headers=headers)).status_code == 403
            assert (await c.post('/api/auth/reauthenticate', headers=headers, json={'password':'wrong'})).status_code == 401
            assert (await c.post('/api/auth/reauthenticate', headers=headers, json={'password':'test-password'})).status_code == 200
            assert (await c.get('/api/auth/passkeys/options')).json()['status'] == 'PENDING_EXTERNAL'
            assert (await c.post('/api/auth/logout', headers=headers)).status_code == 200
            assert (await c.get('/api/auth/me', headers=headers)).status_code == 401
            assert token not in repr(db.auth_sessions.rows) + repr(db.auth_events.rows)
    asyncio.run(scenario())


def test_revocation_expiry_and_legacy_tokens(runtime):
    auth, db = runtime
    import jwt
    async def scenario():
        result = await auth.login('synthetic', 'test-password')
        token = result['token']
        db.users.rows[0]['is_active'] = False
        with pytest.raises(HTTPException):
            await auth.current_user(token)
        db.users.rows[0]['is_active'] = True
        db.auth_sessions.rows[0]['expires_at'] = 0
        with pytest.raises(HTTPException):
            await auth.current_user(token)
        legacy = jwt.encode({'user_id':'synthetic','role':'admin','exp':9999999999}, auth.secret, algorithm='HS256')
        with pytest.raises(HTTPException):
            await auth.current_user(legacy)
    asyncio.run(scenario())


def test_attempts_are_shared_and_bounded(runtime):
    auth, db = runtime
    async def scenario():
        second_worker = SessionAuth(db, auth.secret)
        for _ in range(10):
            with pytest.raises(HTTPException) as denied:
                await auth.login('synthetic', 'wrong')
            assert denied.value.status_code == 401
        with pytest.raises(HTTPException) as denied:
            await second_worker.login('synthetic', 'test-password')
        assert denied.value.status_code == 429
        assert not db.auth_sessions.rows
    asyncio.run(scenario())


def test_tokens_tampering_missing_accounts_and_persistence_failure(runtime):
    auth, db = runtime
    async def scenario():
        result = await auth.login('synthetic', 'test-password')
        token = result['token']
        for bad in ('garbage', token[:-8] + 'tampered'):
            with pytest.raises(HTTPException):
                await auth.current_user(bad)
        db.users.rows.clear()
        with pytest.raises(HTTPException):
            await auth.current_user(token)
        with pytest.raises(HTTPException):
            await auth.login('unknown', 'test-password')
    asyncio.run(scenario())


def test_session_persistence_failure_never_returns_token(runtime):
    auth, db = runtime
    from unittest.mock import AsyncMock
    db.auth_sessions.insert_one = AsyncMock(side_effect=RuntimeError('synthetic storage failure'))
    with pytest.raises(RuntimeError):
        asyncio.run(auth.login('synthetic', 'test-password'))
    assert db.auth_sessions.rows == []


def test_password_corruption_and_unknown_role_fail_closed(runtime):
    auth, db = runtime
    async def scenario():
        original = db.users.rows[0]['password']
        db.users.rows[0]['password'] = 'malformed'
        with pytest.raises(HTTPException) as denied:
            await auth.login('synthetic', 'test-password')
        assert denied.value.status_code == 401
        db.users.rows[0]['password'] = original
        db.users.rows[0]['role'] = 'SYSTEM_DEVELOPER'
        with pytest.raises(HTTPException) as denied:
            await auth.login('synthetic', 'test-password')
        assert denied.value.status_code == 403
    asyncio.run(scenario())


def test_logout_only_revokes_its_session_and_reauthentication_is_server_owned(runtime):
    auth, db = runtime
    async def scenario():
        first = (await auth.login('synthetic', 'test-password'))['token']
        second = (await auth.login('synthetic', 'test-password'))['token']
        assert all(row['reauthenticated_at'] is None for row in db.auth_sessions.rows)
        await auth.reauthenticate(first, 'test-password')
        assert db.auth_sessions.rows[0]['reauthenticated_at'] is not None
        assert db.auth_sessions.rows[1]['reauthenticated_at'] is None
        await auth.logout(first)
        with pytest.raises(HTTPException):
            await auth.reauthenticate(first, 'test-password')
        assert (await auth.current_user(second))['id'] == 'synthetic'
    asyncio.run(scenario())


def test_registration_rejects_unsafe_password_and_cannot_assign_role(runtime):
    auth, db = runtime
    async def scenario():
        async with HTTPClient(app_for(auth)) as c:
            body = {'email':'synthetic@example.com', 'name':'Synthetic', 'password':'x' * 73,
                    'role':'admin', 'is_active':True}
            assert (await c.post('/api/auth/register', json=body)).status_code == 422
            body['password'] = 'test-password'
            response = await c.post('/api/auth/register', json=body)
            assert response.status_code == 200
            assert 'token' not in response.json()
            assert response.json()['user']['role'] == 'telemarketer'
            assert response.json()['user']['is_active'] is False
    asyncio.run(scenario())
