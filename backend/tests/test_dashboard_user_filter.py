"""
Test suite for Dashboard User Filter and Document Upload/Download features
Tests:
1. Dashboard stats API with user_id parameter (Admin only)
2. Client documents upload
3. Client documents download
4. PreQualify to Client conversion with document transfer
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "xavier.hernandez.1988@gmail.com"
ADMIN_PASSWORD = "Cali2020"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        print(f"✓ Admin login successful, token obtained")


class TestDashboardUserFilter:
    """Test Dashboard stats with user_id filter (Admin only feature)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_dashboard_stats_without_user_filter(self, admin_headers):
        """Test dashboard stats returns all data when no user_id filter"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_clients" in data
        assert "sales" in data
        assert "appointments" in data
        
        print(f"✓ Dashboard stats (no filter): {data['total_clients']} clients, {data['sales']} sales")
    
    def test_get_users_list(self, admin_headers):
        """Get list of users to use for filtering"""
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        users = response.json()
        
        # Filter to get telemarketers/bdc_managers
        filtered_users = [u for u in users if u.get('role') in ['telemarketer', 'bdc_manager', 'salesperson']]
        print(f"✓ Found {len(filtered_users)} users available for filtering")
        
        return filtered_users
    
    def test_dashboard_stats_with_user_filter(self, admin_headers):
        """Test dashboard stats with user_id parameter filters correctly"""
        # First get users
        users_response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert users_response.status_code == 200
        users = users_response.json()
        
        # Find a telemarketer or bdc_manager
        test_user = None
        for u in users:
            if u.get('role') in ['telemarketer', 'bdc_manager', 'salesperson'] and u.get('is_active'):
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No active telemarketer/bdc_manager found for testing")
        
        # Get stats without filter
        response_all = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=admin_headers)
        assert response_all.status_code == 200
        stats_all = response_all.json()
        
        # Get stats with user filter
        response_filtered = requests.get(
            f"{BASE_URL}/api/dashboard/stats?user_id={test_user['id']}", 
            headers=admin_headers
        )
        assert response_filtered.status_code == 200, f"Failed: {response_filtered.text}"
        stats_filtered = response_filtered.json()
        
        # Filtered stats should be <= total stats
        assert stats_filtered['total_clients'] <= stats_all['total_clients'], \
            f"Filtered clients ({stats_filtered['total_clients']}) should be <= total ({stats_all['total_clients']})"
        
        print(f"✓ Dashboard stats with user_id filter: {stats_filtered['total_clients']} clients for user {test_user['name']}")
        print(f"  (Total without filter: {stats_all['total_clients']} clients)")
    
    def test_dashboard_stats_with_invalid_user_id(self, admin_headers):
        """Test dashboard stats with non-existent user_id returns empty/zero stats"""
        fake_user_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?user_id={fake_user_id}", 
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return 0 clients for non-existent user
        assert data['total_clients'] == 0, f"Expected 0 clients for fake user, got {data['total_clients']}"
        print(f"✓ Dashboard stats with invalid user_id returns 0 clients")


class TestClientDocuments:
    """Test client document upload and download"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture(scope="class")
    def test_client(self, admin_headers):
        """Create a test client for document testing"""
        unique_phone = f"+1555{datetime.now().strftime('%H%M%S%f')[:7]}"
        client_data = {
            "first_name": "TEST_DocUpload",
            "last_name": "TestClient",
            "phone": unique_phone,
            "email": f"test_doc_{uuid.uuid4().hex[:8]}@test.com"
        }
        response = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create test client: {response.text}"
        client = response.json()
        
        # Handle case where client already exists
        if "error" in client:
            pytest.skip(f"Client creation returned error: {client}")
        
        print(f"✓ Created test client: {client['id']}")
        yield client
        
        # Cleanup - delete test client
        try:
            requests.delete(f"{BASE_URL}/api/clients/{client['id']}?permanent=true", headers=admin_headers)
            print(f"✓ Cleaned up test client: {client['id']}")
        except:
            pass
    
    def test_upload_id_document(self, admin_headers, test_client):
        """Test uploading ID document for a client"""
        client_id = test_client['id']
        
        # Create a simple test file (PDF-like content)
        test_content = b"%PDF-1.4 Test PDF content for ID document"
        files = {
            'files': ('test_id.pdf', test_content, 'application/pdf')
        }
        data = {'doc_type': 'id'}
        
        # Remove Content-Type from headers for multipart upload
        headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        assert "message" in result
        assert "files" in result
        assert len(result["files"]) > 0
        
        print(f"✓ ID document uploaded successfully: {result['message']}")
        return result
    
    def test_upload_income_document(self, admin_headers, test_client):
        """Test uploading income proof document"""
        client_id = test_client['id']
        
        test_content = b"%PDF-1.4 Test PDF content for income proof"
        files = {
            'files': ('test_income.pdf', test_content, 'application/pdf')
        }
        data = {'doc_type': 'income'}
        
        headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        print(f"✓ Income document uploaded successfully: {result['message']}")
    
    def test_upload_residence_document(self, admin_headers, test_client):
        """Test uploading residence proof document"""
        client_id = test_client['id']
        
        test_content = b"%PDF-1.4 Test PDF content for residence proof"
        files = {
            'files': ('test_residence.pdf', test_content, 'application/pdf')
        }
        data = {'doc_type': 'residence'}
        
        headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        print(f"✓ Residence document uploaded successfully: {result['message']}")
    
    def test_list_documents(self, admin_headers, test_client):
        """Test listing documents for a client"""
        client_id = test_client['id']
        
        # First upload a document
        test_content = b"%PDF-1.4 Test PDF"
        files = {'files': ('test.pdf', test_content, 'application/pdf')}
        data = {'doc_type': 'id'}
        headers = {"Authorization": admin_headers["Authorization"]}
        
        requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files, data=data, headers=headers
        )
        
        # Now list documents
        response = requests.get(
            f"{BASE_URL}/api/clients/{client_id}/documents/list/id",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"List failed: {response.text}"
        result = response.json()
        
        assert "documents" in result
        assert "count" in result
        
        print(f"✓ Listed {result['count']} ID documents for client")
    
    def test_download_document(self, admin_headers, test_client):
        """Test downloading a document"""
        client_id = test_client['id']
        
        # First upload a document
        test_content = b"%PDF-1.4 Test PDF content for download test"
        files = {'files': ('download_test.pdf', test_content, 'application/pdf')}
        data = {'doc_type': 'id'}
        headers = {"Authorization": admin_headers["Authorization"]}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files, data=data, headers=headers
        )
        assert upload_response.status_code == 200
        
        # Now try to download
        response = requests.get(
            f"{BASE_URL}/api/clients/{client_id}/documents/download/id",
            headers=admin_headers
        )
        
        # Should return 200 with PDF content or combined PDF
        assert response.status_code == 200, f"Download failed: {response.status_code} - {response.text[:200]}"
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        assert 'pdf' in content_type.lower() or 'octet-stream' in content_type.lower(), \
            f"Expected PDF content type, got: {content_type}"
        
        print(f"✓ Document download successful, content-type: {content_type}")
    
    def test_upload_invalid_doc_type(self, admin_headers, test_client):
        """Test uploading with invalid document type returns error"""
        client_id = test_client['id']
        
        test_content = b"%PDF-1.4 Test"
        files = {'files': ('test.pdf', test_content, 'application/pdf')}
        data = {'doc_type': 'invalid_type'}
        headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/documents/upload",
            files=files, data=data, headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid doc_type, got {response.status_code}"
        print(f"✓ Invalid doc_type correctly returns 400 error")


