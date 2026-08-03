"""
Tests for multiple employments (up to 4) in prequalifications:
- Create a prequalification with 2 employments (submit-with-file, JSON employments field)
- Verify the submission detail returns both employments
- Convert prequalification to client, verify client has employments array
- Sync to existing client, verify employments transferred
- Legacy (no employments array) still works
"""
import io
import json
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@carplus.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _base_prequalify_payload():
    suffix = uuid.uuid4().hex[:8]
    return {
        "firstName": "TEST_EMP",
        "lastName": f"Multi_{suffix}",
        "email": f"testemp_{suffix}@test.com",
        "phone": f"+1777{uuid.uuid4().hex[:7]}",
        "dateOfBirth": "1990-05-15",
        "ssnType": "SSN",
        "ssn": "555-66-7777",
        "address": "500 Multi St",
        "city": "Miami",
        "state": "FL",
        "zipCode": "33101",
        "housingType": "Renta",
        "rentAmount": "1500",
        "timeAtAddressYears": "3",
        "timeAtAddressMonths": "2",
        "idType": "DL",
        "idNumber": "D1234567",
    }


def _two_employments():
    return [
        {
            "employmentType": "W2",
            "employerName": "PrimaryCorp",
            "employerPhoneNumber": "+13051111111",
            "timeWithEmployerYears": "4",
            "timeWithEmployerMonths": "3",
            "incomeType": "Salario",
            "netIncome": "5000",
            "incomeFrequency": "Mensual",
        },
        {
            "employmentType": "1099",
            "employerName": "SideGigLLC",
            "employerPhoneNumber": "+13052222222",
            "timeWithEmployerYears": "1",
            "timeWithEmployerMonths": "6",
            "incomeType": "Comision",
            "netIncome": "1200",
            "incomeFrequency": "Mensual",
        },
    ]


def _submit_with_two_employments():
    """POST to /prequalify/submit-with-file with employments JSON field."""
    payload = _base_prequalify_payload()
    data = {**payload, "employments": json.dumps(_two_employments())}
    # multipart/form-data - no file necessary
    files = {"idFile": ("", io.BytesIO(b""), "application/octet-stream")}
    r = requests.post(f"{BASE_URL}/api/prequalify/submit-with-file",
                      data=data, files=files)
    return r, payload


