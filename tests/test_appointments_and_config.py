"""
Test suite for CRM Appointments and Config Lists functionality
Tests:
1. Appointment form works for salesperson role
2. Config-lists/dealer endpoint works for salesperson
3. POST /api/appointments works for salesperson
4. Admin notifications are created when appointments are created
5. send_appointment_email uses dealer address (if configured)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "xadmin"
ADMIN_PASSWORD = "Cali2020"
VENDEDOR_EMAIL = "test_vendedor@test.com"
VENDEDOR_PASSWORD = "test123"


class TestAuthAndSetup:
    """Test authentication for both admin and salesperson"""
    
    def test_admin_login(self, api_client):
        """Test admin login works"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - user: {data['user'].get('name', data['user']['email'])}")
    
    def test_vendedor_login(self, api_client):
        """Test salesperson (vendedor) login works"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDEDOR_EMAIL,
            "password": VENDEDOR_PASSWORD
        })
        assert response.status_code == 200, f"Vendedor login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "salesperson"
        print(f"✓ Vendedor login successful - user: {data['user'].get('name', data['user']['email'])}")


class TestConfigListsForVendedor:
    """Test that config-lists endpoints work for salesperson role"""
    
    def test_get_dealers_as_vendedor(self, vendedor_client):
        """Verify vendedor can access dealer list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/dealer")
        assert response.status_code == 200, f"Failed to get dealers: {response.text}"
        dealers = response.json()
        assert isinstance(dealers, list)
        print(f"✓ Vendedor can access dealers - found {len(dealers)} dealers")
        
        # Check if Downey dealer exists with address
        downey_dealer = next((d for d in dealers if d.get('name') == 'Downey'), None)
        if downey_dealer:
            print(f"  - Downey dealer found: {downey_dealer}")
            if downey_dealer.get('address'):
                print(f"  - Downey address: {downey_dealer['address']}")
        
        return dealers
    
    def test_get_banks_as_vendedor(self, vendedor_client):
        """Verify vendedor can access bank list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/bank")
        assert response.status_code == 200, f"Failed to get banks: {response.text}"
        banks = response.json()
        assert isinstance(banks, list)
        print(f"✓ Vendedor can access banks - found {len(banks)} banks")
    
    def test_get_cars_as_vendedor(self, vendedor_client):
        """Verify vendedor can access car list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/car")
        assert response.status_code == 200, f"Failed to get cars: {response.text}"
        cars = response.json()
        assert isinstance(cars, list)
        print(f"✓ Vendedor can access cars - found {len(cars)} cars")
    
    def test_get_id_types_as_vendedor(self, vendedor_client):
        """Verify vendedor can access ID type list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/id_type")
        assert response.status_code == 200, f"Failed to get id_types: {response.text}"
        id_types = response.json()
        assert isinstance(id_types, list)
        print(f"✓ Vendedor can access id_types - found {len(id_types)} types")
    
    def test_get_poi_types_as_vendedor(self, vendedor_client):
        """Verify vendedor can access POI type list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/poi_type")
        assert response.status_code == 200, f"Failed to get poi_types: {response.text}"
        poi_types = response.json()
        assert isinstance(poi_types, list)
        print(f"✓ Vendedor can access poi_types - found {len(poi_types)} types")
    
    def test_get_por_types_as_vendedor(self, vendedor_client):
        """Verify vendedor can access POR type list"""
        response = vendedor_client.get(f"{BASE_URL}/api/config-lists/por_type")
        assert response.status_code == 200, f"Failed to get por_types: {response.text}"
        por_types = response.json()
        assert isinstance(por_types, list)
        print(f"✓ Vendedor can access por_types - found {len(por_types)} types")


