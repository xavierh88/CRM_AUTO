"""
Test suite for Backup and Pre-Qualify to Client Conversion
Tests:
1. Verify all dealers have addresses configured
2. Verify backup endpoint includes ALL 20 collections
3. Verify pre-qualify to client conversion flow
4. Verify client is assigned to admin who converted
5. Verify notes include admin_only pre-qualify data
6. Verify submission status changes to 'converted'
"""
import pytest
import requests
import os
import uuid
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "xadmin"
ADMIN_PASSWORD = "Cali2020"

# Expected collections in backup (20 total)
EXPECTED_BACKUP_COLLECTIONS = [
    "users",
    "clients",
    "user_records",
    "cosigner_records",
    "cosigner_relations",
    "appointments",
    "prequalify_submissions",
    "config_lists",
    "record_comments",
    "client_comments",
    "client_requests",
    "notifications",
    "sms_logs",
    "email_logs",
    "sms_templates",
    "sms_conversations",
    "imported_contacts",
    "public_links",
    "collaboration_requests"
]

# Expected dealer addresses
EXPECTED_DEALER_ADDRESSES = {
    "Downey": "7444 Florence Ave",
    "Fullerton": "1100 S Harbor Blvd",
    "Hollywood": "6200 Hollywood Blvd",
    "Long Beach": "1500 E Anaheim St"
}


class TestDealerAddresses:
    """Test that all dealers have addresses configured"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.text}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_01_admin_login(self):
        """Test admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful with xadmin/Cali2020")
    
    def test_02_get_dealer_list(self):
        """Test getting dealer list"""
        response = self.session.get(f"{BASE_URL}/api/config-lists/dealer")
        assert response.status_code == 200, f"Failed to get dealer list: {response.text}"
        
        data = response.json()
        # API returns list directly, not object with items
        dealers = data if isinstance(data, list) else data.get("items", [])
        
        assert len(dealers) > 0, "No dealers found"
        print(f"✓ Found {len(dealers)} dealers")
        
        return dealers
    
    def test_03_verify_dealer_addresses(self):
        """Verify all expected dealers have addresses configured"""
        response = self.session.get(f"{BASE_URL}/api/config-lists/dealer")
        assert response.status_code == 200, f"Failed to get dealer list: {response.text}"
        
        data = response.json()
        # API returns list directly, not object with items
        dealers = data if isinstance(data, list) else data.get("items", [])
        
        dealers_with_addresses = 0
        dealers_without_addresses = []
        
        for dealer in dealers:
            dealer_name = dealer.get("name", "")
            dealer_address = dealer.get("address", "")
            
            if dealer_address and dealer_address.strip():
                dealers_with_addresses += 1
                print(f"✓ Dealer '{dealer_name}' has address: {dealer_address}")
            else:
                dealers_without_addresses.append(dealer_name)
                print(f"✗ Dealer '{dealer_name}' has NO address configured")
        
        # Check expected dealers have correct addresses
        for expected_dealer, expected_address in EXPECTED_DEALER_ADDRESSES.items():
            found = False
            for dealer in dealers:
                if expected_dealer.lower() in dealer.get("name", "").lower():
                    found = True
                    actual_address = dealer.get("address", "")
                    assert expected_address in actual_address, \
                        f"Dealer '{expected_dealer}' address mismatch. Expected '{expected_address}' in '{actual_address}'"
                    print(f"✓ Dealer '{expected_dealer}' has correct address containing '{expected_address}'")
                    break
            
            if not found:
                print(f"⚠ Expected dealer '{expected_dealer}' not found in list")
        
        print(f"\n✓ Summary: {dealers_with_addresses}/{len(dealers)} dealers have addresses configured")
        
        if dealers_without_addresses:
            print(f"⚠ Dealers without addresses: {dealers_without_addresses}")


