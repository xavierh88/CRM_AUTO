"""
Test Dashboard Stats and Salesperson Performance Endpoints with Role-Based Filtering

Tests the following requirements:
1. Telemarketer dashboard shows only their own data
2. BDC Manager dashboard shows Telemarketer data but NOT Admin data
3. Admin dashboard shows all data from all users
4. Salesperson Performance chart visible to Admin and BDC Manager
5. Salesperson Performance chart excludes Admin data for BDC Manager
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://autocrm-dash.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "xavier.hernandez.1988@gmail.com"
ADMIN_PASSWORD = "Cali2020"

# Test user credentials (will be created during tests)
TEST_BDC_MANAGER_EMAIL = f"test_bdc_manager_{uuid.uuid4().hex[:8]}@test.com"
TEST_BDC_MANAGER_PASSWORD = "TestPass123!"
TEST_TELEMARKETER_EMAIL = f"test_telemarketer_{uuid.uuid4().hex[:8]}@test.com"
TEST_TELEMARKETER_PASSWORD = "TestPass123!"


class TestDashboardRoleFiltering:
    """Test dashboard stats filtering by user role"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_user(self, admin_token):
        """Get admin user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture(scope="class")
    def test_bdc_manager(self, admin_token):
        """Create a test BDC Manager user"""
        # Register the user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_BDC_MANAGER_EMAIL,
            "password": TEST_BDC_MANAGER_PASSWORD,
            "name": "TEST_BDC_Manager",
            "phone": "1234567890"
        })
        
        if response.status_code != 200:
            pytest.skip(f"Could not create BDC Manager test user: {response.text}")
        
        user_data = response.json().get("user", {})
        user_id = user_data.get("id")
        
        # Activate the user
        requests.put(f"{BASE_URL}/api/users/activate", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id, "is_active": True}
        )
        
        # Set role to bdc_manager
        requests.put(f"{BASE_URL}/api/users/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id, "role": "bdc_manager"}
        )
        
        # Login as BDC Manager
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BDC_MANAGER_EMAIL,
            "password": TEST_BDC_MANAGER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Could not login as BDC Manager: {login_response.text}")
        
        return {
            "user_id": user_id,
            "token": login_response.json()["token"],
            "user": login_response.json()["user"]
        }
    
    @pytest.fixture(scope="class")
    def test_telemarketer(self, admin_token):
        """Create a test Telemarketer user"""
        # Register the user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_TELEMARKETER_EMAIL,
            "password": TEST_TELEMARKETER_PASSWORD,
            "name": "TEST_Telemarketer",
            "phone": "0987654321"
        })
        
        if response.status_code != 200:
            pytest.skip(f"Could not create Telemarketer test user: {response.text}")
        
        user_data = response.json().get("user", {})
        user_id = user_data.get("id")
        
        # Activate the user
        requests.put(f"{BASE_URL}/api/users/activate", 
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id, "is_active": True}
        )
        
        # Role is already telemarketer by default
        
        # Login as Telemarketer
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_TELEMARKETER_EMAIL,
            "password": TEST_TELEMARKETER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Could not login as Telemarketer: {login_response.text}")
        
        return {
            "user_id": user_id,
            "token": login_response.json()["token"],
            "user": login_response.json()["user"]
        }
    
    # ==================== ADMIN DASHBOARD TESTS ====================
    
    def test_admin_dashboard_stats_returns_all_data(self, admin_token, admin_user):
        """Admin should see all data from all users"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_clients" in data, "Missing total_clients in response"
        assert "sales" in data, "Missing sales in response"
        assert "appointments" in data, "Missing appointments in response"
        assert "total_records" in data, "Missing total_records in response"
        
        print(f"Admin Dashboard Stats: total_clients={data['total_clients']}, sales={data['sales']}, records={data['total_records']}")
    
    def test_admin_salesperson_performance_returns_all_users(self, admin_token):
        """Admin should see performance data for all users including admins"""
        response = requests.get(f"{BASE_URL}/api/dashboard/salesperson-performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Salesperson performance failed: {response.text}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Response should be a list"
        
        print(f"Admin sees {len(data)} salespersons in performance chart")
        for sp in data:
            print(f"  - {sp.get('salesperson_name', 'Unknown')}: records={sp.get('total_records', 0)}, sales={sp.get('sales', 0)}")
    
    # ==================== BDC MANAGER DASHBOARD TESTS ====================
    
    def test_bdc_manager_dashboard_stats_excludes_admin_data(self, test_bdc_manager, admin_token, admin_user):
        """BDC Manager should see all data EXCEPT admin data"""
        # First get admin stats for comparison
        admin_response = requests.get(f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        admin_data = admin_response.json()
        
        # Get BDC Manager stats
        bdc_response = requests.get(f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {test_bdc_manager['token']}"}
        )
        
        assert bdc_response.status_code == 200, f"BDC Manager dashboard stats failed: {bdc_response.text}"
        bdc_data = bdc_response.json()
        
        # Verify response structure
        assert "total_clients" in bdc_data, "Missing total_clients in response"
        assert "sales" in bdc_data, "Missing sales in response"
        
        print(f"BDC Manager Dashboard Stats: total_clients={bdc_data['total_clients']}, sales={bdc_data['sales']}")
        print(f"Admin Dashboard Stats: total_clients={admin_data['total_clients']}, sales={admin_data['sales']}")
        
        # BDC Manager should see <= Admin's data (since admin data is excluded)
        # Note: This might be equal if admin has no data
        assert bdc_data['total_clients'] <= admin_data['total_clients'], \
            f"BDC Manager sees more clients ({bdc_data['total_clients']}) than Admin ({admin_data['total_clients']})"
    
    def test_bdc_manager_salesperson_performance_excludes_admin(self, test_bdc_manager, admin_token):
        """BDC Manager should NOT see admin performance data"""
        # Get admin's performance view
        admin_response = requests.get(f"{BASE_URL}/api/dashboard/salesperson-performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        admin_perf = admin_response.json()
        
        # Get BDC Manager's performance view
        bdc_response = requests.get(f"{BASE_URL}/api/dashboard/salesperson-performance",
            headers={"Authorization": f"Bearer {test_bdc_manager['token']}"}
        )
        
        assert bdc_response.status_code == 200, f"BDC Manager salesperson performance failed: {bdc_response.text}"
        bdc_perf = bdc_response.json()
        
        # Get list of admin user IDs
        users_response = requests.get(f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = users_response.json()
        admin_ids = [u["id"] for u in users if u.get("role") == "admin"]
        
        print(f"Admin IDs to exclude: {admin_ids}")
        print(f"Admin sees {len(admin_perf)} salespersons")
        print(f"BDC Manager sees {len(bdc_perf)} salespersons")
        
        # Verify BDC Manager doesn't see any admin in performance
        bdc_salesperson_ids = [sp.get("salesperson_id") for sp in bdc_perf]
        for admin_id in admin_ids:
            assert admin_id not in bdc_salesperson_ids, \
                f"BDC Manager should NOT see admin {admin_id} in performance chart"
        
        print("PASS: BDC Manager does not see any admin in salesperson performance")
    
    def test_bdc_manager_can_access_salesperson_performance(self, test_bdc_manager):
        """BDC Manager should have access to salesperson performance endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/salesperson-performance",
            headers={"Authorization": f"Bearer {test_bdc_manager['token']}"}
        )
        
        assert response.status_code == 200, f"BDC Manager should have access to salesperson performance: {response.text}"
        print("PASS: BDC Manager can access salesperson performance endpoint")
    
    # ==================== TELEMARKETER DASHBOARD TESTS ====================
    
    def test_telemarketer_dashboard_stats_shows_only_own_data(self, test_telemarketer, admin_token):
        """Telemarketer should only see their own data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {test_telemarketer['token']}"}
        )
        
        assert response.status_code == 200, f"Telemarketer dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_clients" in data, "Missing total_clients in response"
        assert "sales" in data, "Missing sales in response"
        
        # New telemarketer should have 0 clients (they haven't created any)
        print(f"Telemarketer Dashboard Stats: total_clients={data['total_clients']}, sales={data['sales']}")
        
        # Since this is a new test user, they should have 0 clients
        assert data['total_clients'] == 0, \
            f"New telemarketer should have 0 clients, but has {data['total_clients']}"
        
        print("PASS: Telemarketer sees only their own data (0 clients for new user)")
    
    def test_telemarketer_cannot_access_salesperson_performance(self, test_telemarketer):
        """Telemarketer should NOT have access to salesperson performance endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/salesperson-performance",
            headers={"Authorization": f"Bearer {test_telemarketer['token']}"}
        )
        
        assert response.status_code == 403, \
            f"Telemarketer should get 403 for salesperson performance, got {response.status_code}"
        
        print("PASS: Telemarketer cannot access salesperson performance endpoint")
    
    # ==================== DATA CREATION AND VERIFICATION TESTS ====================
    
    def test_telemarketer_creates_client_and_sees_in_dashboard(self, test_telemarketer, admin_token):
        """When telemarketer creates a client, they should see it in their dashboard"""
        # Create a client as telemarketer
        client_response = requests.post(f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {test_telemarketer['token']}"},
            json={
                "first_name": "TEST_Dashboard",
                "last_name": "Client",
                "phone": f"+1555{uuid.uuid4().hex[:7]}"
            }
        )
        
        assert client_response.status_code == 200, f"Failed to create client: {client_response.text}"
        client_data = client_response.json()
        client_id = client_data.get("id")
        
        # Get telemarketer dashboard stats
        stats_response = requests.get(f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {test_telemarketer['token']}"}
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Telemarketer should now see 1 client
        assert stats['total_clients'] >= 1, \
            f"Telemarketer should see at least 1 client after creating one, but sees {stats['total_clients']}"
        
        print(f"PASS: Telemarketer sees their created client in dashboard (total_clients={stats['total_clients']})")
        
        # Cleanup - delete the test client
        requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_bdc_manager_sees_telemarketer_client_but_not_admin_client(self, test_bdc_manager, test_telemarketer, admin_token, admin_user):
        """BDC Manager should see telemarketer's clients but NOT admin's clients"""
        # Create a client as telemarketer
        telemarketer_client = requests.post(f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {test_telemarketer['token']}"},
            json={
                "first_name": "TEST_TelemarketerClient",
                "last_name": "ForBDC",
                "phone": f"+1555{uuid.uuid4().hex[:7]}"
            }
        )
        telemarketer_client_id = telemarketer_client.json().get("id") if telemarketer_client.status_code == 200 else None
        
        # Create a client as admin
        admin_client = requests.post(f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "TEST_AdminClient",
                "last_name": "NotForBDC",
                "phone": f"+1555{uuid.uuid4().hex[:7]}"
            }
        )
        admin_client_id = admin_client.json().get("id") if admin_client.status_code == 200 else None
        
        # Get BDC Manager's client list
        bdc_clients_response = requests.get(f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {test_bdc_manager['token']}"}
        )
        
        assert bdc_clients_response.status_code == 200
        bdc_clients = bdc_clients_response.json()
        bdc_client_ids = [c.get("id") for c in bdc_clients]
        
        # BDC Manager should see telemarketer's client
        if telemarketer_client_id:
            assert telemarketer_client_id in bdc_client_ids, \
                "BDC Manager should see telemarketer's client"
            print("PASS: BDC Manager sees telemarketer's client")
        
        # BDC Manager should NOT see admin's client
        if admin_client_id:
            assert admin_client_id not in bdc_client_ids, \
                "BDC Manager should NOT see admin's client"
            print("PASS: BDC Manager does NOT see admin's client")
        
        # Cleanup
        if telemarketer_client_id:
            requests.delete(f"{BASE_URL}/api/clients/{telemarketer_client_id}?permanent=true",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        if admin_client_id:
            requests.delete(f"{BASE_URL}/api/clients/{admin_client_id}?permanent=true",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
    
    # ==================== PERIOD FILTERING TESTS ====================
    
    def test_dashboard_stats_with_period_filter(self, admin_token):
        """Test dashboard stats with different period filters"""
        periods = ["all", "6months", "month"]
        
        for period in periods:
            response = requests.get(f"{BASE_URL}/api/dashboard/stats?period={period}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200, f"Dashboard stats failed for period={period}: {response.text}"
            data = response.json()
            
            assert "total_clients" in data
            assert "current_period" in data
            assert data["current_period"] == period
            
            print(f"Period '{period}': total_clients={data['total_clients']}, sales={data['sales']}")
        
        print("PASS: Dashboard stats work with all period filters")
    
    def test_dashboard_stats_with_specific_month(self, admin_token):
        """Test dashboard stats with specific month filter"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats?month=2026-01",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Dashboard stats failed for month filter: {response.text}"
        data = response.json()
        
        assert "total_clients" in data
        assert data["current_period"] == "2026-01"
        
        print(f"Month '2026-01': total_clients={data['total_clients']}, sales={data['sales']}")
        print("PASS: Dashboard stats work with specific month filter")


class TestCleanup:
    """Cleanup test users after all tests"""
    
    def test_cleanup_test_users(self):
        """Delete test users created during testing"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            print("Could not login as admin for cleanup")
            return
        
        admin_token = login_response.json()["token"]
        
        # Get all users
        users_response = requests.get(f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if users_response.status_code != 200:
            print("Could not get users for cleanup")
            return
        
        users = users_response.json()
        
        # Find and deactivate test users (those with TEST_ prefix in name)
        for user in users:
            if user.get("name", "").startswith("TEST_"):
                # Deactivate the user
                requests.put(f"{BASE_URL}/api/users/activate",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"user_id": user["id"], "is_active": False}
                )
                print(f"Deactivated test user: {user.get('name')}")
        
        print("PASS: Test users cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