class TestPrequalifyMultipleEmployments:
    submission_ids = []

    def test_submit_with_two_employments_persists_array(self, admin_headers):
        r, payload = _submit_with_two_employments()
        assert r.status_code in (200, 201), r.text
        body = r.json()
        sub_id = body.get("id") or body.get("submission_id")
        assert sub_id, f"No id in response: {body}"
        TestPrequalifyMultipleEmployments.submission_ids.append(sub_id)

        # Fetch list and find our submission
        list_r = requests.get(f"{BASE_URL}/api/prequalify/submissions",
                              headers=admin_headers)
        assert list_r.status_code == 200
        subs = list_r.json()
        ours = next((s for s in subs if s.get("id") == sub_id), None)
        assert ours, "Submission not returned in list"

        emps = ours.get("employments")
        assert isinstance(emps, list), f"employments is not a list: {emps}"
        assert len(emps) == 2, f"Expected 2 employments, got {len(emps)}: {emps}"
        # Verify content of second employment (the reported bug)
        e2 = emps[1]
        assert e2.get("employerName") == "SideGigLLC"
        assert e2.get("employerPhoneNumber") == "+13052222222"
        assert e2.get("netIncome") == "1200"

    def test_convert_prequalify_to_new_client_transfers_all_employments(self, admin_headers):
        r, payload = _submit_with_two_employments()
        assert r.status_code in (200, 201), r.text
        sub_id = r.json().get("id") or r.json().get("submission_id")
        TestPrequalifyMultipleEmployments.submission_ids.append(sub_id)

        # Convert to client
        conv_r = requests.post(
            f"{BASE_URL}/api/prequalify/submissions/{sub_id}/create-client",
            headers=admin_headers, json={})
        assert conv_r.status_code == 200, conv_r.text
        client_id = conv_r.json().get("client_id") or conv_r.json().get("id")
        assert client_id, f"No client_id returned: {conv_r.json()}"

        try:
            # Fetch client
            c_r = requests.get(f"{BASE_URL}/api/clients/{client_id}",
                               headers=admin_headers)
            assert c_r.status_code == 200, c_r.text
            client = c_r.json()
            emps = client.get("employments")
            assert isinstance(emps, list), f"Client missing employments array: {client}"
            assert len(emps) == 2, f"Client has {len(emps)} employments (expected 2)"
            assert emps[0].get("employerName") == "PrimaryCorp"
            assert emps[1].get("employerName") == "SideGigLLC"
            # Legacy fields also populated from first employment
            assert client.get("employer_name") == "PrimaryCorp"
        finally:
            requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true",
                            headers=admin_headers)

    def test_sync_prequalify_to_existing_client_transfers_employments(self, admin_headers):
        # Use SAME phone in client and prequalify so backend auto-matches
        shared_phone = f"+1666{uuid.uuid4().hex[:7]}"
        create = requests.post(f"{BASE_URL}/api/clients",
                               headers=admin_headers,
                               json={"first_name": "TEST_SYNC",
                                     "last_name": "Target",
                                     "phone": shared_phone})
        assert create.status_code == 200, create.text
        client_id = create.json()["id"]

        # Create prequalify with 2 employments, matching phone
        payload = _base_prequalify_payload()
        payload["phone"] = shared_phone
        data = {**payload, "employments": json.dumps(_two_employments())}
        files = {"idFile": ("", io.BytesIO(b""), "application/octet-stream")}
        r = requests.post(f"{BASE_URL}/api/prequalify/submit-with-file",
                          data=data, files=files)
        assert r.status_code in (200, 201), r.text
        sub_id = r.json().get("id") or r.json().get("submission_id")
        TestPrequalifyMultipleEmployments.submission_ids.append(sub_id)

        try:
            sync_r = requests.post(
                f"{BASE_URL}/api/prequalify/submissions/{sub_id}/sync-to-client",
                headers=admin_headers,
                json={"client_id": client_id})
            assert sync_r.status_code == 200, sync_r.text

            c_r = requests.get(f"{BASE_URL}/api/clients/{client_id}",
                               headers=admin_headers)
            assert c_r.status_code == 200
            client = c_r.json()
            emps = client.get("employments")
            assert isinstance(emps, list), f"employments missing after sync: {client}"
            assert len(emps) == 2, f"expected 2 employments, got {len(emps)}"
            assert emps[1].get("employerName") == "SideGigLLC"
            assert emps[1].get("netIncome") == "1200"
            assert client.get("employer_name") == "PrimaryCorp"
        finally:
            requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true",
                            headers=admin_headers)

    def test_legacy_prequalify_no_employments_array_still_convertible(self, admin_headers):
        # Submit via JSON endpoint (does NOT include employments array)
        payload = {
            **_base_prequalify_payload(),
            "employerName": "LegacyCo",
            "employerPhoneNumber": "+13053334444",
            "incomeType": "Salario",
            "netIncome": "3500",
            "incomeFrequency": "Mensual",
            "timeWithEmployerYears": "5",
            "timeWithEmployerMonths": "0",
            "employmentType": "W2",
        }
        r = requests.post(f"{BASE_URL}/api/prequalify/submit", json=payload)
        assert r.status_code in (200, 201), r.text
        sub_id = r.json().get("id") or r.json().get("submission_id")
        assert sub_id
        TestPrequalifyMultipleEmployments.submission_ids.append(sub_id)

        # Convert to client
        conv_r = requests.post(
            f"{BASE_URL}/api/prequalify/submissions/{sub_id}/create-client",
            headers=admin_headers, json={})
        assert conv_r.status_code == 200, conv_r.text
        client_id = conv_r.json().get("client_id") or conv_r.json().get("id")
        assert client_id

        try:
            c_r = requests.get(f"{BASE_URL}/api/clients/{client_id}",
                               headers=admin_headers)
            assert c_r.status_code == 200
            client = c_r.json()
            # Should have built employments from legacy fields (backward compat)
            emps = client.get("employments") or []
            assert len(emps) == 1, f"legacy should yield 1 employment, got {emps}"
            assert emps[0].get("employerName") == "LegacyCo"
            assert client.get("employer_name") == "LegacyCo"
        finally:
            requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true",
                            headers=admin_headers)

    @classmethod
    def teardown_class(cls):
        # Cleanup submissions
        try:
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            if r.status_code == 200:
                h = {"Authorization": f"Bearer {r.json()['token']}"}
                for sid in cls.submission_ids:
                    requests.delete(f"{BASE_URL}/api/prequalify/submissions/{sid}",
                                    headers=h)
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