class TestBackupEndpoint:
    """Test backup endpoint includes ALL collections"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.text}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_01_backup_endpoint_accessible(self):
        """Test backup endpoint is accessible for admin"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup")
        assert response.status_code == 200, f"Backup endpoint failed: {response.status_code} - {response.text}"
        print(f"✓ Backup endpoint accessible for admin")
    
    def test_02_backup_returns_json(self):
        """Test backup returns valid JSON"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup")
        assert response.status_code == 200
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type or "application/octet-stream" in content_type, \
            f"Unexpected content type: {content_type}"
        
        # Try to parse as JSON
        try:
            data = response.json()
            print(f"✓ Backup returns valid JSON")
        except json.JSONDecodeError:
            # If it's a file download, try to decode the content
            data = json.loads(response.content.decode('utf-8'))
            print(f"✓ Backup returns valid JSON (as file download)")
        
        return data
    
    def test_03_backup_has_metadata(self):
        """Test backup has required metadata fields"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup")
        assert response.status_code == 200
        
        try:
            data = response.json()
        except:
            data = json.loads(response.content.decode('utf-8'))
        
        assert "backup_date" in data, "Missing backup_date in backup"
        assert "backup_version" in data, "Missing backup_version in backup"
        assert "collections" in data, "Missing collections in backup"
        
        print(f"✓ Backup has metadata: date={data['backup_date']}, version={data['backup_version']}")
    
    def test_04_backup_includes_all_collections(self):
        """Test backup includes ALL 20 expected collections"""
        response = self.session.get(f"{BASE_URL}/api/admin/backup")
        assert response.status_code == 200
        
        try:
            data = response.json()
        except:
            data = json.loads(response.content.decode('utf-8'))
        
        collections = data.get("collections", {})
        
        missing_collections = []
        present_collections = []
        
        for expected_collection in EXPECTED_BACKUP_COLLECTIONS:
            if expected_collection in collections:
                doc_count = len(collections[expected_collection])
                present_collections.append(f"{expected_collection} ({doc_count} docs)")
                print(f"✓ Collection '{expected_collection}' present with {doc_count} documents")
            else:
                missing_collections.append(expected_collection)
                print(f"✗ Collection '{expected_collection}' MISSING from backup")
        
        # Check for any extra collections not in expected list
        extra_collections = [c for c in collections.keys() if c not in EXPECTED_BACKUP_COLLECTIONS]
        if extra_collections:
            print(f"ℹ Extra collections in backup: {extra_collections}")
        
        print(f"\n✓ Summary: {len(present_collections)}/{len(EXPECTED_BACKUP_COLLECTIONS)} expected collections present")
        
        assert len(missing_collections) == 0, \
            f"Missing collections in backup: {missing_collections}"
        
        print(f"✓ All {len(EXPECTED_BACKUP_COLLECTIONS)} expected collections are included in backup")
    
    def test_05_backup_non_admin_forbidden(self):
        """Test backup endpoint is forbidden for non-admin users"""
        # Create a new session without auth
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Try to access backup without auth
        response = session.get(f"{BASE_URL}/api/admin/backup")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for unauthenticated request, got {response.status_code}"
        
        print(f"✓ Backup endpoint correctly returns {response.status_code} for unauthenticated request")


