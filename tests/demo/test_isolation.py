"""Offline demo identity regression tests; no server, database or credentials."""
import asyncio
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from runtime_security import require_enabled_user, mock_delivery
from crm_authorization import CRMAccess, SCOPED_COLLECTIONS
from document_authorization import can_access_documents


class NoDatabase:
    def __getattr__(self, key):
        raise AssertionError('Demo identity reached database: ' + key)


@pytest.mark.parametrize('marker', [
    {'role': 'DEMO'}, {'role': 'demo'}, {'is_demo': True},
    {'is_demo': 'true'}, {'id': 'demo-visitor'},
])
def test_demo_cannot_access_any_crm_collection_or_document(marker):
    user = {'id': 'fictional-user', 'role': 'admin', 'approved': True, **marker}
    with pytest.raises(HTTPException) as denied:
        require_enabled_user(user)
    assert denied.value.status_code == 403
    access = CRMAccess(NoDatabase(), user)
    for collection in SCOPED_COLLECTIONS:
        for operation in ('read', 'write', 'delete'):
            with pytest.raises(HTTPException) as denied:
                asyncio.run(access.require(collection, 'fictional-nondemo-client', operation))
            assert denied.value.status_code == 403
            with pytest.raises(HTTPException):
                asyncio.run(access.scope(collection, operation))
    assert not asyncio.run(can_access_documents(NoDatabase(), user, {'id': 'fictional-nondemo-client'}))


def test_regular_identity_and_mock_delivery_contract_remain_intact():
    user = {'id': 'fictional-user', 'role': 'admin', 'approved': True}
    assert require_enabled_user(user) == user
    for channel in ('sms', 'email', 'whatsapp', 'credit'):
        assert mock_delivery(channel)['success'] is False
        assert mock_delivery(channel)['provider'] == 'mock'
