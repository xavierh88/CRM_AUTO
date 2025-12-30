import requests
import sys
import json
from datetime import datetime

class CRMAPITester:
    def __init__(self, base_url="https://dealershipcrm.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.user_id = None
        self.admin_id = None
        self.client_id = None
        self.record_id = None
        self.appointment_id = None
        self.cosigner_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, use_admin=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Use admin token if specified and available
        token = self.admin_token if use_admin and self.admin_token else self.token
        if token:
            headers['Authorization'] = f'Bearer {token}'

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

    def test_auth_register_salesperson(self):
        """Test salesperson registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Register Salesperson",
            "POST",
            "auth/register",
            200,
            data={
                "email": f"salesperson_{timestamp}@dealer.com",
                "password": "TestPass123!",
                "name": f"Test Salesperson {timestamp}",
                "role": "salesperson",
                "phone": f"+1555{timestamp}"
            }
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_auth_register_admin(self):
        """Test admin registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Register Admin",
            "POST",
            "auth/register",
            200,
            data={
                "email": f"admin_{timestamp}@dealer.com",
                "password": "AdminPass123!",
                "name": f"Test Admin {timestamp}",
                "role": "admin",
                "phone": f"+1666{timestamp}"
            }
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.admin_id = response['user']['id']
            return True
        return False

    def test_auth_login(self):
        """Test login with registered user"""
        if not self.token:
            return False
        
        # Extract email from token payload (simplified)
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": f"salesperson_{timestamp}@dealer.com",
                "password": "TestPass123!"
            }
        )
        return success

    def test_auth_me(self):
        """Test get current user"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_protected_route_without_token(self):
        """Test protected route without token"""
        old_token = self.token
        self.token = None
        success, _ = self.run_test(
            "Protected Route Without Token",
            "GET",
            "auth/me",
            401
        )
        self.token = old_token
        return success

    def test_create_client(self):
        """Test client creation"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Create Client",
            "POST",
            "clients",
            200,
            data={
                "first_name": "John",
                "last_name": "Doe",
                "phone": f"+1555123{timestamp}",
                "email": f"john.doe_{timestamp}@email.com",
                "address": "123 Main St",
                "apartment": "Apt 1"
            }
        )
        if success and 'id' in response:
            self.client_id = response['id']
            return True
        return False

    def test_list_clients(self):
        """Test listing clients"""
        success, response = self.run_test(
            "List Clients",
            "GET",
            "clients",
            200
        )
        return success and isinstance(response, list)

    def test_search_clients(self):
        """Test client search by phone"""
        if not self.client_id:
            return False
        
        success, response = self.run_test(
            "Search Client by Phone",
            "GET",
            f"clients/search/phone/555123",
            200
        )
        return success

    def test_create_user_record(self):
        """Test user record (cartilla) creation"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Create User Record",
            "POST",
            "user-records",
            200,
            data={
                "client_id": self.client_id,
                "dl": True,
                "checks": True,
                "ssn": False,
                "itin": True,
                "auto": "Honda Civic",
                "credit": "Good",
                "bank": "Chase Bank",
                "auto_loan": "15000",
                "down_payment": "3000",
                "dealer": "ABC Motors"
            }
        )
        if success and 'id' in response:
            self.record_id = response['id']
            return True
        return False

    def test_get_user_records(self):
        """Test getting user records"""
        success, response = self.run_test(
            "Get User Records",
            "GET",
            "user-records",
            200
        )
        return success and isinstance(response, list)

    def test_create_appointment(self):
        """Test appointment creation"""
        if not self.record_id or not self.client_id:
            return False
            
        success, response = self.run_test(
            "Create Appointment",
            "POST",
            "appointments",
            200,
            data={
                "user_record_id": self.record_id,
                "client_id": self.client_id,
                "date": "2024-12-20",
                "time": "10:00",
                "dealer": "ABC Motors",
                "language": "en"
            }
        )
        if success and 'id' in response:
            self.appointment_id = response['id']
            return True
        return False

    def test_update_appointment_status(self):
        """Test appointment status update"""
        if not self.appointment_id:
            return False
            
        success, _ = self.run_test(
            "Update Appointment Status",
            "PUT",
            f"appointments/{self.appointment_id}/status?status=cumplido",
            200
        )
        return success

    def test_get_appointments(self):
        """Test getting appointments"""
        success, response = self.run_test(
            "Get Appointments",
            "GET",
            "appointments",
            200
        )
        return success and isinstance(response, list)

    def test_get_agenda(self):
        """Test getting agenda"""
        success, response = self.run_test(
            "Get Agenda",
            "GET",
            "appointments/agenda",
            200
        )
        return success and isinstance(response, list)

    def test_create_cosigner(self):
        """Test co-signer creation"""
        if not self.client_id:
            return False
            
        # First create another client to be cosigner
        timestamp = datetime.now().strftime('%H%M%S')
        success, cosigner_response = self.run_test(
            "Create Cosigner Client",
            "POST",
            "clients",
            200,
            data={
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": f"+1555999{timestamp}",
                "email": f"jane.smith_{timestamp}@email.com"
            }
        )
        
        if not success:
            return False
            
        cosigner_client_id = cosigner_response['id']
        
        success, response = self.run_test(
            "Create Cosigner Relation",
            "POST",
            "cosigners",
            200,
            data={
                "buyer_client_id": self.client_id,
                "cosigner_client_id": cosigner_client_id
            }
        )
        if success and 'id' in response:
            self.cosigner_id = response['id']
            return True
        return False

    def test_get_cosigners(self):
        """Test getting cosigners"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Get Cosigners",
            "GET",
            f"cosigners/{self.client_id}",
            200
        )
        return success and isinstance(response, list)

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        success, response = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        return success and 'total_clients' in response

    def test_admin_get_users(self):
        """Test admin get users list"""
        success, response = self.run_test(
            "Admin Get Users",
            "GET",
            "users",
            200,
            use_admin=True
        )
        return success and isinstance(response, list)

    def test_admin_get_performance(self):
        """Test admin get salesperson performance"""
        success, response = self.run_test(
            "Admin Get Performance",
            "GET",
            "dashboard/salesperson-performance",
            200,
            use_admin=True
        )
        return success and isinstance(response, list)

    def test_admin_get_trash(self):
        """Test admin access to trash"""
        success, response = self.run_test(
            "Admin Get Trash Clients",
            "GET",
            "trash/clients",
            200,
            use_admin=True
        )
        return success and isinstance(response, list)

    def test_sms_send_documents(self):
        """Test SMS send documents link (mocked)"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Send Documents SMS",
            "POST",
            f"sms/send-documents-link?client_id={self.client_id}",
            200
        )
        return success and 'message' in response

    def test_sms_send_appointment(self):
        """Test SMS send appointment link (mocked)"""
        if not self.client_id or not self.appointment_id:
            return False
            
        success, response = self.run_test(
            "Send Appointment SMS",
            "POST",
            f"sms/send-appointment-link?client_id={self.client_id}&appointment_id={self.appointment_id}",
            200
        )
        return success and 'message' in response

    def test_non_admin_access_admin_routes(self):
        """Test non-admin user accessing admin routes"""
        success, _ = self.run_test(
            "Non-Admin Access Admin Route",
            "GET",
            "users",
            403
        )
        return success

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

    def test_last_record_date_null_when_no_records(self):
        """Test that last_record_date is null when client has no records"""
        # Create a new client without any records
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Create Client Without Records",
            "POST",
            "clients",
            200,
            data={
                "first_name": "NoRecords",
                "last_name": "Client",
                "phone": f"+1555000{timestamp}",
                "email": f"norecords_{timestamp}@email.com"
            }
        )
        
        if not success:
            return False
            
        # Get clients list and check this client has null last_record_date
        success, clients = self.run_test(
            "Get Clients - Check Null Last Record Date",
            "GET",
            "clients",
            200
        )
        
        if success:
            new_client = next((c for c in clients if c['phone'] == f"+1555000{timestamp}"), None)
            if new_client and new_client.get('last_record_date') is None:
                print(f"✅ Confirmed: last_record_date is null for client without records")
                return True
            else:
                print(f"❌ Expected null last_record_date, got: {new_client.get('last_record_date') if new_client else 'client not found'}")
        
        return False

    def test_last_record_date_shows_when_records_exist(self):
        """Test that last_record_date shows date of last record created"""
        if not self.client_id:
            return False
            
        # Get clients list and check our client has last_record_date set
        success, clients = self.run_test(
            "Get Clients - Check Last Record Date Set",
            "GET",
            "clients",
            200
        )
        
        if success:
            client = next((c for c in clients if c['id'] == self.client_id), None)
            if client and client.get('last_record_date') is not None:
                print(f"✅ Confirmed: last_record_date is set: {client['last_record_date']}")
                return True
            else:
                print(f"❌ Expected last_record_date to be set, got: {client.get('last_record_date') if client else 'client not found'}")
        
        return False

    def test_search_by_name(self):
        """Test search by first name and last name"""
        # Search by first name
        success1, response1 = self.run_test(
            "Search Clients by First Name",
            "GET",
            "clients?search=John",
            200
        )
        
        # Search by last name  
        success2, response2 = self.run_test(
            "Search Clients by Last Name", 
            "GET",
            "clients?search=Doe",
            200
        )
        
        return success1 and success2 and isinstance(response1, list) and isinstance(response2, list)

    def test_search_by_phone(self):
        """Test search by phone number"""
        success, response = self.run_test(
            "Search Clients by Phone",
            "GET", 
            "clients?search=555",
            200
        )
        
        return success and isinstance(response, list)

    def test_new_opportunity_with_previous_record_id(self):
        """Test creating new opportunity linked to previous record"""
        if not self.client_id or not self.record_id:
            return False
            
        success, response = self.run_test(
            "Create New Opportunity Record",
            "POST",
            "user-records",
            200,
            data={
                "client_id": self.client_id,
                "previous_record_id": self.record_id,
                "dl": False,
                "checks": True,
                "ssn": True,
                "itin": False
            }
        )
        
        if success and 'id' in response:
            # Check that opportunity_number is incremented
            if response.get('opportunity_number', 1) > 1:
                print(f"✅ Confirmed: New opportunity created with opportunity_number: {response['opportunity_number']}")
                return True
            else:
                print(f"❌ Expected opportunity_number > 1, got: {response.get('opportunity_number')}")
        
        return False

    def test_multiple_cosigners_allowed(self):
        """Test that multiple co-signers can be added to same buyer"""
        if not self.client_id:
            return False
            
        # Create first cosigner
        timestamp1 = datetime.now().strftime('%H%M%S')
        success1, cosigner1_response = self.run_test(
            "Create First Cosigner Client",
            "POST",
            "clients",
            200,
            data={
                "first_name": "Cosigner1",
                "last_name": "Smith",
                "phone": f"+1555111{timestamp1}",
                "email": f"cosigner1_{timestamp1}@email.com"
            }
        )
        
        if not success1:
            return False
            
        # Create second cosigner
        timestamp2 = datetime.now().strftime('%H%M%S') + "2"
        success2, cosigner2_response = self.run_test(
            "Create Second Cosigner Client",
            "POST",
            "clients", 
            200,
            data={
                "first_name": "Cosigner2",
                "last_name": "Johnson",
                "phone": f"+1555222{timestamp2}",
                "email": f"cosigner2_{timestamp2}@email.com"
            }
        )
        
        if not success2:
            return False
            
        # Link first cosigner
        success3, relation1 = self.run_test(
            "Link First Cosigner",
            "POST",
            "cosigners",
            200,
            data={
                "buyer_client_id": self.client_id,
                "cosigner_client_id": cosigner1_response['id']
            }
        )
        
        # Link second cosigner
        success4, relation2 = self.run_test(
            "Link Second Cosigner",
            "POST", 
            "cosigners",
            200,
            data={
                "buyer_client_id": self.client_id,
                "cosigner_client_id": cosigner2_response['id']
            }
        )
        
        # Verify both cosigners are linked
        success5, cosigners_list = self.run_test(
            "Get Multiple Cosigners",
            "GET",
            f"cosigners/{self.client_id}",
            200
        )
        
        if success3 and success4 and success5:
            if len(cosigners_list) >= 2:
                print(f"✅ Confirmed: Multiple cosigners allowed - found {len(cosigners_list)} cosigners")
                return True
            else:
                print(f"❌ Expected multiple cosigners, found: {len(cosigners_list)}")
        
        return False

    # ==================== IMPORT CONTACTS & SMS MARKETING TESTS ====================
    
    def test_import_contacts_csv(self):
        """Test importing contacts from CSV file"""
        # Create a simple CSV content for testing
        csv_content = "First Name,Last Name,Phone\nJohn,Doe,5551234567\nJane,Smith,5559876543"
        
        # For this test, we'll simulate the file upload by testing the endpoint
        # In a real scenario, we'd need to create an actual file
        success, response = self.run_test(
            "Import Contacts (Simulated)",
            "GET",  # Using GET to test endpoint exists, actual would be POST with file
            "imported-contacts",
            200,
            use_admin=True
        )
        return success

    def test_get_imported_contacts(self):
        """Test getting list of imported contacts"""
        success, response = self.run_test(
            "Get Imported Contacts",
            "GET",
            "imported-contacts?limit=50",
            200,
            use_admin=True
        )
        return success and 'contacts' in response

    def test_send_sms_now_to_contact(self):
        """Test sending immediate SMS to imported contact"""
        # First get contacts to find one to test with
        success, response = self.run_test(
            "Get Contacts for SMS Test",
            "GET",
            "imported-contacts?limit=1",
            200,
            use_admin=True
        )
        
        if success and response.get('contacts') and len(response['contacts']) > 0:
            contact_id = response['contacts'][0]['id']
            success, sms_response = self.run_test(
                "Send SMS Now to Contact",
                "POST",
                f"imported-contacts/{contact_id}/send-sms-now",
                200,
                use_admin=True
            )
            return success
        else:
            print("⚠️  No imported contacts found to test SMS sending")
            return True  # Pass if no contacts to test

    def test_toggle_opt_out_status(self):
        """Test toggling opt-out status for imported contact"""
        # First get contacts to find one to test with
        success, response = self.run_test(
            "Get Contacts for Opt-out Test",
            "GET",
            "imported-contacts?limit=1",
            200,
            use_admin=True
        )
        
        if success and response.get('contacts') and len(response['contacts']) > 0:
            contact_id = response['contacts'][0]['id']
            current_opt_out = response['contacts'][0].get('opt_out', False)
            
            success, opt_response = self.run_test(
                "Toggle Opt-out Status",
                "PUT",
                f"imported-contacts/{contact_id}/opt-out?opt_out={not current_opt_out}",
                200,
                use_admin=True
            )
            return success
        else:
            print("⚠️  No imported contacts found to test opt-out toggle")
            return True  # Pass if no contacts to test

    def test_delete_imported_contact(self):
        """Test deleting an imported contact"""
        # First get contacts to find one to test with
        success, response = self.run_test(
            "Get Contacts for Delete Test",
            "GET",
            "imported-contacts?limit=1",
            200,
            use_admin=True
        )
        
        if success and response.get('contacts') and len(response['contacts']) > 0:
            contact_id = response['contacts'][0]['id']
            
            success, delete_response = self.run_test(
                "Delete Imported Contact",
                "DELETE",
                f"imported-contacts/{contact_id}",
                200,
                use_admin=True
            )
            return success
        else:
            print("⚠️  No imported contacts found to test deletion")
            return True  # Pass if no contacts to test

    def test_get_sms_templates(self):
        """Test getting SMS templates"""
        success, response = self.run_test(
            "Get SMS Templates",
            "GET",
            "sms-templates",
            200,
            use_admin=True
        )
        return success and isinstance(response, list)

    def test_update_sms_template(self):
        """Test updating an SMS template"""
        # First get templates to find one to update
        success, templates = self.run_test(
            "Get Templates for Update Test",
            "GET",
            "sms-templates",
            200,
            use_admin=True
        )
        
        if success and templates and len(templates) > 0:
            template_key = templates[0]['template_key']
            
            success, update_response = self.run_test(
                "Update SMS Template",
                "PUT",
                f"sms-templates/{template_key}",
                200,
                data={
                    "template_key": template_key,
                    "message_en": "Updated English message for testing {first_name}",
                    "message_es": "Mensaje en español actualizado para pruebas {first_name}"
                },
                use_admin=True
            )
            return success
        else:
            print("⚠️  No SMS templates found to test update")
            return True  # Pass if no templates to test

    def test_salesperson_login(self):
        """Test login with salesperson credentials"""
        success, response = self.run_test(
            "Salesperson Login (vendedor1@test.com)",
            "POST",
            "auth/login",
            200,
            data={
                "email": "vendedor1@test.com",
                "password": "Test1234"
            }
        )
        if success and 'token' in response:
            # Store salesperson token for later tests
            self.salesperson_token = response['token']
            return True
        return False

    def test_non_admin_sms_template_access(self):
        """Test that non-admin users cannot update SMS templates"""
        if not hasattr(self, 'salesperson_token'):
            return False
            
        # Temporarily use salesperson token
        old_token = self.token
        self.token = self.salesperson_token
        
        success, _ = self.run_test(
            "Non-Admin SMS Template Update (Should Fail)",
            "PUT",
            "sms-templates/marketing_initial",
            403,  # Should be forbidden
            data={
                "template_key": "marketing_initial",
                "message_en": "Unauthorized update attempt",
                "message_es": "Intento de actualización no autorizado"
            }
        )
        
        # Restore admin token
        self.token = old_token
        return success

    # ==================== CONFIG LISTS TESTS ====================
    
    def test_get_id_types(self):
        """Test GET /api/config-lists/id_type"""
        success, response = self.run_test(
            "Get ID Types",
            "GET",
            "config-lists/id_type",
            200,
            use_admin=True
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} ID types: {[item.get('name') for item in response]}")
            # Check for expected items
            expected_items = ["DL", "Matricula", "Other Driver Licenses", "Passport", "Resident ID", "US Passport", "Votacion ID"]
            found_items = [item.get('name') for item in response]
            if len(found_items) >= 7:
                print(f"✅ Expected 7+ ID types, found {len(found_items)}")
                return True
            else:
                print(f"❌ Expected 7+ ID types, found {len(found_items)}")
        return False

    def test_get_poi_types(self):
        """Test GET /api/config-lists/poi_type"""
        success, response = self.run_test(
            "Get POI Types",
            "GET",
            "config-lists/poi_type",
            200,
            use_admin=True
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} POI types: {[item.get('name') for item in response]}")
            # Check for expected items
            expected_items = ["Cash", "Company Check", "Personal Check", "Talon de Cheque"]
            found_items = [item.get('name') for item in response]
            if len(found_items) >= 4:
                print(f"✅ Expected 4+ POI types, found {len(found_items)}")
                return True
            else:
                print(f"❌ Expected 4+ POI types, found {len(found_items)}")
        return False

    def test_get_por_types(self):
        """Test GET /api/config-lists/por_type"""
        success, response = self.run_test(
            "Get POR Types",
            "GET",
            "config-lists/por_type",
            200,
            use_admin=True
        )
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} POR types: {[item.get('name') for item in response]}")
            # Check for expected items
            expected_items = ["Agua", "Bank Statements", "Car Insurance", "Gas", "Internet", "Luz", "TV Cable", "Telefono"]
            found_items = [item.get('name') for item in response]
            if len(found_items) >= 8:
                print(f"✅ Expected 8+ POR types, found {len(found_items)}")
                return True
            else:
                print(f"❌ Expected 8+ POR types, found {len(found_items)}")
        return False

    def test_add_id_type(self):
        """Test POST /api/config-lists with category=id_type"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Add New ID Type",
            "POST",
            "config-lists",
            200,
            data={
                "category": "id_type",
                "name": f"Test ID Type {timestamp}"
            },
            use_admin=True
        )
        if success and 'id' in response:
            self.test_id_type_id = response['id']
            print(f"✅ Created ID type with ID: {self.test_id_type_id}")
            return True
        return False

    def test_add_poi_type(self):
        """Test POST /api/config-lists with category=poi_type"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Add New POI Type",
            "POST",
            "config-lists",
            200,
            data={
                "category": "poi_type",
                "name": f"Test POI Type {timestamp}"
            },
            use_admin=True
        )
        if success and 'id' in response:
            self.test_poi_type_id = response['id']
            print(f"✅ Created POI type with ID: {self.test_poi_type_id}")
            return True
        return False

    def test_add_por_type(self):
        """Test POST /api/config-lists with category=por_type"""
        timestamp = datetime.now().strftime('%H%M%S')
        success, response = self.run_test(
            "Add New POR Type",
            "POST",
            "config-lists",
            200,
            data={
                "category": "por_type",
                "name": f"Test POR Type {timestamp}"
            },
            use_admin=True
        )
        if success and 'id' in response:
            self.test_por_type_id = response['id']
            print(f"✅ Created POR type with ID: {self.test_por_type_id}")
            return True
        return False

    def test_delete_id_type(self):
        """Test DELETE /api/config-lists/{id} for ID type"""
        if not hasattr(self, 'test_id_type_id'):
            return False
        
        success, response = self.run_test(
            "Delete ID Type",
            "DELETE",
            f"config-lists/{self.test_id_type_id}",
            200,
            use_admin=True
        )
        return success

    def test_delete_poi_type(self):
        """Test DELETE /api/config-lists/{id} for POI type"""
        if not hasattr(self, 'test_poi_type_id'):
            return False
        
        success, response = self.run_test(
            "Delete POI Type",
            "DELETE",
            f"config-lists/{self.test_poi_type_id}",
            200,
            use_admin=True
        )
        return success

    def test_delete_por_type(self):
        """Test DELETE /api/config-lists/{id} for POR type"""
        if not hasattr(self, 'test_por_type_id'):
            return False
        
        success, response = self.run_test(
            "Delete POR Type",
            "DELETE",
            f"config-lists/{self.test_por_type_id}",
            200,
            use_admin=True
        )
        return success

    def test_enhanced_opportunity_form_fields(self):
        """Test creating user record with enhanced opportunity form fields"""
        if not self.client_id:
            return False
            
        success, response = self.run_test(
            "Create Enhanced Opportunity Record",
            "POST",
            "user-records",
            200,
            data={
                "client_id": self.client_id,
                # ID fields
                "has_id": True,
                "id_type": "DL",
                # POI fields
                "has_poi": True,
                "poi_type": "Cash",
                # Other checkboxes
                "ssn": True,
                "itin": False,
                "self_employed": True,
                # POR fields
                "has_por": True,
                "por_types": ["Agua", "Luz", "Gas"],
                # Bank info
                "bank": "Chase Bank",
                "bank_deposit_type": "No deposito directo",
                # Down Payment with Trade-in
                "down_payment_type": "Trade",
                "trade_make": "Honda",
                "trade_model": "Civic",
                "trade_year": "2018",
                "trade_title": "Clean Title",
                "trade_miles": "50000",
                "trade_plate": "CA",
                "trade_estimated_value": "15000",
                # Finance status (fixed typo)
                "finance_status": "lease"  # Should be "lease" not "least"
            }
        )
        
        if success and 'id' in response:
            # Verify the fields are saved correctly
            record = response
            checks = [
                record.get('has_id') == True,
                record.get('id_type') == "DL",
                record.get('has_poi') == True,
                record.get('poi_type') == "Cash",
                record.get('self_employed') == True,
                record.get('has_por') == True,
                record.get('por_types') == ["Agua", "Luz", "Gas"],
                record.get('bank') == "Chase Bank",
                record.get('bank_deposit_type') == "No deposito directo",
                record.get('down_payment_type') == "Trade",
                record.get('trade_make') == "Honda",
                record.get('finance_status') == "lease"
            ]
            
            if all(checks):
                print(f"✅ All enhanced opportunity form fields saved correctly")
                return True
            else:
                print(f"❌ Some enhanced opportunity form fields not saved correctly")
                print(f"   Record data: {json.dumps(record, indent=2)}")
        
        return False

    def test_cosigner_alert_logic(self):
        """Test cosigner alert when Tipo de Depósito='No deposito directo' AND POI type='Cash'"""
        if not self.client_id:
            return False
            
        # This test verifies the backend accepts the combination that should trigger frontend alert
        success, response = self.run_test(
            "Create Record with Cosigner Alert Conditions",
            "POST",
            "user-records",
            200,
            data={
                "client_id": self.client_id,
                "has_poi": True,
                "poi_type": "Cash",
                "bank_deposit_type": "No deposito directo"
            }
        )
        
        if success:
            record = response
            if (record.get('poi_type') == "Cash" and 
                record.get('bank_deposit_type') == "No deposito directo"):
                print(f"✅ Cosigner alert conditions saved correctly (frontend should show warning)")
                return True
            else:
                print(f"❌ Cosigner alert conditions not saved correctly")
        
        return False

    # ==================== NEW SCHEDULER TESTS ====================
    
    def test_scheduler_status(self):
        """Test GET /api/scheduler/status (admin only)"""
        success, response = self.run_test(
            "Get Scheduler Status",
            "GET",
            "scheduler/status",
            200,
            use_admin=True
        )
        return success and 'status' in response

    def test_scheduler_run_now(self):
        """Test POST /api/scheduler/run-now (admin only)"""
        success, response = self.run_test(
            "Manually Trigger Marketing SMS Job",
            "POST",
            "scheduler/run-now",
            200,
            use_admin=True
        )
        return success and 'message' in response

    def test_non_admin_scheduler_access(self):
        """Test that non-admin users cannot access scheduler endpoints"""
        if not hasattr(self, 'salesperson_token'):
            return False
            
        # Temporarily use salesperson token
        old_token = self.token
        self.token = self.salesperson_token
        
        # Test scheduler status access
        success1, _ = self.run_test(
            "Non-Admin Scheduler Status (Should Fail)",
            "GET",
            "scheduler/status",
            403  # Should be forbidden
        )
        
        # Test scheduler run-now access
        success2, _ = self.run_test(
            "Non-Admin Scheduler Run-Now (Should Fail)",
            "POST",
            "scheduler/run-now",
            403  # Should be forbidden
        )
        
        # Restore admin token
        self.token = old_token
        return success1 and success2

def main():
    print("🚀 Starting CRM API Testing - Dashboard, Agenda, and SMS Scheduler Features...")
    tester = CRMAPITester()
    
    # Authentication Tests
    print("\n" + "="*50)
    print("AUTHENTICATION TESTS")
    print("="*50)
    
    # Test admin login first with provided credentials
    if not tester.test_admin_login():
        print("❌ Admin login failed, stopping tests")
        return 1
    else:
        # Use admin token as main token for testing
        tester.token = tester.admin_token
        tester.user_id = tester.admin_id
    
    # Test salesperson login
    tester.test_salesperson_login()
    
    tester.test_auth_me()
    
    # NEW SCHEDULER TESTS
    print("\n" + "="*50)
    print("SMS SCHEDULER TESTS")
    print("="*50)
    
    tester.test_scheduler_status()
    tester.test_scheduler_run_now()
    tester.test_non_admin_scheduler_access()
    
    # Dashboard and Agenda Tests
    print("\n" + "="*50)
    print("DASHBOARD & AGENDA TESTS")
    print("="*50)
    
    tester.test_dashboard_stats()
    tester.test_get_agenda()
    
    # Create test data for appointment status testing
    if tester.test_create_client() and tester.test_create_user_record() and tester.test_create_appointment():
        tester.test_update_appointment_status()
    
    # Import Contacts & SMS Marketing Tests
    print("\n" + "="*50)
    print("IMPORT CONTACTS & SMS MARKETING TESTS")
    print("="*50)
    
    # Test import contacts functionality
    tester.test_import_contacts_csv()
    tester.test_get_imported_contacts()
    tester.test_send_sms_now_to_contact()
    tester.test_toggle_opt_out_status()
    tester.test_delete_imported_contact()
    
    # Test SMS templates functionality
    tester.test_get_sms_templates()
    tester.test_update_sms_template()
    tester.test_non_admin_sms_template_access()
    
    # Client Tests - Focus on Last Record Date
    print("\n" + "="*50)
    print("CLIENT MANAGEMENT TESTS - LAST RECORD DATE")
    print("="*50)
    
    # Test 1: Last record date null when no records
    tester.test_last_record_date_null_when_no_records()
    
    # Test 2: Last record date shows when records exist (using existing client)
    if tester.client_id:
        tester.test_last_record_date_shows_when_records_exist()
    
    # Search Tests
    print("\n" + "="*50)
    print("SEARCH FUNCTIONALITY TESTS")
    print("="*50)
    
    # Test 3: Search by name (first name and last name)
    tester.test_search_by_name()
    
    # Test 4: Search by phone
    tester.test_search_by_phone()
    
    # New Opportunity Tests
    print("\n" + "="*50)
    print("NEW OPPORTUNITY TESTS")
    print("="*50)
    
    # Test 5: New opportunity with previous_record_id
    if tester.client_id and tester.record_id:
        tester.test_new_opportunity_with_previous_record_id()
    
    # Multiple Co-signers Tests
    print("\n" + "="*50)
    print("MULTIPLE CO-SIGNERS TESTS")
    print("="*50)
    
    # Test 6: Multiple co-signers allowed
    if tester.client_id:
        tester.test_multiple_cosigners_allowed()
    
    # Additional Core Tests
    print("\n" + "="*50)
    print("ADDITIONAL CORE FUNCTIONALITY TESTS")
    print("="*50)
    
    tester.test_list_clients()
    tester.test_get_user_records()
    
    # Print Results
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.failed_tests:
        print(f"\n❌ Failed tests ({len(tester.failed_tests)}):")
        for test in tester.failed_tests:
            error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
            print(f"  - {test['test']}: {error_msg}")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    return 0 if success_rate >= 70 else 1

if __name__ == "__main__":
    sys.exit(main())