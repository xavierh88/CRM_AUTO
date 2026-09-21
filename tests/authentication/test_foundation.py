"""Offline authentication contracts; all identities and passwords are synthetic."""
from dataclasses import replace
import pytest
from backend.authentication.foundation import (
    Actor, ConfirmationGate, PasskeysPending, hash_password, verify_password,
    passkey_options, verify_passkey,
)


@pytest.fixture
def actor():
    return Actor('fictional-user', 'fictional-tenant', 'fictional-session',
                 'admin', True, True, 100.0)


def test_password_roundtrip_and_corrupt_hash():
    encoded = hash_password('fictional password only')
    assert verify_password('fictional password only', encoded)
    assert not verify_password('wrong fictional password', encoded)
    for value in ('broken', '', None, '$2b$99$' + 'x' * 53):
        assert not verify_password('fictional password only', value)


@pytest.mark.parametrize('password', ['', None, 'x' * 73, 'é' * 37, '\ud800'])
def test_password_rejects_unsafe_input(password):
    with pytest.raises(ValueError):
        hash_password(password)
    assert not verify_password(password, 'broken')


def test_passkeys_never_authenticate_without_verifier():
    assert passkey_options() == {'status': 'PENDING_EXTERNAL', 'available': False,
                                'password_fallback': True}
    with pytest.raises(PasskeysPending):
        verify_passkey({'verified': True, 'biometric': 'must not be inspected'})


def test_confirmation_is_bound_and_single_use(actor):
    gate = ConfirmationGate(clock=lambda: 100.0)
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    assert gate.confirm(actor, ticket, 'manage_users', 'fictional-target', 'a' * 64,
                        human_confirmed=True) is None
    with pytest.raises(PermissionError):
        gate.confirm(actor, ticket, 'manage_users', 'fictional-target', 'a' * 64,
                     human_confirmed=True)


@pytest.mark.parametrize('changes', [
    {'active': False}, {'human': False}, {'role': 'unknown'},
    {'role': 'salesperson'}, {'reauthenticated_at': None},
    {'reauthenticated_at': -201}, {'reauthenticated_at': 101},
    {'reauthenticated_at': float('nan')}, {'user_id': ''}, {'tenant_id': ''},
    {'session_id': ''}, {'active': 'true'},
])
def test_preview_denies_untrusted_or_stale_actor(actor, changes):
    with pytest.raises(PermissionError):
        ConfirmationGate(clock=lambda: 100).preview(
            replace(actor, **changes), 'manage_users', 'fictional-target', 'a' * 64)


@pytest.mark.parametrize('changes', [
    {'user_id': 'other'}, {'tenant_id': 'other'}, {'session_id': 'other'},
    {'role': 'salesperson'}, {'active': False}, {'human': False},
])
def test_confirmation_rechecks_actor(actor, changes):
    gate = ConfirmationGate(clock=lambda: 100)
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    with pytest.raises(PermissionError):
        gate.confirm(replace(actor, **changes), ticket, 'manage_users',
                     'fictional-target', 'a' * 64, human_confirmed=True)


@pytest.mark.parametrize('action,target,digest,confirmed', [
    ('edit_schema', 'fictional-target', 'a' * 64, True),
    ('manage_users', 'other', 'a' * 64, True),
    ('manage_users', 'fictional-target', 'b' * 64, True),
    ('manage_users', 'fictional-target', 'a' * 64, False),
    ('manage_users', 'fictional-target', 'a' * 64, 'true'),
])
def test_confirmation_cannot_change_preview(actor, action, target, digest, confirmed):
    gate = ConfirmationGate(clock=lambda: 100)
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    with pytest.raises(PermissionError):
        gate.confirm(actor, ticket, action, target, digest, human_confirmed=confirmed)


def test_expiration_capacity_and_developer_boundary(actor):
    now = [100]
    gate = ConfirmationGate(clock=lambda: now[0], capacity=1)
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    with pytest.raises(PermissionError):
        gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    now[0] = 401
    with pytest.raises(PermissionError):
        gate.confirm(replace(actor, reauthenticated_at=401), ticket, 'manage_users',
                     'fictional-target', 'a' * 64, human_confirmed=True)
    actor = replace(actor, reauthenticated_at=401)
    with pytest.raises(PermissionError):
        gate.preview(actor, 'edit_schema', 'fictional-target', 'a' * 64)
    gate.preview(replace(actor, role='SYSTEM_DEVELOPER'), 'edit_schema',
                 'fictional-target', 'a' * 64)


@pytest.mark.parametrize('action', ['send_sms', 'send_email', 'credit_check', 'unknown'])
def test_no_external_permission_even_for_admin(actor, action):
    with pytest.raises(PermissionError):
        ConfirmationGate().preview(actor, action, 'fictional-target', 'a' * 64)


def test_passkey_management_is_self_only(actor):
    gate = ConfirmationGate(clock=lambda: 100)
    with pytest.raises(PermissionError):
        gate.preview(actor, 'manage_passkeys', 'another-user', 'a' * 64)
    gate.preview(actor, 'manage_passkeys', actor.user_id, 'a' * 64)


def test_concurrent_confirmation_has_only_one_winner(actor):
    from concurrent.futures import ThreadPoolExecutor
    gate = ConfirmationGate(clock=lambda: 100)
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    def confirm(_):
        try:
            gate.confirm(actor, ticket, 'manage_users', 'fictional-target', 'a' * 64,
                         human_confirmed=True)
            return True
        except PermissionError:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(confirm, range(8))) == 1


@pytest.mark.parametrize('target,digest', [('', 'a' * 64), ('x' * 257, 'a' * 64),
                                        ('target', ''), ('target', 'G' * 64)])
def test_invalid_bindings(actor, target, digest):
    with pytest.raises(PermissionError):
        ConfirmationGate(clock=lambda: 100).preview(actor, 'manage_users', target, digest)


@pytest.mark.parametrize('capacity', [0, -1, True, 10001])
def test_invalid_capacity(capacity):
    with pytest.raises(ValueError):
        ConfirmationGate(capacity=capacity)


def test_exact_expiry_and_clock_rollback(actor):
    now = [100]
    gate = ConfirmationGate(clock=lambda: now[0])
    ticket = gate.preview(actor, 'manage_users', 'fictional-target', 'a' * 64)
    for timestamp in (99, 400):
        now[0] = timestamp
        with pytest.raises(PermissionError):
            gate.confirm(replace(actor, reauthenticated_at=timestamp), ticket,
                         'manage_users', 'fictional-target', 'a' * 64, human_confirmed=True)
