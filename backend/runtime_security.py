"""Shared authentication and fail-closed V2 development runtime boundaries."""
import os
from fastapi import HTTPException

ROLES = frozenset({'admin', 'bdc_manager', 'bdc', 'telemarketer', 'salesperson'})


def jwt_secret(environ=None):
    secret = (os.environ if environ is None else environ).get('JWT_SECRET', '')
    if len(secret.strip()) < 32 or secret == 'dealercrm-secret-key-2024':
        raise RuntimeError('JWT_SECRET must be explicitly configured with at least 32 characters')
    return secret


def require_enabled_user(user):
    """Legacy accounts may use either flag; explicit denial always wins."""
    if not isinstance(user, dict) or not isinstance(user.get('id'), str) or not user['id']:
        raise HTTPException(401, 'Invalid account')
    if not isinstance(user.get('role'), str) or user['role'] not in ROLES:
        raise HTTPException(403, 'Unsupported account role')
    flags = [user[key] for key in ('is_active', 'approved') if key in user]
    if not flags or any(flag is not True for flag in flags):
        raise HTTPException(403, 'Account inactive or pending approval')
    return user


def mock_delivery(channel):
    # Deliberately no environment switch to enable real providers in this branch.
    # Existing callers only mark delivered/reminded when success is True.
    return {'success': False, 'status': 'mocked', 'provider': 'mock',
            'channel': channel, 'error': 'External delivery disabled in V2 development'}