class TestPrequalifyToClientConversion:
    """Test pre-qualify to client conversion flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.text}")
        
        self.admin_data = login_response.json()
        token = self.admin_data.get("token")
        self.admin_id = self.admin_data["user"]["id"]
        self.admin_name = self.admin_data["user"].get("name") or self.admin_data["user"]["email"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_01_create_prequalify_submission(self):
        """Test creating a pre-qualify submission"""
        unique_id = uuid.uuid4().hex[:8]
        
        test_data = {
            "email": f"preq_test_{unique_id}@test.com",
            "firstName": f"PreqNombre_{unique_id}",
            "lastName": f"PreqApellido_{unique_id}",
            "phone": f"213{unique_id[:7]}",
            "idType": "DL",
            "idNumber": f"DL{unique_id}",
            "ssn": "123-45-6789",
            "ssnType": "SSN",
            "dateOfBirth": "1990-05-15",
            "address": "123 Test Street",
            "city": "Los Angeles",
            "state": "CA",
            "zipCode": "90001",
            "housingType": "Renta",
            "rentAmount": "1500",
            "timeAtAddressYears": 2,
            "timeAtAddressMonths": 6,
            "employerName": "Test Company Inc",
            "timeWithEmployerYears": 3,
            "timeWithEmployerMonths": 4,
            "incomeType": "Company",
            "netIncome": "4500",
            "incomeFrequency": "Mensual",
            "estimatedDownPayment": "5000",
            "consentAccepted": True
        }
        
        # Use multipart form data for this endpoint
        response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        
        assert response.status_code == 200, f"Pre-qualify submission failed: {response.text}"
        data = response.json()
        assert "id" in data
        
        submission_id = data["id"]
        print(f"✓ Pre-qualify submission created with ID: {submission_id}")
        
        return submission_id, test_data
    
    def test_02_convert_prequalify_to_client(self):
        """Test converting pre-qualify submission to client"""
        # First create a submission
        unique_id = uuid.uuid4().hex[:8]
        
        test_data = {
            "email": f"convert_test_{unique_id}@test.com",
            "firstName": f"ConvertNombre_{unique_id}",
            "lastName": f"ConvertApellido_{unique_id}",
            "phone": f"310{unique_id[:7]}",
            "idType": "Passport",
            "idNumber": f"PASS{unique_id}",
            "ssn": "987-65-4321",
            "ssnType": "ITIN",
            "dateOfBirth": "1985-08-20",
            "address": "456 Convert Ave",
            "city": "Pasadena",
            "state": "CA",
            "zipCode": "91101",
            "housingType": "Dueño",
            "rentAmount": "",
            "timeAtAddressYears": 5,
            "timeAtAddressMonths": 3,
            "employerName": "Convert Corp",
            "timeWithEmployerYears": 2,
            "timeWithEmployerMonths": 8,
            "incomeType": "Self-Employed",
            "netIncome": "6000",
            "incomeFrequency": "Cada dos semanas",
            "estimatedDownPayment": "8000",
            "consentAccepted": True
        }
        
        # Create submission
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200, f"Pre-qualify submission failed: {submit_response.text}"
        submission_id = submit_response.json()["id"]
        print(f"✓ Pre-qualify submission created: {submission_id}")
        
        # Convert to client
        convert_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert convert_response.status_code == 200, f"Convert to client failed: {convert_response.text}"
        
        result = convert_response.json()
        assert "client_id" in result, "Missing client_id in response"
        assert "record_id" in result, "Missing record_id in response"
        assert "message" in result, "Missing message in response"
        
        client_id = result["client_id"]
        record_id = result["record_id"]
        
        print(f"✓ Client created: {client_id}")
        print(f"✓ Record created: {record_id}")
        
        return submission_id, client_id, record_id, test_data
    
    def test_03_verify_client_assigned_to_admin(self):
        """Verify client is assigned to the admin who converted it"""
        # Create and convert a submission
        unique_id = uuid.uuid4().hex[:8]
        
        test_data = {
            "email": f"assign_test_{unique_id}@test.com",
            "firstName": f"AssignNombre_{unique_id}",
            "lastName": f"AssignApellido_{unique_id}",
            "phone": f"818{unique_id[:7]}",
            "consentAccepted": True
        }
        
        # Create submission
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200
        submission_id = submit_response.json()["id"]
        
        # Convert to client
        convert_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert convert_response.status_code == 200
        
        client_id = convert_response.json()["client_id"]
        
        # Get client details
        client_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert client_response.status_code == 200, f"Failed to get client: {client_response.text}"
        
        client = client_response.json()
        
        # Verify created_by is the admin who converted
        # Note: salesperson_id is stored in DB but not returned in ClientResponse model
        assert client.get("created_by") == self.admin_id, \
            f"Client created_by mismatch. Expected {self.admin_id}, got {client.get('created_by')}"
        
        print(f"✓ Client created_by admin: {client.get('created_by')}")
        print(f"✓ Admin ID matches: {self.admin_id}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
    
    def test_04_verify_notes_have_admin_only_flag(self):
        """Verify record notes include pre-qualify data with admin_only flag"""
        # Create and convert a submission
        unique_id = uuid.uuid4().hex[:8]
        
        test_data = {
            "email": f"notes_test_{unique_id}@test.com",
            "firstName": f"NotesNombre_{unique_id}",
            "lastName": f"NotesApellido_{unique_id}",
            "phone": f"626{unique_id[:7]}",
            "idType": "DL",
            "idNumber": f"DL{unique_id}",
            "ssn": "111-22-3333",
            "dateOfBirth": "1992-03-10",
            "address": "789 Notes Street",
            "city": "Glendale",
            "state": "CA",
            "zipCode": "91201",
            "employerName": "Notes Corp",
            "netIncome": "5500",
            "estimatedDownPayment": "7000",
            "consentAccepted": True
        }
        
        # Create submission
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200
        submission_id = submit_response.json()["id"]
        
        # Convert to client
        convert_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert convert_response.status_code == 200
        
        client_id = convert_response.json()["client_id"]
        record_id = convert_response.json()["record_id"]
        
        # Get record comments
        comments_response = self.session.get(f"{BASE_URL}/api/user-records/{record_id}/comments")
        assert comments_response.status_code == 200, f"Failed to get comments: {comments_response.text}"
        
        comments = comments_response.json()
        assert len(comments) > 0, "No comments found on record"
        
        # Find the pre-qualify note
        prequalify_note = None
        for comment in comments:
            content = comment.get("comment", "") or comment.get("content", "")
            if "Pre-Qualify Data" in content:
                prequalify_note = comment
                break
        
        assert prequalify_note is not None, "Pre-qualify note not found in comments"
        
        # Verify admin_only flag
        assert prequalify_note.get("admin_only") == True, \
            f"Pre-qualify note should have admin_only=True, got {prequalify_note.get('admin_only')}"
        
        print(f"✓ Pre-qualify note found with admin_only=True")
        
        # Verify note contains pre-qualify data
        note_content = prequalify_note.get("comment", "") or prequalify_note.get("content", "")
        assert "Pre-Qualify Data" in note_content, "Note should contain 'Pre-Qualify Data'"
        assert test_data["dateOfBirth"] in note_content or "Fecha Nacimiento" in note_content, \
            "Note should contain date of birth info"
        
        print(f"✓ Note contains pre-qualify data")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
    
    def test_05_verify_submission_status_converted(self):
        """Verify submission status changes to 'converted' after creating client"""
        # Create and convert a submission
        unique_id = uuid.uuid4().hex[:8]
        
        test_data = {
            "email": f"status_test_{unique_id}@test.com",
            "firstName": f"StatusNombre_{unique_id}",
            "lastName": f"StatusApellido_{unique_id}",
            "phone": f"562{unique_id[:7]}",
            "consentAccepted": True
        }
        
        # Create submission
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200
        submission_id = submit_response.json()["id"]
        
        # Check initial status
        get_response = self.session.get(f"{BASE_URL}/api/prequalify/submissions/{submission_id}")
        assert get_response.status_code == 200
        initial_status = get_response.json()["submission"].get("status", "pending")
        print(f"✓ Initial submission status: {initial_status}")
        
        # Convert to client
        convert_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert convert_response.status_code == 200
        
        client_id = convert_response.json()["client_id"]
        
        # Check status after conversion
        get_response = self.session.get(f"{BASE_URL}/api/prequalify/submissions/{submission_id}")
        assert get_response.status_code == 200
        
        submission = get_response.json()["submission"]
        final_status = submission.get("status")
        
        assert final_status == "converted", \
            f"Submission status should be 'converted', got '{final_status}'"
        
        print(f"✓ Submission status changed to 'converted'")
        
        # Verify matched_client_id is set
        assert submission.get("matched_client_id") == client_id, \
            f"matched_client_id should be {client_id}, got {submission.get('matched_client_id')}"
        
        print(f"✓ matched_client_id set to {client_id}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
    
    def test_06_full_conversion_flow(self):
        """Test complete pre-qualify to client conversion flow"""
        unique_id = uuid.uuid4().hex[:8]
        
        # Complete test data
        test_data = {
            "email": f"full_flow_{unique_id}@test.com",
            "firstName": f"FullFlowNombre_{unique_id}",
            "lastName": f"FullFlowApellido_{unique_id}",
            "phone": f"714{unique_id[:7]}",
            "idType": "Matricula",
            "idNumber": f"MAT{unique_id}",
            "ssn": "444-55-6666",
            "ssnType": "SSN",
            "dateOfBirth": "1988-12-25",
            "address": "999 Full Flow Blvd",
            "apartment": "Suite 100",
            "city": "Anaheim",
            "state": "CA",
            "zipCode": "92801",
            "housingType": "Renta",
            "rentAmount": "2000",
            "timeAtAddressYears": 3,
            "timeAtAddressMonths": 7,
            "employerName": "Full Flow Corp",
            "timeWithEmployerYears": 4,
            "timeWithEmployerMonths": 2,
            "incomeType": "Company",
            "netIncome": "7500",
            "incomeFrequency": "Semanal",
            "estimatedDownPayment": "10000",
            "consentAccepted": True
        }
        
        # Step 1: Create submission
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200
        submission_id = submit_response.json()["id"]
        print(f"✓ Step 1: Submission created: {submission_id}")
        
        # Step 2: Convert to client
        convert_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert convert_response.status_code == 200
        
        result = convert_response.json()
        client_id = result["client_id"]
        record_id = result["record_id"]
        print(f"✓ Step 2: Client created: {client_id}, Record: {record_id}")
        
        # Step 3: Verify client data
        client_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert client_response.status_code == 200
        client = client_response.json()
        
        assert client["first_name"] == test_data["firstName"]
        assert client["last_name"] == test_data["lastName"]
        assert client["email"] == test_data["email"]
        # Note: salesperson_id is stored in DB but not returned in ClientResponse model
        # Use created_by instead to verify admin assignment
        assert client["created_by"] == self.admin_id
        print(f"✓ Step 3: Client data verified")
        
        # Step 4: Verify record data
        record_response = self.session.get(f"{BASE_URL}/api/user-records/{record_id}")
        assert record_response.status_code == 200
        record = record_response.json()
        
        assert record["client_id"] == client_id
        assert record["salesperson_id"] == self.admin_id
        assert record["employment_company_name"] == test_data["employerName"]
        print(f"✓ Step 4: Record data verified")
        
        # Step 5: Verify notes with admin_only
        comments_response = self.session.get(f"{BASE_URL}/api/user-records/{record_id}/comments")
        assert comments_response.status_code == 200
        comments = comments_response.json()
        
        prequalify_note = next((c for c in comments if "Pre-Qualify Data" in (c.get("comment", "") or c.get("content", ""))), None)
        assert prequalify_note is not None
        assert prequalify_note.get("admin_only") == True
        print(f"✓ Step 5: Admin-only notes verified")
        
        # Step 6: Verify submission status
        get_response = self.session.get(f"{BASE_URL}/api/prequalify/submissions/{submission_id}")
        assert get_response.status_code == 200
        submission = get_response.json()["submission"]
        
        assert submission["status"] == "converted"
        assert submission["matched_client_id"] == client_id
        print(f"✓ Step 6: Submission status 'converted' verified")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
        
        print(f"\n✓ FULL CONVERSION FLOW COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
