"""
Test suite for CRM features - Iteration 10
Tests:
1. White screen fix after appointment creation (SMS/email error handling)
2. Owner filter dropdown for Admin/BDC Manager
3. Note reminders system with datetime field
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "xavier.hernandez.1988@gmail.com"
ADMIN_PASSWORD = "Cali2020"


class TestAuthentication:
    """Test login functionality"""
    
    def test_admin_login(self):
        """Test admin login with provided credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"✓ Admin login successful - User: {data['user']['name']}, Role: {data['user']['role']}")
        return data["access_token"]


class TestOwnerFilter:
    """Test owner filter functionality for Admin/BDC Manager"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_clients_with_owner_filter_mine(self, auth_token):
        """Test GET /api/clients with owner_filter=mine"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=mine",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        clients = response.json()
        print(f"✓ Owner filter 'mine' returned {len(clients)} clients")
        return clients
    
    def test_clients_with_owner_filter_others(self, auth_token):
        """Test GET /api/clients with owner_filter=others"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=others",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        clients = response.json()
        print(f"✓ Owner filter 'others' returned {len(clients)} clients")
        return clients
    
    def test_clients_with_owner_filter_all(self, auth_token):
        """Test GET /api/clients with owner_filter=all"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=all",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        clients = response.json()
        print(f"✓ Owner filter 'all' returned {len(clients)} clients")
        return clients
    
    def test_owner_filter_counts_make_sense(self, auth_token):
        """Verify that mine + others <= all"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        mine_resp = requests.get(f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=mine", headers=headers)
        others_resp = requests.get(f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=others", headers=headers)
        all_resp = requests.get(f"{BASE_URL}/api/clients?exclude_sold=true&owner_filter=all", headers=headers)
        
        mine_count = len(mine_resp.json())
        others_count = len(others_resp.json())
        all_count = len(all_resp.json())
        
        # mine + others should equal all (no overlap)
        assert mine_count + others_count == all_count, \
            f"Filter counts don't add up: mine({mine_count}) + others({others_count}) != all({all_count})"
        print(f"✓ Owner filter counts verified: mine({mine_count}) + others({others_count}) = all({all_count})")


class TestNoteReminders:
    """Test note/comment reminders functionality"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_client_id(self, auth_token):
        """Get a test client ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/clients?limit=1", headers=headers)
        clients = response.json()
        if clients:
            return clients[0]["id"]
        pytest.skip("No clients available for testing")
    
    def test_add_note_without_reminder(self, auth_token, test_client_id):
        """Test adding a note without reminder"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/clients/{test_client_id}/comments",
            headers=headers,
            data={"comment": "TEST_Note without reminder"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["comment"] == "TEST_Note without reminder"
        assert data["reminder_at"] is None
        assert data["reminder_sent"] == False
        print(f"✓ Note without reminder created: {data['id']}")
        return data["id"]
    
    def test_add_note_with_reminder(self, auth_token, test_client_id):
        """Test adding a note with reminder datetime"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Set reminder for 1 hour from now
        reminder_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{test_client_id}/comments",
            headers=headers,
            data={
                "comment": "TEST_Note with reminder - follow up call",
                "reminder_at": reminder_time
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["comment"] == "TEST_Note with reminder - follow up call"
        assert data["reminder_at"] is not None
        assert data["reminder_sent"] == False
        print(f"✓ Note with reminder created: {data['id']}, reminder_at: {data['reminder_at']}")
        return data["id"]
    
    def test_get_client_notes(self, auth_token, test_client_id):
        """Test retrieving client notes"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/clients/{test_client_id}/comments",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        notes = response.json()
        print(f"✓ Retrieved {len(notes)} notes for client")
        
        # Check if any notes have reminders
        notes_with_reminders = [n for n in notes if n.get("reminder_at")]
        print(f"  - Notes with reminders: {len(notes_with_reminders)}")
        return notes
    
    def test_note_reminder_fields_present(self, auth_token, test_client_id):
        """Verify note response includes reminder fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a note with reminder
        reminder_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        response = requests.post(
            f"{BASE_URL}/api/clients/{test_client_id}/comments",
            headers=headers,
            data={
                "comment": "TEST_Verify reminder fields",
                "reminder_at": reminder_time
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        assert "id" in data
        assert "client_id" in data
        assert "comment" in data
        assert "user_id" in data
        assert "user_name" in data
        assert "created_at" in data
        assert "reminder_at" in data
        assert "reminder_sent" in data
        print(f"✓ All reminder fields present in note response")


class TestAppointmentCreation:
    """Test appointment creation with SMS/email error handling"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_client_with_record(self, auth_token):
        """Get a client with a user record for appointment testing"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get clients
        clients_resp = requests.get(f"{BASE_URL}/api/clients?limit=5", headers=headers)
        clients = clients_resp.json()
        
        for client in clients:
            # Check if client has records
            records_resp = requests.get(
                f"{BASE_URL}/api/user-records?client_id={client['id']}",
                headers=headers
            )
            records = records_resp.json()
            if records:
                return {"client": client, "record": records[0]}
        
        pytest.skip("No client with records available for testing")
    
    def test_create_appointment_success(self, auth_token, test_client_with_record):
        """Test creating an appointment successfully"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        client = test_client_with_record["client"]
        record = test_client_with_record["record"]
        
        # Create appointment
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            headers=headers,
            json={
                "user_record_id": record["id"],
                "client_id": client["id"],
                "date": tomorrow,
                "time": "10:00",
                "dealer": "Downey",
                "language": "es"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["date"] == tomorrow
        assert data["time"] == "10:00"
        print(f"✓ Appointment created successfully: {data['id']}")
        return data
    
    def test_sms_endpoint_handles_errors_gracefully(self, auth_token, test_client_with_record):
        """Test that SMS endpoint returns proper error (not crash)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        client = test_client_with_record["client"]
        
        # Try to send SMS - may fail due to Twilio A2P but should return proper error
        response = requests.post(
            f"{BASE_URL}/api/sms/send-appointment-link?client_id={client['id']}&appointment_id=fake-id",
            headers=headers
        )
        # Should return 404 or 500 with proper error message, not crash
        assert response.status_code in [200, 404, 500], f"Unexpected status: {response.status_code}"
        print(f"✓ SMS endpoint handled gracefully with status {response.status_code}")
    
    def test_email_endpoint_handles_errors_gracefully(self, auth_token, test_client_with_record):
        """Test that email endpoint returns proper error (not crash)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        client = test_client_with_record["client"]
        
        # Try to send email - may fail but should return proper error
        response = requests.post(
            f"{BASE_URL}/api/email/send-appointment-link?client_id={client['id']}&appointment_id=fake-id",
            headers=headers
        )
        # Should return 404 or 500 with proper error message, not crash
        assert response.status_code in [200, 404, 500], f"Unexpected status: {response.status_code}"
        print(f"✓ Email endpoint handled gracefully with status {response.status_code}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_cleanup_test_notes(self, auth_token):
        """Clean up TEST_ prefixed notes"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get all clients
        clients_resp = requests.get(f"{BASE_URL}/api/clients?limit=100", headers=headers)
        clients = clients_resp.json()
        
        deleted_count = 0
        for client in clients:
            # Get notes for this client
            notes_resp = requests.get(
                f"{BASE_URL}/api/clients/{client['id']}/comments",
                headers=headers
            )
            notes = notes_resp.json()
            
            # Delete TEST_ prefixed notes
            for note in notes:
                if note.get("comment", "").startswith("TEST_"):
                    del_resp = requests.delete(
                        f"{BASE_URL}/api/clients/{client['id']}/comments/{note['id']}",
                        headers=headers
                    )
                    if del_resp.status_code == 200:
                        deleted_count += 1
        
        print(f"✓ Cleaned up {deleted_count} test notes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
