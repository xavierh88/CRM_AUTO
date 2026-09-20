"""Security contracts with fictional data; no server startup or external services."""
import asyncio
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from runtime_security import require_enabled_user, jwt_secret, mock_delivery
from public_tokens import resolve_appointment_token
from upload_validation import validate_documents, upload_directory
from crm_authorization import CRMAccess


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize('flags,allowed', [
    ({}, False), ({'is_active': True}, True), ({'approved': True}, True),
    ({'is_active': False, 'approved': True}, False),
    ({'is_active': True, 'approved': False}, False),
    ({'is_active': 'true'}, False), ({'approved': None}, False),
])
def test_account_flags_agree_for_all_roles(flags, allowed):
    for role in ('admin', 'bdc', 'bdc_manager', 'salesperson', 'telemarketer'):
        user = {'id': 'fictional-user', 'role': role, **flags}
        if allowed:
            require_enabled_user(user)
        else:
            with pytest.raises(HTTPException):
                require_enabled_user(user)


def test_no_secret_fallback_or_provider_success():
    for env in ({}, {'JWT_SECRET': 'dealercrm-secret-key-2024'}, {'JWT_SECRET': 'short'}):
        with pytest.raises(RuntimeError):
            jwt_secret(env)
    assert jwt_secret({'JWT_SECRET': 'fictional-test-key-' * 3}) == 'fictional-test-key-' * 3
    assert mock_delivery('sms')['success'] is False
    assert mock_delivery('email')['status'] == 'mocked'


@pytest.mark.parametrize('expiry', [None, '', 'not-a-date', '2026-01-01',
    (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()])
def test_public_token_invalid_expiry_never_falls_back(expiry):
    db = SimpleNamespace(public_links=SimpleNamespace(find_one=AsyncMock(return_value={
        'record_id': 'fictional-appt', 'client_id': 'fictional-client', 'expires_at': expiry,
        'link_type': 'appointment'})), appointments=SimpleNamespace(find_one=AsyncMock()))
    with pytest.raises(HTTPException):
        run(resolve_appointment_token(db, 'a' * 43))
    db.appointments.find_one.assert_not_called()


def test_valid_token_binds_client_and_appointment():
    link = {'record_id': 'fictional-appt', 'client_id': 'fictional-client',
            'expires_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), 'link_type': 'appointment'}
    appointment = {'id': 'fictional-appt', 'client_id': 'fictional-client', 'public_token': 'a' * 43}
    db = SimpleNamespace(public_links=SimpleNamespace(find_one=AsyncMock(return_value=link)),
                         appointments=SimpleNamespace(find_one=AsyncMock(return_value=appointment)),
                         clients=SimpleNamespace(find_one=AsyncMock(return_value={'id': 'fictional-client'})))
    assert run(resolve_appointment_token(db, 'a' * 43)) == appointment
    appointment['client_id'] = 'other-client'
    with pytest.raises(HTTPException):
        run(resolve_appointment_token(db, 'a' * 43))


def test_upload_validation_and_path(tmp_path):
    from starlette.datastructures import Headers
    def upload(name, content, mime):
        return UploadFile(io.BytesIO(content), filename=name, headers=Headers({'content-type': mime}))
    for file in [upload('../escape.pdf', b'%PDF-1.4', 'application/pdf'),
                 upload('fictional.html', b'<html>', 'text/html'),
                 upload('fictional.pdf', b'not pdf', 'application/pdf'),
                 upload('fictional.pdf', b'%PDF-' + b'x' * (10 * 1024 * 1024), 'application/pdf')]:
        with pytest.raises(HTTPException):
            run(validate_documents([file]))
    result = run(validate_documents([upload('fictional.pdf', b'%PDF-1.4\n%%EOF', 'application/pdf')]))
    assert result[0]['extension'] == 'pdf'
    with pytest.raises(HTTPException):
        upload_directory(tmp_path, '../escape')
    (tmp_path / 'clients').symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(HTTPException):
        upload_directory(tmp_path, 'fictional-client')


def test_crm_direct_access_denies_other_owner_and_readonly_collaborator():
    client = {'id': 'fictional-client', 'created_by': 'fictional-owner', 'collaboration_users': ['fictional-collaborator']}
    db = SimpleNamespace(clients=SimpleNamespace(find_one=AsyncMock(return_value=client)),
                         users=SimpleNamespace(find_one=AsyncMock(return_value={'role': 'admin'})))
    for role, user_id in [('telemarketer', 'other'), ('bdc_manager', 'other'), ('unknown', 'fictional-owner')]:
        with pytest.raises(HTTPException):
            run(CRMAccess(db, {'id': user_id, 'role': role}).require('clients', client['id']))
    access = CRMAccess(db, {'id': 'fictional-collaborator', 'role': 'salesperson'})
    assert run(access.require('clients', client['id'])) == client
    with pytest.raises(HTTPException):
        run(access.require('clients', client['id'], 'write'))