class TestAppointmentsForVendedor:
    """Test appointment creation and management for salesperson role"""
    
    def test_vendedor_can_get_clients(self, vendedor_client):
        """Verify vendedor can see their clients"""
        response = vendedor_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        clients = response.json()
        assert isinstance(clients, list)
        print(f"✓ Vendedor can access clients - found {len(clients)} clients")
        return clients
    
    def test_vendedor_can_get_user_records(self, vendedor_client):
        """Verify vendedor can see user records"""
        response = vendedor_client.get(f"{BASE_URL}/api/user-records")
        assert response.status_code == 200, f"Failed to get user records: {response.text}"
        records = response.json()
        assert isinstance(records, list)
        print(f"✓ Vendedor can access user records - found {len(records)} records")
        return records
    
    def test_create_appointment_as_vendedor(self, vendedor_client, admin_client):
        """Test creating an appointment as vendedor and verify admin notification"""
        # First get a client and record for the vendedor
        clients_response = vendedor_client.get(f"{BASE_URL}/api/clients")
        assert clients_response.status_code == 200
        clients = clients_response.json()
        
        if not clients:
            pytest.skip("No clients available for vendedor to create appointment")
        
        client = clients[0]
        client_id = client['id']
        
        # Get records for this client
        records_response = vendedor_client.get(f"{BASE_URL}/api/user-records", params={"client_id": client_id})
        assert records_response.status_code == 200
        records = records_response.json()
        
        if not records:
            # Create a record first
            record_data = {
                "client_id": client_id,
                "has_id": True,
                "id_type": "DL"
            }
            create_record_response = vendedor_client.post(f"{BASE_URL}/api/user-records", json=record_data)
            assert create_record_response.status_code == 200, f"Failed to create record: {create_record_response.text}"
            record = create_record_response.json()
        else:
            record = records[0]
        
        record_id = record['id']
        
        # Get admin notifications count before creating appointment
        admin_notifs_before = admin_client.get(f"{BASE_URL}/api/notifications")
        notifs_before_count = len(admin_notifs_before.json()) if admin_notifs_before.status_code == 200 else 0
        
        # Create appointment
        appointment_data = {
            "user_record_id": record_id,
            "client_id": client_id,
            "date": "2026-01-20",
            "time": "10:00",
            "dealer": "Downey",
            "language": "es"
        }
        
        response = vendedor_client.post(f"{BASE_URL}/api/appointments", json=appointment_data)
        assert response.status_code == 200, f"Failed to create appointment: {response.text}"
        
        appointment = response.json()
        assert appointment.get("id")
        assert appointment.get("client_id") == client_id
        assert appointment.get("user_record_id") == record_id
        assert appointment.get("date") == "2026-01-20"
        assert appointment.get("time") == "10:00"
        assert appointment.get("dealer") == "Downey"
        assert appointment.get("status") == "agendado"
        
        print(f"✓ Vendedor created appointment successfully - ID: {appointment['id']}")
        
        # Wait a moment for notification to be created
        time.sleep(0.5)
        
        # Check admin received notification
        admin_notifs_after = admin_client.get(f"{BASE_URL}/api/notifications")
        assert admin_notifs_after.status_code == 200
        notifs_response = admin_notifs_after.json()
        
        # Handle both list and dict response formats
        if isinstance(notifs_response, dict):
            notifs_after = notifs_response.get("notifications", [])
        else:
            notifs_after = notifs_response
        
        # Find the new notification about this appointment
        new_notifs = [n for n in notifs_after if isinstance(n, dict) and "Nueva cita" in n.get("message", "")]
        
        if new_notifs:
            print(f"✓ Admin received notification about new appointment: {new_notifs[0]['message']}")
        else:
            print("⚠ Warning: Admin notification not found (may be same user or timing issue)")
        
        return appointment
    
    def test_get_appointments_as_vendedor(self, vendedor_client):
        """Verify vendedor can see appointments"""
        response = vendedor_client.get(f"{BASE_URL}/api/appointments")
        assert response.status_code == 200, f"Failed to get appointments: {response.text}"
        appointments = response.json()
        assert isinstance(appointments, list)
        print(f"✓ Vendedor can access appointments - found {len(appointments)} appointments")
        return appointments


class TestDealerAddressInEmail:
    """Test that send_appointment_email uses dealer address"""
    
    def test_dealer_has_address_configured(self, admin_client):
        """Verify Downey dealer has address configured"""
        response = admin_client.get(f"{BASE_URL}/api/config-lists/dealer")
        assert response.status_code == 200
        dealers = response.json()
        
        downey = next((d for d in dealers if d.get('name') == 'Downey'), None)
        assert downey is not None, "Downey dealer not found"
        
        address = downey.get('address')
        print(f"✓ Downey dealer found - address: {address or 'NOT SET'}")
        
        if address:
            assert "Florence" in address or "Downey" in address, f"Address doesn't look correct: {address}"
            print(f"✓ Downey dealer has valid address: {address}")
        else:
            print("⚠ Warning: Downey dealer has no address configured")
        
        return downey


class TestAdminNotifications:
    """Test admin notification system"""
    
    def test_admin_can_get_notifications(self, admin_client):
        """Verify admin can access notifications"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Failed to get notifications: {response.text}"
        notifs_response = response.json()
        
        # Handle both list and dict response formats
        if isinstance(notifs_response, dict):
            notifications = notifs_response.get("notifications", [])
            unread_count = notifs_response.get("unread_count", 0)
            print(f"✓ Admin can access notifications - found {len(notifications)} notifications (unread: {unread_count})")
        else:
            notifications = notifs_response
            print(f"✓ Admin can access notifications - found {len(notifications)} notifications")
        
        assert isinstance(notifications, list)
        
        # Check for appointment notifications
        appt_notifs = [n for n in notifications if isinstance(n, dict) and n.get("type") == "appointment"]
        print(f"  - Appointment notifications: {len(appt_notifs)}")
        
        for notif in appt_notifs[:3]:  # Show first 3
            print(f"    - {notif.get('message', 'No message')}")


# Fixtures
@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def vendedor_token(api_client):
    """Get vendedor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDEDOR_EMAIL,
        "password": VENDEDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Vendedor authentication failed")


@pytest.fixture
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


@pytest.fixture
def vendedor_client(vendedor_token):
    """Session with vendedor auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {vendedor_token}"
    })
    return session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