class TestPreQualifyConversion:
    """Test PreQualify to Client conversion with document transfer"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_get_prequalify_submissions(self, admin_headers):
        """Test getting prequalify submissions list"""
        response = requests.get(f"{BASE_URL}/api/prequalify/submissions", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        submissions = response.json()
        
        print(f"✓ Found {len(submissions)} prequalify submissions")
        return submissions
    
    def test_prequalify_submission_detail(self, admin_headers):
        """Test getting a specific prequalify submission"""
        # First get list
        list_response = requests.get(f"{BASE_URL}/api/prequalify/submissions", headers=admin_headers)
        assert list_response.status_code == 200
        submissions = list_response.json()
        
        if not submissions:
            pytest.skip("No prequalify submissions available for testing")
        
        # Get first submission detail
        submission_id = submissions[0]['id']
        response = requests.get(
            f"{BASE_URL}/api/prequalify/submissions/{submission_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "submission" in data
        print(f"✓ Got prequalify submission detail: {submission_id}")
    
    def test_prequalify_to_client_conversion_endpoint_exists(self, admin_headers):
        """Test that the prequalify to client conversion endpoint exists"""
        # We'll test with a fake ID to verify endpoint exists
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/prequalify/submissions/{fake_id}/create-client",
            headers=admin_headers
        )
        
        # Should return 404 (not found) not 405 (method not allowed)
        assert response.status_code in [404, 400], \
            f"Expected 404 or 400 for non-existent submission, got {response.status_code}"
        
        print(f"✓ PreQualify to Client conversion endpoint exists and responds correctly")


class TestDashboardStatsIntegration:
    """Integration tests for dashboard stats with various filters"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_dashboard_stats_with_period_filter(self, admin_headers):
        """Test dashboard stats with period filter"""
        for period in ['all', '6months', 'month']:
            response = requests.get(
                f"{BASE_URL}/api/dashboard/stats?period={period}",
                headers=admin_headers
            )
            assert response.status_code == 200, f"Failed for period={period}: {response.text}"
            data = response.json()
            assert "total_clients" in data
            print(f"✓ Dashboard stats with period={period}: {data['total_clients']} clients")
    
    def test_dashboard_stats_with_month_filter(self, admin_headers):
        """Test dashboard stats with specific month filter"""
        # Use current month
        current_month = datetime.now().strftime("%Y-%m")
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?month={current_month}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        print(f"✓ Dashboard stats for month {current_month}: {data['total_clients']} clients")
    
    def test_dashboard_stats_combined_filters(self, admin_headers):
        """Test dashboard stats with user_id and period combined"""
        # Get a user first
        users_response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert users_response.status_code == 200
        users = users_response.json()
        
        test_user = None
        for u in users:
            if u.get('role') in ['telemarketer', 'bdc_manager'] and u.get('is_active'):
                test_user = u
                break
        
        if not test_user:
            pytest.skip("No active user found for combined filter test")
        
        # Test with both user_id and period
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?user_id={test_user['id']}&period=6months",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        print(f"✓ Dashboard stats with user_id + period filter: {data['total_clients']} clients")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
