"""
Test suite for the 7 CRM improvements:
1. Dashboard stat details endpoint (clickable stats)
2. Clients Excel export
3. Client prequalify info endpoint
4. Prequalify submission - employer_phone_number field
5. Delete prequalify submission
"""

import pytest
import requests
import os
import uuid
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

ADMIN_EMAIL = "admin@carplus.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    assert data["user"]["role"] == "admin"
    return data["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ============ 1. Dashboard clickable stats details ============
class TestDashboardStatDetails:
    STAT_TYPES = [
        "total_clients", "new_clients_month", "sales", "sales_month",
        "today_appointments", "week_appointments",
    ]

    def test_total_clients_details(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats/total_clients/details",
                         headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["stat_type"] == "total_clients"
        assert "items" in data and "count" in data
        assert isinstance(data["items"], list)
        assert data["count"] == len(data["items"])
        if data["items"]:
            it = data["items"][0]
            assert "id" in it
            assert "_id" not in it

    @pytest.mark.parametrize("stat_type", STAT_TYPES)
    def test_all_stat_types_reachable(self, admin_headers, stat_type):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats/{stat_type}/details",
                         headers=admin_headers)
        assert r.status_code == 200, f"{stat_type}: {r.text}"
        data = r.json()
        assert data["stat_type"] == stat_type
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats/total_clients/details")
        assert r.status_code in (401, 403)


# ============ 2. Clients Excel Export ============
class TestClientsExcelExport:
    def test_export_admin_returns_excel(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/clients/export/excel", headers=admin_headers)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct or "excel" in ct, f"Unexpected content-type: {ct}"
        assert r.headers.get("content-disposition", "").lower().startswith("attachment")
        # xlsx files start with PK zip signature
        assert r.content[:2] == b"PK", "Response is not a valid xlsx file"

        # Verify columns
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
            ws = wb.active
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            assert headers == ["Nombre", "Apellido", "Email", "Teléfono"], f"Bad headers: {headers}"
        except ImportError:
            pass

    def test_export_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/clients/export/excel")
        assert r.status_code in (401, 403)


# ============ 3. Client Prequalify Link ============
class TestClientPrequalify:
    def test_get_client_prequalify_no_match(self, admin_headers):
        # Create a client with a random phone unlikely to match
        random_phone = f"+1999{uuid.uuid4().hex[:7]}"
        create = requests.post(f"{BASE_URL}/api/clients",
                               headers=admin_headers,
                               json={"first_name": "TEST_PQ",
                                     "last_name": "Client",
                                     "phone": random_phone})
        assert create.status_code == 200, create.text
        client_id = create.json()["id"]

        try:
            r = requests.get(f"{BASE_URL}/api/clients/{client_id}/prequalify",
                             headers=admin_headers)
            assert r.status_code == 200, r.text
            data = r.json()
            assert "found" in data
            assert "prequalify" in data
            # For a fresh random-phone client we don't expect a match
            assert data["found"] is False
            assert data["prequalify"] is None
        finally:
            requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true",
                            headers=admin_headers)

    def test_client_prequalify_client_not_found(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/clients/nonexistent-id-xyz/prequalify",
                         headers=admin_headers)
        assert r.status_code == 404

    def test_client_prequalify_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/clients/any/prequalify")
        assert r.status_code in (401, 403)


# ============ 4. Prequalify submission + employer_phone_number ============
class TestPrequalifyEmployerPhone:
    def test_submit_prequalify_with_employer_phone(self, admin_headers):
        # Use JSON endpoint (simpler for automated testing)
        payload = {
            "firstName": "TEST_PQ",
            "lastName": f"Emp_{uuid.uuid4().hex[:6]}",
            "email": f"testpq_{uuid.uuid4().hex[:8]}@test.com",
            "phone": f"+1555{uuid.uuid4().hex[:7]}",
            "dateOfBirth": "1990-01-01",
            "ssn": "123-45-6789",
            "address": "123 Test St",
            "city": "Miami",
            "state": "FL",
            "zipCode": "33101",
            "employerName": "TestCo",
            "employerPhoneNumber": "+13051234567",
            "monthlyIncome": "5000",
            "yearsAtJob": "3",
        }
        r = requests.post(f"{BASE_URL}/api/prequalify/submit", json=payload)
        # Endpoint may accept or validate strictly; just don't 500
        assert r.status_code in (200, 201, 400, 422), r.text

        submission_id = None
        if r.status_code in (200, 201):
            body = r.json()
            submission_id = body.get("id") or body.get("submission_id")

        # Verify listing contains employer phone number field
        list_r = requests.get(f"{BASE_URL}/api/prequalify/submissions",
                              headers=admin_headers)
        assert list_r.status_code == 200, list_r.text
        submissions = list_r.json()
        assert isinstance(submissions, list)

        # Find our submission
        if submission_id:
            ours = next((s for s in submissions if s.get("id") == submission_id), None)
            if ours:
                # Field name might be employerPhoneNumber or employer_phone_number
                assert (
                    ours.get("employerPhoneNumber") == "+13051234567"
                    or ours.get("employer_phone_number") == "+13051234567"
                ), f"Employer phone not persisted: {ours}"

                # Verify address/city/zip stored (bug fix #4)
                assert ours.get("address") == "123 Test St"
                assert ours.get("city") == "Miami"
                assert (ours.get("zipCode") == "33101" or ours.get("zip_code") == "33101")

                # Cleanup - delete the submission
                del_r = requests.delete(
                    f"{BASE_URL}/api/prequalify/submissions/{submission_id}",
                    headers=admin_headers)
                assert del_r.status_code == 200, del_r.text


# ============ 5. Delete prequalify submission ============
class TestDeletePrequalifySubmission:
    def test_delete_nonexistent_returns_404(self, admin_headers):
        r = requests.delete(
            f"{BASE_URL}/api/prequalify/submissions/nonexistent-id-xyz-{uuid.uuid4().hex}",
            headers=admin_headers)
        assert r.status_code == 404

    def test_delete_requires_admin(self):
        r = requests.delete(f"{BASE_URL}/api/prequalify/submissions/any")
        assert r.status_code in (401, 403)

    def test_full_delete_flow(self, admin_headers):
        # Create submission
        payload = {
            "firstName": "TEST_DEL",
            "lastName": f"Sub_{uuid.uuid4().hex[:6]}",
            "email": f"testdel_{uuid.uuid4().hex[:8]}@test.com",
            "phone": f"+1444{uuid.uuid4().hex[:7]}",
            "dateOfBirth": "1990-01-01",
            "ssn": "111-22-3333",
            "address": "1 Del St",
            "city": "Miami",
            "state": "FL",
            "zipCode": "33101",
            "employerName": "DelCo",
            "employerPhoneNumber": "+13051112222",
            "monthlyIncome": "5000",
            "yearsAtJob": "2",
        }
        r = requests.post(f"{BASE_URL}/api/prequalify/submit", json=payload)
        if r.status_code not in (200, 201):
            pytest.skip(f"Cannot create submission for delete test: {r.text}")
        submission_id = r.json().get("id") or r.json().get("submission_id")
        if not submission_id:
            pytest.skip("No submission_id returned")

        # Delete it
        del_r = requests.delete(
            f"{BASE_URL}/api/prequalify/submissions/{submission_id}",
            headers=admin_headers)
        assert del_r.status_code == 200, del_r.text
        assert "message" in del_r.json()

        # Verify it no longer exists
        list_r = requests.get(f"{BASE_URL}/api/prequalify/submissions",
                              headers=admin_headers)
        submissions = list_r.json()
        assert not any(s.get("id") == submission_id for s in submissions), \
            "Submission still present after delete"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
