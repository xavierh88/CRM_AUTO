#!/usr/bin/env python3
"""
Demo User Seeder for Dealer AI OS V2
Creates a demo user with fictional data for demonstration purposes.
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from authentication.foundation import hash_password

# Add backend to path
sys.path.insert(0, '/opt/dealer-ai-v2/worktrees/070-final-product-completion/backend')

from config import db, mongo_url, JWT_SECRET

async def seed_demo_user():
    """Create demo user and fictional data"""
    client = AsyncIOMotorClient(mongo_url)
    demo_db = client[db.name]
    
    demo_email = "demo@dealerai.com"
    demo_password = "demo123456"
    password_hash = hash_password(demo_password)
    
    # Check if demo user exists
    existing = await demo_db.users.find_one({"email": demo_email})
    if existing:
        print(f"Demo user already exists: {existing['_id']}")
        return existing['_id']
    
    # Create demo user
    demo_user_id = str(uuid.uuid4())
    demo_user = {
        "_id": demo_user_id,
        "id": demo_user_id,
        "email": demo_email,
        "password": password_hash,
        "name": "Demo User",
        "phone": "+1555000000",
        "role": "demo",
        "dealer_id": "demo-dealer",
        "is_active": True,
        "is_demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "avatar_url": None
    }
    
    await demo_db.users.insert_one(demo_user)
    print(f"Created demo user: {demo_user_id}")
    
    # Create fictional vehicles
    vehicles = [
        {
            "id": str(uuid.uuid4()), "vin": "1HGCM82633A123456", "make": "Honda", "model": "Accord",
            "year": 2023, "trim": "EX-L", "color": "White", "mileage": 15000, "price": 28500, "cost": 25000,
            "status": "available", "dealer": "Main", "stock_number": "H23-001", "days_on_lot": 45,
            "description": "Clean CarFax, one owner", "features": "Bluetooth, Backup Camera, Leather Seats, Sunroof",
            "images": [], "created_at": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "5TDZZRFH0MS123456", "make": "Toyota", "model": "RAV4",
            "year": 2024, "trim": "XLE", "color": "Blue", "mileage": 500, "price": 34500, "cost": 31000,
            "status": "available", "dealer": "Main", "stock_number": "T24-002", "days_on_lot": 12,
            "description": "New arrival, hybrid AWD", "features": "Bluetooth, Backup Camera, Blind Spot Monitor, Lane Keep Assist",
            "images": [], "created_at": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "1FTFW1E50MFA12345", "make": "Ford", "model": "F-150",
            "year": 2023, "trim": "Lariat", "color": "Black", "mileage": 22000, "price": 42000, "cost": 38000,
            "status": "reserved", "dealer": "North", "stock_number": "F23-003", "days_on_lot": 78,
            "description": "EcoBoost, 4WD, crew cab", "features": "Leather, Navigation, 360 Camera, Pro Trailer Backup",
            "images": [], "created_at": (datetime.now(timezone.utc) - timedelta(days=78)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "1G1BE5SM0N7123456", "make": "Chevrolet", "model": "Malibu",
            "year": 2024, "trim": "LT", "color": "Silver", "mileage": 100, "price": 26500, "cost": 23500,
            "status": "available", "dealer": "Main", "stock_number": "C24-004", "days_on_lot": 8,
            "description": "Fuel efficient sedan", "features": "Bluetooth, Backup Camera, Apple CarPlay, Android Auto",
            "images": [], "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "KM8K33AG0NU123456", "make": "Hyundai", "model": "Santa Fe",
            "year": 2023, "trim": "Limited", "color": "Red", "mileage": 18000, "price": 36500, "cost": 32500,
            "status": "sold", "dealer": "South", "stock_number": "H23-005", "days_on_lot": 120,
            "description": "Well maintained, all service records", "features": "Leather, Panoramic Sunroof, Heated Seats, Harman Kardon Audio",
            "images": [], "created_at": (datetime.now(timezone.utc) - timedelta(days=120)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
    ]
    
    await demo_db.inventory.insert_many(vehicles)
    print(f"Created {len(vehicles)} fictional vehicles")
    
    # Create fictional leads/customers
    now = datetime.now(timezone.utc)
    leads = [
        {
            "id": str(uuid.uuid4()), "first_name": "John", "last_name": "Smith", "phone": "+15551234567",
            "email": "john.smith@email.com", "address": "123 Main St, Anytown, ST 12345",
            "source": "Website", "commercial_stage": "NEW LEAD", "vehicle_interest": "2024 Honda Accord EX-L",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Interested in test drive this weekend", "follow_up_date": (now + timedelta(days=2)).date().isoformat(),
            "follow_up_notes": "Schedule test drive", "created_at": (now - timedelta(hours=5)).isoformat(),
            "last_contact": (now - timedelta(hours=5)).isoformat(), "is_sold": False,
            "id_uploaded": False, "income_proof_uploaded": False, "residence_proof_uploaded": False,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "Maria", "last_name": "Garcia", "phone": "+15559876543",
            "email": "maria.garcia@email.com", "address": "456 Oak Ave, Springfield, ST 67890",
            "source": "Walk-in", "commercial_stage": "CONTACTED", "vehicle_interest": "2024 Toyota RAV4 Hybrid",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Wants to compare RAV4 vs CR-V", "follow_up_date": (now + timedelta(days=1)).date().isoformat(),
            "follow_up_notes": "Send comparison sheet", "created_at": (now - timedelta(days=1)).isoformat(),
            "last_contact": (now - timedelta(hours=2)).isoformat(), "is_sold": False,
            "id_uploaded": True, "income_proof_uploaded": False, "residence_proof_uploaded": False,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "Robert", "last_name": "Johnson", "phone": "+15554567890",
            "email": "robert.j@email.com", "address": "789 Pine Rd, Lakeside, ST 54321",
            "source": "Facebook", "commercial_stage": "ENGAGED", "vehicle_interest": "2023 Ford F-150 Lariat",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Trade-in 2018 Silverado, needs appraisal", "follow_up_date": now.date().isoformat(),
            "follow_up_notes": "Complete trade appraisal", "created_at": (now - timedelta(days=3)).isoformat(),
            "last_contact": (now - timedelta(hours=24)).isoformat(), "is_sold": False,
            "id_uploaded": True, "income_proof_uploaded": True, "residence_proof_uploaded": False,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "Sarah", "last_name": "Williams", "phone": "+15552345678",
            "email": "sarah.w@email.com", "address": "321 Elm Blvd, Riverside, ST 98765",
            "source": "Referral", "commercial_stage": "APPOINTMENT", "vehicle_interest": "2024 Chevrolet Malibu LT",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Appointment scheduled for Saturday 10am", "follow_up_date": (now + timedelta(days=3)).date().isoformat(),
            "follow_up_notes": "Confirm appointment", "created_at": (now - timedelta(days=5)).isoformat(),
            "last_contact": (now - timedelta(hours=12)).isoformat(), "is_sold": False,
            "id_uploaded": True, "income_proof_uploaded": True, "residence_proof_uploaded": True,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "David", "last_name": "Brown", "phone": "+15553456789",
            "email": "david.brown@email.com", "address": "555 Cedar Ln, Hilltop, ST 11111",
            "source": "Phone", "commercial_stage": "NEGOTIATING", "vehicle_interest": "2023 Hyundai Santa Fe Limited",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Negotiating price, wants $500 off", "follow_up_date": (now - timedelta(days=1)).date().isoformat(),
            "follow_up_notes": "Follow up on counter-offer", "created_at": (now - timedelta(days=7)).isoformat(),
            "last_contact": (now - timedelta(days=2)).isoformat(), "is_sold": False,
            "id_uploaded": True, "income_proof_uploaded": True, "residence_proof_uploaded": True,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "Lisa", "last_name": "Davis", "phone": "+15554567891",
            "email": "lisa.davis@email.com", "address": "777 Maple Dr, Valley View, ST 22222",
            "source": "Email Campaign", "commercial_stage": "PENDING DEAL", "vehicle_interest": "2024 Toyota RAV4 XLE",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Credit approved, pending final paperwork", "follow_up_date": now.date().isoformat(),
            "follow_up_notes": "Finalize deal structure", "created_at": (now - timedelta(days=10)).isoformat(),
            "last_contact": (now - timedelta(hours=6)).isoformat(), "is_sold": False,
            "id_uploaded": True, "income_proof_uploaded": True, "residence_proof_uploaded": True,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "James", "last_name": "Wilson", "phone": "+15555678901",
            "email": "james.w@email.com", "address": "888 Birch Way, Summit, ST 33333",
            "source": "Third Party", "commercial_stage": "SOLD", "vehicle_interest": "2023 Chevrolet Malibu LT",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Deal closed, delivery scheduled", "follow_up_date": (now + timedelta(days=1)).date().isoformat(),
            "follow_up_notes": "Delivery confirmation", "created_at": (now - timedelta(days=14)).isoformat(),
            "last_contact": (now - timedelta(days=1)).isoformat(), "is_sold": True,
            "id_uploaded": True, "income_proof_uploaded": True, "residence_proof_uploaded": True,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
        {
            "id": str(uuid.uuid4()), "first_name": "Jennifer", "last_name": "Martinez", "phone": "+15556789012",
            "email": "jen.martinez@email.com", "address": "999 Spruce Ct, Meadowbrook, ST 44444",
            "source": "Previous Customer", "commercial_stage": "STOP/HOLD", "vehicle_interest": "2024 Honda Accord Touring",
            "assigned_salesperson": "Demo User", "assigned_salesperson_name": "Demo User",
            "notes": "Customer requested hold until next month", "follow_up_date": (now + timedelta(days=30)).date().isoformat(),
            "follow_up_notes": "Re-engage in 30 days", "created_at": (now - timedelta(days=20)).isoformat(),
            "last_contact": (now - timedelta(days=5)).isoformat(), "is_sold": False,
            "id_uploaded": False, "income_proof_uploaded": False, "residence_proof_uploaded": False,
            "created_by": demo_user_id, "dealer_id": "demo-dealer"
        },
    ]
    
    await demo_db.clients.insert_many(leads)
    print(f"Created {len(leads)} fictional leads/customers")
    
    # Create fictional appointments
    appointments = [
        {
            "id": str(uuid.uuid4()), "client_id": leads[0]["id"], "client_name": "John Smith",
            "client_phone": "+15551234567", "date": (now + timedelta(days=1)).date().isoformat(),
            "time": "10:00", "dealer": "Main", "type": "test_drive", "language": "en",
            "notes": "Test drive 2024 Honda Accord EX-L", "status": "agendado",
            "created_at": now.isoformat(), "created_by": demo_user_id
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[1]["id"], "client_name": "Maria Garcia",
            "client_phone": "+15559876543", "date": now.date().isoformat(),
            "time": "14:00", "dealer": "Main", "type": "showroom", "language": "es",
            "notes": "Compare RAV4 vs CR-V", "status": "agendado",
            "created_at": (now - timedelta(days=1)).isoformat(), "created_by": demo_user_id
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[2]["id"], "client_name": "Robert Johnson",
            "client_phone": "+15554567890", "date": (now + timedelta(days=2)).date().isoformat(),
            "time": "11:00", "dealer": "North", "type": "test_drive", "language": "en",
            "notes": "Test drive F-150, trade appraisal for Silverado", "status": "sin_configurar",
            "created_at": (now - timedelta(days=2)).isoformat(), "created_by": demo_user_id
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[3]["id"], "client_name": "Sarah Williams",
            "client_phone": "+15552345678", "date": (now + timedelta(days=3)).date().isoformat(),
            "time": "10:00", "dealer": "Main", "type": "delivery", "language": "en",
            "notes": "Delivery of 2024 Malibu LT", "status": "agendado",
            "created_at": (now - timedelta(days=4)).isoformat(), "created_by": demo_user_id
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[4]["id"], "client_name": "David Brown",
            "client_phone": "+15553456789", "date": (now - timedelta(days=1)).date().isoformat(),
            "time": "15:00", "dealer": "South", "type": "follow_up", "language": "en",
            "notes": "Follow up on Santa Fe negotiation", "status": "cambio_hora",
            "created_at": (now - timedelta(days=6)).isoformat(), "created_by": demo_user_id
        },
    ]
    
    await demo_db.appointments.insert_many(appointments)
    print(f"Created {len(appointments)} fictional appointments")
    
    # Create fictional conversations
    conversations = [
        {
            "id": str(uuid.uuid4()), "client_id": leads[0]["id"], "client_name": "John Smith",
            "client_phone": "+15551234567", "channel": "sms", "salesperson_id": demo_user_id,
            "last_message": "Thanks for the info! What's the best time Saturday?", "last_message_at": (now - timedelta(hours=2)).isoformat(),
            "unread_count": 2, "status": "active", "created_at": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[1]["id"], "client_name": "Maria Garcia",
            "client_phone": "+15559876543", "channel": "email", "salesperson_id": demo_user_id,
            "last_message": "When can I test drive the RAV4 Hybrid?", "last_message_at": (now - timedelta(hours=5)).isoformat(),
            "unread_count": 0, "status": "active", "created_at": (now - timedelta(days=2)).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[2]["id"], "client_name": "Robert Johnson",
            "client_phone": "+15554567890", "channel": "facebook", "salesperson_id": demo_user_id,
            "last_message": "Interested in the F-150, can we talk trade?", "last_message_at": (now - timedelta(hours=1)).isoformat(),
            "unread_count": 1, "status": "active", "created_at": (now - timedelta(days=3)).isoformat()
        },
    ]
    
    await demo_db.conversations.insert_many(conversations)
    print(f"Created {len(conversations)} fictional conversations")
    
    # Create fictional messages
    messages = []
    for conv in conversations:
        messages.extend([
            {
                "id": str(uuid.uuid4()), "conversation_id": conv["id"], "direction": "inbound",
                "body": f"Hi, I saw the {leads[0]['vehicle_interest'] if conv['client_id'] == leads[0]['id'] else 'vehicle'} online. Is it still available?",
                "created_at": (now - timedelta(hours=4)).isoformat(), "status": "read"
            },
            {
                "id": str(uuid.uuid4()), "conversation_id": conv["id"], "direction": "outbound",
                "body": "Yes it is! Would you like to schedule a test drive?",
                "created_at": (now - timedelta(hours=3)).isoformat(), "status": "sent"
            },
            {
                "id": str(uuid.uuid4()), "conversation_id": conv["id"], "direction": "inbound",
                "body": conv["last_message"],
                "created_at": conv["last_message_at"], "status": "delivered"
            },
        ])
    
    await demo_db.messages.insert_many(messages)
    print(f"Created {len(messages)} fictional messages")
    
    # Create fictional prequalifications
    prequals = [
        {
            "id": str(uuid.uuid4()), "client_id": leads[2]["id"], "client_name": "Robert Johnson",
            "client_email": "robert.j@email.com", "status": "APPROVED", "amount": 35000,
            "rate": 5.99, "term": 72, "lender": "Demo Credit Union",
            "created_at": (now - timedelta(days=2)).isoformat(), "updated_at": (now - timedelta(hours=12)).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[3]["id"], "client_name": "Sarah Williams",
            "client_email": "sarah.w@email.com", "status": "APPROVED", "amount": 28000,
            "rate": 4.99, "term": 60, "lender": "Demo Bank",
            "created_at": (now - timedelta(days=3)).isoformat(), "updated_at": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "client_id": leads[4]["id"], "client_name": "David Brown",
            "client_email": "david.brown@email.com", "status": "CONDITIONAL", "amount": 32000,
            "rate": 6.49, "term": 72, "lender": "Demo Finance",
            "created_at": (now - timedelta(days=5)).isoformat(), "updated_at": (now - timedelta(days=2)).isoformat()
        },
    ]
    
    await demo_db.prequalifications.insert_many(prequals)
    print(f"Created {len(prequals)} fictional prequalifications")
    
    # Create fictional activities
    activities = [
        {"id": str(uuid.uuid4()), "type": "lead_created", "description": "New lead: John Smith - 2024 Honda Accord EX-L",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"lead_id": leads[0]["id"]},
         "created_at": (now - timedelta(hours=5)).isoformat()},
        {"id": str(uuid.uuid4()), "type": "message_received", "description": "SMS from John Smith: Thanks for the info!",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"conversation_id": conversations[0]["id"]},
         "created_at": (now - timedelta(hours=2)).isoformat()},
        {"id": str(uuid.uuid4()), "type": "appointment_created", "description": "Appointment scheduled: Maria Garcia - RAV4 Comparison",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"appointment_id": appointments[1]["id"]},
         "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "type": "lead_updated", "description": "Lead stage updated: Robert Johnson → ENGAGED",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"lead_id": leads[2]["id"]},
         "created_at": (now - timedelta(hours=24)).isoformat()},
        {"id": str(uuid.uuid4()), "type": "prequalification_approved", "description": "Prequalification approved: Sarah Williams - $28,000",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"prequal_id": prequals[1]["id"]},
         "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "type": "deal_closed", "description": "Deal closed: James Wilson - 2023 Chevrolet Malibu LT",
         "user_id": demo_user_id, "user_name": "Demo User", "metadata": {"deal_value": 26500, "lead_id": leads[6]["id"]},
         "created_at": (now - timedelta(days=1)).isoformat()},
    ]
    
    await demo_db.activities.insert_many(activities)
    print(f"Created {len(activities)} fictional activities")
    
    print("\n✅ Demo user and fictional data seeded successfully!")
    print(f"Demo login: {demo_email} / {demo_password}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_demo_user())