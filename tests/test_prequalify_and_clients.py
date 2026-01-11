"""
Test suite for Pre-Qualify and Client functionality
Tests:
1. Pre-qualify submission with separated time fields (timeAtAddressYears/Months, timeWithEmployerYears/Months)
2. Create client from pre-qualify - verify data mapping
3. Client CRUD with time_at_address_years/months fields
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@carplus.com"
ADMIN_PASSWORD = "Cali2020"

class TestPrequalifyAndClients:
    """Test Pre-Qualify submission and Client creation with separated time fields"""
    
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
        self.test_phone = f"+1213{uuid.uuid4().hex[:7]}"
        
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
        print(f"✓ Admin login successful")
    
    def test_02_prequalify_submit_with_separated_time_fields(self):
        """Test pre-qualify submission accepts separated time fields"""
        unique_id = uuid.uuid4().hex[:8]
        test_data = {
            "email": f"test_{unique_id}@test.com",
            "firstName": f"TestNombre_{unique_id}",
            "lastName": f"TestApellido_{unique_id}",
            "phone": f"213{unique_id[:7]}",
            "idNumber": "A12345678",
            "ssn": "123-45-6789",
            "dateOfBirth": "1990-05-15",
            "address": "123 Test Street",
            "city": "Los Angeles",
            "state": "CA",
            "zipCode": "90001",
            "housingType": "Renta",
            "rentAmount": "1500",
            # Separated time at address fields
            "timeAtAddressYears": 2,
            "timeAtAddressMonths": 6,
            "employerName": "Test Company Inc",
            # Separated time with employer fields
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
            headers={"Content-Type": None}  # Let requests set the correct content type
        )
        
        assert response.status_code == 200, f"Pre-qualify submission failed: {response.text}"
        data = response.json()
        assert "id" in data
        self.submission_id = data["id"]
        print(f"✓ Pre-qualify submission created with ID: {self.submission_id}")
        
        # Verify the submission was stored correctly
        get_response = self.session.get(f"{BASE_URL}/api/prequalify/submissions/{self.submission_id}")
        assert get_response.status_code == 200, f"Failed to get submission: {get_response.text}"
        
        submission_data = get_response.json()["submission"]
        
        # Verify separated time fields are stored
        assert submission_data.get("timeAtAddressYears") == 2, f"timeAtAddressYears not stored correctly: {submission_data.get('timeAtAddressYears')}"
        assert submission_data.get("timeAtAddressMonths") == 6, f"timeAtAddressMonths not stored correctly: {submission_data.get('timeAtAddressMonths')}"
        assert submission_data.get("timeWithEmployerYears") == 3, f"timeWithEmployerYears not stored correctly: {submission_data.get('timeWithEmployerYears')}"
        assert submission_data.get("timeWithEmployerMonths") == 4, f"timeWithEmployerMonths not stored correctly: {submission_data.get('timeWithEmployerMonths')}"
        
        print(f"✓ Time fields stored correctly: Address={submission_data.get('timeAtAddressYears')}y {submission_data.get('timeAtAddressMonths')}m, Employer={submission_data.get('timeWithEmployerYears')}y {submission_data.get('timeWithEmployerMonths')}m")
        
        return self.submission_id
    
    def test_03_create_client_from_prequalify(self):
        """Test creating client from pre-qualify maps all fields correctly"""
        # First create a pre-qualify submission
        unique_id = uuid.uuid4().hex[:8]
        test_data = {
            "email": f"client_{unique_id}@test.com",
            "firstName": f"ClientNombre_{unique_id}",
            "lastName": f"ClientApellido_{unique_id}",
            "phone": f"310{unique_id[:7]}",
            "idNumber": "B98765432",
            "dateOfBirth": "1985-08-20",
            "address": "456 Client Ave",
            "city": "Pasadena",
            "state": "CA",
            "zipCode": "91101",
            "housingType": "Dueño",
            "rentAmount": "",
            "timeAtAddressYears": 5,
            "timeAtAddressMonths": 3,
            "employerName": "Client Corp",
            "timeWithEmployerYears": 2,
            "timeWithEmployerMonths": 8,
            "incomeType": "Company",
            "netIncome": "6000",
            "incomeFrequency": "Cada dos semanas",
            "estimatedDownPayment": "8000",
            "consentAccepted": True
        }
        
        # Submit pre-qualify
        submit_response = self.session.post(
            f"{BASE_URL}/api/prequalify/submit-with-file",
            data=test_data,
            headers={"Content-Type": None}
        )
        assert submit_response.status_code == 200, f"Pre-qualify submission failed: {submit_response.text}"
        submission_id = submit_response.json()["id"]
        print(f"✓ Pre-qualify submission created: {submission_id}")
        
        # Create client from pre-qualify
        create_response = self.session.post(f"{BASE_URL}/api/prequalify/submissions/{submission_id}/create-client")
        assert create_response.status_code == 200, f"Create client failed: {create_response.text}"
        
        result = create_response.json()
        client_id = result["client_id"]
        record_id = result["record_id"]
        print(f"✓ Client created: {client_id}, Record: {record_id}")
        
        # Verify client data
        client_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert client_response.status_code == 200, f"Failed to get client: {client_response.text}"
        
        client = client_response.json()
        
        # Verify time at address fields are mapped to client
        assert client.get("time_at_address_years") == 5, f"Client time_at_address_years incorrect: {client.get('time_at_address_years')}"
        assert client.get("time_at_address_months") == 3, f"Client time_at_address_months incorrect: {client.get('time_at_address_months')}"
        assert client.get("housing_type") == "Dueño", f"Client housing_type incorrect: {client.get('housing_type')}"
        assert client.get("date_of_birth") == "1985-08-20", f"Client date_of_birth incorrect: {client.get('date_of_birth')}"
        
        print(f"✓ Client time at address: {client.get('time_at_address_years')} years, {client.get('time_at_address_months')} months")
        
        # Verify record data
        record_response = self.session.get(f"{BASE_URL}/api/user-records/{record_id}")
        assert record_response.status_code == 200, f"Failed to get record: {record_response.text}"
        
        record = record_response.json()
        
        # Verify employment time fields are mapped to record
        assert record.get("employment_time_years") == 2, f"Record employment_time_years incorrect: {record.get('employment_time_years')}"
        assert record.get("employment_time_months") == 8, f"Record employment_time_months incorrect: {record.get('employment_time_months')}"
        assert record.get("employment_company_name") == "Client Corp", f"Record employment_company_name incorrect: {record.get('employment_company_name')}"
        
        print(f"✓ Record employment time: {record.get('employment_time_years')} years, {record.get('employment_time_months')} months")
        
        # Verify notes contain formatted time
        comments_response = self.session.get(f"{BASE_URL}/api/user-records/{record_id}/comments")
        assert comments_response.status_code == 200, f"Failed to get comments: {comments_response.text}"
        
        comments = comments_response.json()
        if comments:
            note_content = comments[0].get("comment", "") or comments[0].get("content", "")
            # Check for formatted time strings
            assert "5 años, 3 meses" in note_content or "5 yrs" in note_content or "Tiempo en Dirección" in note_content, f"Note doesn't contain time at address info: {note_content[:200]}"
            assert "2 años, 8 meses" in note_content or "2 yrs" in note_content or "Tiempo con Empleador" in note_content, f"Note doesn't contain employer time info: {note_content[:200]}"
            print(f"✓ Notes contain formatted time information")
        
        # Cleanup - delete the test client
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
        
        return client_id
    
    def test_04_client_crud_with_time_fields(self):
        """Test client CRUD operations with time_at_address fields"""
        unique_id = uuid.uuid4().hex[:8]
        
        # Create client with time fields
        client_data = {
            "first_name": f"TEST_CRUDNombre_{unique_id}",
            "last_name": f"TEST_CRUDApellido_{unique_id}",
            "phone": f"818{unique_id[:7]}",
            "email": f"crud_{unique_id}@test.com",
            "address": "789 CRUD Street",
            "apartment": "Apt 5B",
            "date_of_birth": "1992-03-10",
            "time_at_address_years": 1,
            "time_at_address_months": 9,
            "housing_type": "Renta",
            "rent_amount": "2000"
        }
        
        # Create
        create_response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert create_response.status_code == 200, f"Create client failed: {create_response.text}"
        
        created_client = create_response.json()
        client_id = created_client["id"]
        
        # Verify created data
        assert created_client["time_at_address_years"] == 1
        assert created_client["time_at_address_months"] == 9
        assert created_client["housing_type"] == "Renta"
        assert created_client["rent_amount"] == "2000"
        assert created_client["apartment"] == "Apt 5B"
        print(f"✓ Client created with time fields: {client_id}")
        
        # Read
        get_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 200
        fetched_client = get_response.json()
        assert fetched_client["time_at_address_years"] == 1
        assert fetched_client["time_at_address_months"] == 9
        print(f"✓ Client read verified")
        
        # Update
        update_data = {
            **client_data,
            "time_at_address_years": 3,
            "time_at_address_months": 2,
            "housing_type": "Dueño",
            "rent_amount": ""
        }
        update_response = self.session.put(f"{BASE_URL}/api/clients/{client_id}", json=update_data)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        updated_client = update_response.json()
        assert updated_client["time_at_address_years"] == 3
        assert updated_client["time_at_address_months"] == 2
        assert updated_client["housing_type"] == "Dueño"
        print(f"✓ Client updated with new time fields")
        
        # Delete
        delete_response = self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")
        assert delete_response.status_code == 200
        print(f"✓ Client deleted")
        
        # Verify deletion
        verify_response = self.session.get(f"{BASE_URL}/api/clients/{client_id}")
        assert verify_response.status_code == 404
        print(f"✓ Client deletion verified")
    
    def test_05_prequalify_submissions_list(self):
        """Test listing pre-qualify submissions"""
        response = self.session.get(f"{BASE_URL}/api/prequalify/submissions")
        assert response.status_code == 200, f"Failed to list submissions: {response.text}"
        
        submissions = response.json()
        assert isinstance(submissions, list)
        print(f"✓ Pre-qualify submissions list: {len(submissions)} submissions found")
        
        # Check that submissions have the expected fields
        if submissions:
            sample = submissions[0]
            expected_fields = ["id", "firstName", "lastName", "phone", "email", "status"]
            for field in expected_fields:
                assert field in sample, f"Missing field {field} in submission"
            print(f"✓ Submission structure verified")


class TestClientModals:
    """Test client modal functionality - Add Client and Client Info"""
    
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
    
    def test_01_add_client_all_fields(self):
        """Test adding client with all fields including time at address"""
        unique_id = uuid.uuid4().hex[:8]
        
        client_data = {
            "first_name": f"TEST_Modal_{unique_id}",
            "last_name": f"TEST_Apellido_{unique_id}",
            "phone": f"626{unique_id[:7]}",
            "email": f"modal_{unique_id}@test.com",
            "address": "100 Modal Test Blvd",
            "apartment": "Suite 200",
            "date_of_birth": "1988-12-25",
            "time_at_address_years": 4,
            "time_at_address_months": 7,
            "housing_type": "Vivo con familiares",
            "rent_amount": ""
        }
        
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert response.status_code == 200, f"Failed to create client: {response.text}"
        
        client = response.json()
        
        # Verify all fields
        assert client["first_name"] == client_data["first_name"]
        assert client["last_name"] == client_data["last_name"]
        assert client["email"] == client_data["email"]
        assert client["address"] == client_data["address"]
        assert client["apartment"] == client_data["apartment"]
        assert client["date_of_birth"] == client_data["date_of_birth"]
        assert client["time_at_address_years"] == 4
        assert client["time_at_address_months"] == 7
        assert client["housing_type"] == "Vivo con familiares"
        
        print(f"✓ Client created with all modal fields")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client['id']}?permanent=true")
    
    def test_02_update_client_time_fields(self):
        """Test updating client time at address fields (Client Info modal edit mode)"""
        unique_id = uuid.uuid4().hex[:8]
        
        # Create initial client
        client_data = {
            "first_name": f"TEST_Edit_{unique_id}",
            "last_name": f"TEST_EditLast_{unique_id}",
            "phone": f"562{unique_id[:7]}",
            "email": f"edit_{unique_id}@test.com",
            "time_at_address_years": 1,
            "time_at_address_months": 0,
            "housing_type": "Renta",
            "rent_amount": "1200"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        
        # Update with new values (simulating edit mode save)
        update_data = {
            **client_data,
            "time_at_address_years": 6,
            "time_at_address_months": 11,
            "housing_type": "Dueño",
            "rent_amount": ""
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/clients/{client_id}", json=update_data)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        updated = update_response.json()
        assert updated["time_at_address_years"] == 6
        assert updated["time_at_address_months"] == 11
        assert updated["housing_type"] == "Dueño"
        
        print(f"✓ Client time fields updated successfully")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
