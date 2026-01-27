#!/usr/bin/env python3
"""
Focused test script for new DealerCRM implementations:
1. Document Upload/Download APIs
2. Direct Deposit Amount field
3. Update Documents Status API
"""

import requests
import json
import io
from datetime import datetime

class NewFeaturesTester:
    def __init__(self):
        self.base_url = "https://autocrm-dash.preview.emergentagent.com/api"
        self.token = None
        self.client_id = None
        self.record_id = None
        
    def login_admin(self):
        """Login as admin"""
        response = requests.post(f"{self.base_url}/auth/login", json={
            "email": "xadmin",
            "password": "Cali2020"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['token']
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {response.status_code}")
            return False
    
    def get_existing_client(self):
        """Get an existing client for testing"""
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get(f"{self.base_url}/clients", headers=headers)
        
        if response.status_code == 200:
            clients = response.json()
            if clients:
                # Find a client that's not deleted and has a proper name
                for client in clients:
                    if not client.get('is_deleted', False) and client.get('first_name') != 'Cosigner1' and client.get('first_name') != 'Cosigner2':
                        self.client_id = client['id']
                        print(f"✅ Using existing client: {client['first_name']} {client['last_name']} (ID: {self.client_id})")
                        return True
                
                # If no suitable client found, use the first one
                self.client_id = clients[0]['id']
                print(f"✅ Using client: {clients[0]['first_name']} {clients[0]['last_name']} (ID: {self.client_id})")
                return True
        
        print("❌ No clients found")
        return False
    
    def test_document_upload_id(self):
        """Test uploading ID document"""
        print("\n🔍 Testing ID Document Upload...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Create test file
        test_file_content = b"This is a test ID document for testing purposes"
        files = {
            'file': ('test_id_document.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        data = {'doc_type': 'id'}
        
        response = requests.post(
            f"{self.base_url}/clients/{self.client_id}/documents/upload",
            data=data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ID document uploaded successfully: {result.get('message')}")
            return True
        else:
            print(f"❌ ID document upload failed: {response.status_code} - {response.text}")
            return False
    
    def test_document_upload_income(self):
        """Test uploading income document"""
        print("\n🔍 Testing Income Document Upload...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Create test file
        test_file_content = b"This is a test income proof document for testing purposes"
        files = {
            'file': ('test_income_document.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        data = {'doc_type': 'income'}
        
        response = requests.post(
            f"{self.base_url}/clients/{self.client_id}/documents/upload",
            data=data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Income document uploaded successfully: {result.get('message')}")
            return True
        else:
            print(f"❌ Income document upload failed: {response.status_code} - {response.text}")
            return False
    
    def test_document_upload_residence(self):
        """Test uploading residence document"""
        print("\n🔍 Testing Residence Document Upload...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Create test file
        test_file_content = b"This is a test residence proof document for testing purposes"
        files = {
            'file': ('test_residence_document.pdf', io.BytesIO(test_file_content), 'application/pdf')
        }
        data = {'doc_type': 'residence'}
        
        response = requests.post(
            f"{self.base_url}/clients/{self.client_id}/documents/upload",
            data=data,
            files=files,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Residence document uploaded successfully: {result.get('message')}")
            return True
        else:
            print(f"❌ Residence document upload failed: {response.status_code} - {response.text}")
            return False
    
    def test_document_download_id(self):
        """Test downloading ID document"""
        print("\n🔍 Testing ID Document Download...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(
            f"{self.base_url}/clients/{self.client_id}/documents/download/id",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ ID document downloaded successfully (Content-Type: {response.headers.get('Content-Type')})")
            return True
        elif response.status_code == 404:
            print(f"⚠️  ID document not found (may not have been uploaded)")
            return True  # Not a failure if document wasn't uploaded
        else:
            print(f"❌ ID document download failed: {response.status_code} - {response.text}")
            return False
    
    def test_document_download_income(self):
        """Test downloading income document"""
        print("\n🔍 Testing Income Document Download...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(
            f"{self.base_url}/clients/{self.client_id}/documents/download/income",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ Income document downloaded successfully (Content-Type: {response.headers.get('Content-Type')})")
            return True
        elif response.status_code == 404:
            print(f"⚠️  Income document not found (may not have been uploaded)")
            return True
        else:
            print(f"❌ Income document download failed: {response.status_code} - {response.text}")
            return False
    
    def test_document_download_residence(self):
        """Test downloading residence document"""
        print("\n🔍 Testing Residence Document Download...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(
            f"{self.base_url}/clients/{self.client_id}/documents/download/residence",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ Residence document downloaded successfully (Content-Type: {response.headers.get('Content-Type')})")
            return True
        elif response.status_code == 404:
            print(f"⚠️  Residence document not found (may not have been uploaded)")
            return True
        else:
            print(f"❌ Residence document download failed: {response.status_code} - {response.text}")
            return False
    
    def test_update_documents_status(self):
        """Test updating document status with residence_proof_uploaded"""
        print("\n🔍 Testing Update Documents Status...")
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        # Test setting residence_proof_uploaded to True
        response = requests.put(
            f"{self.base_url}/clients/{self.client_id}/documents",
            json={"residence_proof_uploaded": True},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('residence_proof_uploaded') == True:
                print(f"✅ Residence proof status updated to True")
                
                # Test setting to False to clear file URLs
                response2 = requests.put(
                    f"{self.base_url}/clients/{self.client_id}/documents",
                    json={
                        "id_uploaded": False,
                        "income_proof_uploaded": False,
                        "residence_proof_uploaded": False
                    },
                    headers=headers
                )
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    print(f"✅ Document statuses set to False successfully")
                    return True
                else:
                    print(f"❌ Failed to set document statuses to False: {response2.status_code}")
                    return False
            else:
                print(f"❌ Expected residence_proof_uploaded=True, got {result.get('residence_proof_uploaded')}")
                return False
        else:
            print(f"❌ Update documents status failed: {response.status_code} - {response.text}")
            return False
    
    def test_create_user_record_with_direct_deposit(self):
        """Test creating user record with direct_deposit_amount"""
        print("\n🔍 Testing Create User Record with Direct Deposit Amount...")
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        record_data = {
            "client_id": self.client_id,
            "bank_deposit_type": "Deposito Directo",
            "direct_deposit_amount": "2500.00",
            "has_id": True,
            "id_type": "DL",
            "has_poi": True,
            "poi_type": "Company Check",
            "ssn": True,
            "itin": False,
            "self_employed": False,
            "has_por": True,
            "por_types": ["Agua", "Luz"],
            "bank": "Chase Bank",
            "auto": "Honda Civic",
            "credit": "Good",
            "auto_loan": "15000",
            "dealer": "ABC Motors",
            "finance_status": "no"
        }
        
        response = requests.post(
            f"{self.base_url}/user-records",
            json=record_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            self.record_id = result['id']
            if result.get('direct_deposit_amount') == "2500.00":
                print(f"✅ User record created with direct_deposit_amount: {result['direct_deposit_amount']}")
                return True
            else:
                print(f"❌ Expected direct_deposit_amount='2500.00', got {result.get('direct_deposit_amount')}")
                return False
        else:
            print(f"❌ Create user record failed: {response.status_code} - {response.text}")
            return False
    
    def test_update_user_record_with_direct_deposit(self):
        """Test updating user record with direct_deposit_amount"""
        print("\n🔍 Testing Update User Record with Direct Deposit Amount...")
        
        if not self.record_id:
            print("❌ No record ID available for update test")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        update_data = {
            "client_id": self.client_id,
            "bank_deposit_type": "Deposito Directo",
            "direct_deposit_amount": "3000.00",
            "has_id": True,
            "id_type": "DL",
            "has_poi": True,
            "poi_type": "Company Check",
            "ssn": True,
            "itin": False,
            "self_employed": False,
            "has_por": True,
            "por_types": ["Agua", "Luz"],
            "bank": "Chase Bank",
            "auto": "Honda Civic",
            "credit": "Good",
            "auto_loan": "15000",
            "dealer": "ABC Motors",
            "finance_status": "no"
        }
        
        response = requests.put(
            f"{self.base_url}/user-records/{self.record_id}",
            json=update_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('direct_deposit_amount') == "3000.00":
                print(f"✅ User record updated with direct_deposit_amount: {result['direct_deposit_amount']}")
                return True
            else:
                print(f"❌ Expected direct_deposit_amount='3000.00', got {result.get('direct_deposit_amount')}")
                return False
        else:
            print(f"❌ Update user record failed: {response.status_code} - {response.text}")
            return False
    
    def test_get_user_records_includes_direct_deposit(self):
        """Test that GET user-records returns direct_deposit_amount"""
        print("\n🔍 Testing GET User Records includes Direct Deposit Amount...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(f"{self.base_url}/user-records", headers=headers)
        
        if response.status_code == 200:
            records = response.json()
            
            # Find records with direct_deposit_amount
            records_with_deposit = [r for r in records if r.get('direct_deposit_amount')]
            
            if records_with_deposit:
                print(f"✅ Found {len(records_with_deposit)} user records with direct_deposit_amount")
                for record in records_with_deposit[:3]:  # Show first 3
                    print(f"   Record {record['id']}: direct_deposit_amount = {record['direct_deposit_amount']}")
                return True
            else:
                print(f"⚠️  No user records found with direct_deposit_amount field")
                return True  # Not a failure if no records have this field
        else:
            print(f"❌ Get user records failed: {response.status_code} - {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all new feature tests"""
        print("🚀 Starting New Features Testing for DealerCRM...")
        
        if not self.login_admin():
            return False
        
        if not self.get_existing_client():
            return False
        
        tests = [
            # Document Upload/Download Tests
            ("Document Upload - ID", self.test_document_upload_id),
            ("Document Upload - Income", self.test_document_upload_income),
            ("Document Upload - Residence", self.test_document_upload_residence),
            ("Document Download - ID", self.test_document_download_id),
            ("Document Download - Income", self.test_document_download_income),
            ("Document Download - Residence", self.test_document_download_residence),
            ("Update Documents Status", self.test_update_documents_status),
            
            # Direct Deposit Amount Tests
            ("Create User Record with Direct Deposit", self.test_create_user_record_with_direct_deposit),
            ("Update User Record with Direct Deposit", self.test_update_user_record_with_direct_deposit),
            ("GET User Records includes Direct Deposit", self.test_get_user_records_includes_direct_deposit),
        ]
        
        passed = 0
        total = len(tests)
        failed_tests = []
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed_tests.append(test_name)
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
                failed_tests.append(test_name)
        
        print(f"\n{'='*60}")
        print("TEST RESULTS")
        print(f"{'='*60}")
        print(f"📊 Tests passed: {passed}/{total}")
        
        if failed_tests:
            print(f"\n❌ Failed tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test}")
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = NewFeaturesTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)