import requests
import sys
import json
from datetime import datetime

class AdminFeaturesAPITester:
    def __init__(self, base_url="https://dealconcierge.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.admin_id = None
        self.client_id = None
        self.bank_id = None
        self.dealer_id = None
        self.car_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_admin_login(self):
        """Test admin login with xadmin/Cali2020"""
        success, response = self.run_test(
            "Admin Login (xadmin/Cali2020)",
            "POST",
            "auth/login",
            200,
            data={
                "email": "xadmin",
                "password": "Cali2020"
            }
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.admin_id = response['user']['id']
            return True
        return False

    def test_get_banks_list(self):
        """Test getting banks list - should have 33+ US banks"""
        success, response = self.run_test(
            "Get Banks List",
            "GET",
            "config-lists/bank",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} banks in the list")
            if len(response) >= 33:
                print(f"✅ Confirmed: Banks list has 33+ items ({len(response)} banks)")
                # Check for some expected US banks
                bank_names = [bank['name'] for bank in response]
                expected_banks = ['Chase', 'Bank of America', 'Wells Fargo', 'Citibank']
                found_banks = [bank for bank in expected_banks if bank in bank_names]
                print(f"✅ Found expected US banks: {found_banks}")
                return True
            else:
                print(f"❌ Expected 33+ banks, found {len(response)}")
        return False

    def test_get_dealers_list(self):
        """Test getting dealers list - should have Downey and Long Beach"""
        success, response = self.run_test(
            "Get Dealers List",
            "GET",
            "config-lists/dealer",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} dealers in the list")
            dealer_names = [dealer['name'] for dealer in response]
            expected_dealers = ['Downey', 'Long Beach']
            found_dealers = [dealer for dealer in expected_dealers if dealer in dealer_names]
            if len(found_dealers) >= 2:
                print(f"✅ Confirmed: Found expected dealers: {found_dealers}")
                return True
            else:
                print(f"❌ Expected Downey and Long Beach, found: {dealer_names}")
        return False

    def test_get_cars_list(self):
        """Test getting cars list - should have car models"""
        success, response = self.run_test(
            "Get Cars List",
            "GET",
            "config-lists/car",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} cars in the list")
            if len(response) > 0:
                car_names = [car['name'] for car in response[:5]]  # Show first 5
                print(f"✅ Sample cars: {car_names}")
                return True
            else:
                print(f"❌ Expected cars list to have items")
        return False

    def test_add_bank(self):
        """Test adding a new bank to the list"""
        timestamp = datetime.now().strftime('%H%M%S')
        bank_name = f"Test Bank {timestamp}"
        
        success, response = self.run_test(
            "Add New Bank",
            "POST",
            "config-lists",
            200,
            data={
                "name": bank_name,
                "category": "bank"
            }
        )
        if success and 'id' in response:
            self.bank_id = response['id']
            print(f"✅ Added bank: {bank_name}")
            return True
        return False

    def test_add_dealer(self):
        """Test adding a new dealer to the list"""
        timestamp = datetime.now().strftime('%H%M%S')
        dealer_name = f"Test Dealer {timestamp}"
        
        success, response = self.run_test(
            "Add New Dealer",
            "POST",
            "config-lists",
            200,
            data={
                "name": dealer_name,
                "category": "dealer"
            }
        )
        if success and 'id' in response:
            self.dealer_id = response['id']
            print(f"✅ Added dealer: {dealer_name}")
            return True
        return False

    def test_add_car(self):
        """Test adding a new car to the list"""
        timestamp = datetime.now().strftime('%H%M%S')
        car_name = f"Test Car {timestamp}"
        
        success, response = self.run_test(
            "Add New Car",
            "POST",
            "config-lists",
            200,
            data={
                "name": car_name,
                "category": "car"
            }
        )
        if success and 'id' in response:
            self.car_id = response['id']
            print(f"✅ Added car: {car_name}")
            return True
        return False

    def test_delete_config_item(self):
        """Test deleting a config list item"""
        if not self.bank_id:
            return False
            
        success, response = self.run_test(
            "Delete Config Item (Bank)",
            "DELETE",
            f"config-lists/{self.bank_id}",
            200
        )
        return success

    def test_create_client_for_trash(self):
        """Create a client that we can delete to test trash functionality"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Create Client for Trash Test",
            "POST",
            "clients",
            200,
            data={
                "first_name": "TrashTest",
                "last_name": "Client",
                "phone": f"+1555777{timestamp}",
                "email": f"trashtest_{timestamp}@email.com"
            }
        )
        if success and 'id' in response:
            self.client_id = response['id']
            return True
        return False

    def test_delete_client_to_trash(self):
        """Test soft deleting a client (moves to trash)"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Delete Client to Trash",
            "DELETE",
            f"clients/{self.client_id}",
            200
        )
        return success

    def test_get_trash_clients(self):
        """Test getting deleted clients from trash"""
        success, response = self.run_test(
            "Get Trash Clients",
            "GET",
            "trash/clients",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} clients in trash")
            # Check if our deleted client is in trash
            deleted_client = next((c for c in response if c['id'] == self.client_id), None)
            if deleted_client:
                print(f"✅ Confirmed: Deleted client found in trash")
                return True
            else:
                print(f"❌ Deleted client not found in trash")
        return False

    def test_restore_client(self):
        """Test restoring a client from trash"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Restore Client from Trash",
            "POST",
            f"clients/{self.client_id}/restore",
            200
        )
        return success

    def test_permanent_delete_client(self):
        """Test permanently deleting a client"""
        if not self.client_id:
            return False
            
        # First delete to trash again
        self.test_delete_client_to_trash()
        
        success, response = self.run_test(
            "Permanent Delete Client",
            "DELETE",
            f"clients/{self.client_id}?permanent=true",
            200
        )
        return success

    def test_get_users_list(self):
        """Test admin getting users list"""
        success, response = self.run_test(
            "Get Users List (Admin)",
            "GET",
            "users",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} users")
            return True
        return False

    def test_get_trash_records(self):
        """Test getting deleted records from trash"""
        success, response = self.run_test(
            "Get Trash Records",
            "GET",
            "trash/user-records",
            200
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} records in trash")
            return True
        return False

def main():
    print("🚀 Starting Admin Features API Testing...")
    tester = AdminFeaturesAPITester()
    
    # Authentication
    print("\n" + "="*50)
    print("ADMIN AUTHENTICATION")
    print("="*50)
    
    if not tester.test_admin_login():
        print("❌ Admin login failed, stopping tests")
        return 1

    # Config Lists Tests
    print("\n" + "="*50)
    print("CONFIG LISTS TESTS (Banks, Dealers, Cars)")
    print("="*50)
    
    tester.test_get_banks_list()
    tester.test_get_dealers_list()
    tester.test_get_cars_list()
    
    # Test adding new items
    tester.test_add_bank()
    tester.test_add_dealer()
    tester.test_add_car()
    
    # Test deleting items
    tester.test_delete_config_item()

    # Trash Functionality Tests
    print("\n" + "="*50)
    print("TRASH FUNCTIONALITY TESTS")
    print("="*50)
    
    tester.test_create_client_for_trash()
    tester.test_delete_client_to_trash()
    tester.test_get_trash_clients()
    tester.test_restore_client()
    tester.test_permanent_delete_client()
    tester.test_get_trash_records()

    # Admin Panel Tests
    print("\n" + "="*50)
    print("ADMIN PANEL TESTS")
    print("="*50)
    
    tester.test_get_users_list()
    
    # Print Results
    print("\n" + "="*50)
    print("ADMIN FEATURES TEST RESULTS")
    print("="*50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.failed_tests:
        print(f"\n❌ Failed tests ({len(tester.failed_tests)}):")
        for test in tester.failed_tests:
            error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
            print(f"  - {test['test']}: {error_msg}")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())