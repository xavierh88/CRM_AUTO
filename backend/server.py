from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from twilio.rest import Client as TwilioClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'dealercrm-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        print(f"Warning: Could not initialize Twilio client: {e}")

# Create the main app
app = FastAPI(title="DealerCRM Pro API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

class UserActivate(BaseModel):
    user_id: str
    is_active: bool

class UserRoleUpdate(BaseModel):
    user_id: str
    role: str

class UserLogin(BaseModel):
    email: str  # Can be email or username
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    created_at: str

class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None

class ClientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    id_uploaded: bool = False
    income_proof_uploaded: bool = False
    last_record_date: Optional[str] = None  # Date of last record created (not last_contact)
    created_at: str
    created_by: str
    is_deleted: bool = False

class UserRecordCreate(BaseModel):
    client_id: str
    dl: bool = False
    checks: bool = False
    ssn: bool = False
    itin: bool = False
    auto: Optional[str] = None
    credit: Optional[str] = None
    bank: Optional[str] = None
    auto_loan: Optional[str] = None
    down_payment: Optional[str] = None
    dealer: Optional[str] = None
    # Finance status: financiado, least, no
    finance_status: str = "no"  # financiado, least, no
    # Vehicle info (only when finance_status is financiado or least)
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[int] = None
    sale_day: Optional[int] = None
    sale_year: Optional[int] = None
    previous_record_id: Optional[str] = None  # For "New Opportunity" - links to previous record

class UserRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    salesperson_id: str
    salesperson_name: str
    dl: bool = False
    checks: bool = False
    ssn: bool = False
    itin: bool = False
    auto: Optional[str] = None
    credit: Optional[str] = None
    bank: Optional[str] = None
    auto_loan: Optional[str] = None
    down_payment: Optional[str] = None
    dealer: Optional[str] = None
    # Finance status
    finance_status: str = "no"  # financiado, least, no
    # Vehicle info
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[int] = None
    sale_day: Optional[int] = None
    sale_year: Optional[int] = None
    created_at: str
    is_deleted: bool = False
    previous_record_id: Optional[str] = None  # Reference to previous opportunity
    opportunity_number: int = 1  # 1 = first, 2 = second opportunity, etc.

class AppointmentCreate(BaseModel):
    user_record_id: str
    client_id: str
    date: Optional[str] = None
    time: Optional[str] = None
    dealer: Optional[str] = None
    language: str = "en"  # en or es
    change_time: Optional[str] = None

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_record_id: str
    client_id: str
    salesperson_id: str
    date: Optional[str] = None
    time: Optional[str] = None
    dealer: Optional[str] = None
    language: str = "en"
    change_time: Optional[str] = None
    status: str = "sin_configurar"  # agendado, sin_configurar, cambio_hora, tres_semanas, no_show, cumplido
    link_sent_at: Optional[str] = None
    reminder_count: int = 0
    created_at: str

class CoSignerRelationCreate(BaseModel):
    buyer_client_id: str
    cosigner_client_id: str

class CoSignerRelationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    buyer_client_id: str
    cosigner_client_id: str
    created_at: str

class SMSLogCreate(BaseModel):
    client_id: str
    phone: str
    message_type: str  # documents, appointment, reminder
    status: str = "pending"

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=dict)
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "role": "salesperson",  # All new users are salesperson by default
        "phone": user.phone,
        "is_active": False,  # Users must be activated by admin
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Return success but no token - user needs admin activation
    return {"message": "Registration successful. Please wait for admin approval.", "user": {k: v for k, v in user_doc.items() if k != "password" and k != "_id"}}

@api_router.post("/auth/login", response_model=dict)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is active (admin accounts are always active)
    if not user.get("is_active", False) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Account not activated. Please wait for admin approval.")
    
    token = create_token(user["id"], user["email"], user["role"])
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== USERS ROUTES ====================

@api_router.get("/users", response_model=List[dict])
async def get_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users

@api_router.put("/users/activate")
async def activate_user(data: UserActivate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": data.user_id},
        {"$set": {"is_active": data.is_active}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {'activated' if data.is_active else 'deactivated'} successfully"}

@api_router.put("/users/role")
async def update_user_role(data: UserRoleUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if data.role not in ["admin", "salesperson"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'salesperson'")
    
    result = await db.users.update_one(
        {"id": data.user_id},
        {"$set": {"role": data.role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User role updated to {data.role}"}

# ==================== CLIENTS ROUTES ====================

@api_router.post("/clients", response_model=dict)
async def create_client(client: ClientCreate, current_user: dict = Depends(get_current_user)):
    # Check for existing client by phone
    existing = await db.clients.find_one({"phone": client.phone, "is_deleted": {"$ne": True}})
    if existing:
        raise HTTPException(status_code=400, detail="Client with this phone already exists")
    
    now = datetime.now(timezone.utc).isoformat()
    client_doc = {
        "id": str(uuid.uuid4()),
        "first_name": client.first_name,
        "last_name": client.last_name,
        "phone": client.phone,
        "email": client.email,
        "address": client.address,
        "apartment": client.apartment,
        "id_uploaded": False,
        "income_proof_uploaded": False,
        "last_record_date": None,  # No records yet
        "created_at": now,
        "created_by": current_user["id"],
        "is_deleted": False
    }
    await db.clients.insert_one(client_doc)
    del client_doc["_id"]
    return client_doc

import re as regex_module

@api_router.get("/clients", response_model=List[dict])
async def get_clients(include_deleted: bool = False, search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {} if include_deleted and current_user["role"] == "admin" else {"is_deleted": {"$ne": True}}
    
    # Add search filter for name and phone (escape special regex characters)
    if search:
        escaped_search = regex_module.escape(search)
        search_regex = {"$regex": escaped_search, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"phone": search_regex}
        ]
    
    clients = await db.clients.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # For each client, get the last record date
    for client in clients:
        last_record = await db.user_records.find_one(
            {"client_id": client["id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "created_at": 1},
            sort=[("created_at", -1)]
        )
        client["last_record_date"] = last_record["created_at"] if last_record else None
    
    return clients

@api_router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@api_router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(client_id: str, client: ClientCreate, current_user: dict = Depends(get_current_user)):
    update_data = client.model_dump(exclude_unset=True)
    update_data["last_contact"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.clients.update_one({"id": client_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return updated

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, permanent: bool = False, current_user: dict = Depends(get_current_user)):
    if permanent:
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required for permanent deletion")
        await db.clients.delete_one({"id": client_id})
    else:
        await db.clients.update_one({"id": client_id}, {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat(), "deleted_by": current_user["id"]}})
    return {"message": "Client deleted"}

@api_router.post("/clients/{client_id}/restore")
async def restore_client(client_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    await db.clients.update_one({"id": client_id}, {"$set": {"is_deleted": False}, "$unset": {"deleted_at": "", "deleted_by": ""}})
    return {"message": "Client restored"}

@api_router.put("/clients/{client_id}/documents")
async def update_client_documents(client_id: str, id_uploaded: bool = None, income_proof_uploaded: bool = None, current_user: dict = Depends(get_current_user)):
    update_data = {}
    if id_uploaded is not None:
        update_data["id_uploaded"] = id_uploaded
    if income_proof_uploaded is not None:
        update_data["income_proof_uploaded"] = income_proof_uploaded
    
    if update_data:
        await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return updated

# ==================== USER RECORDS (CARTILLAS) ROUTES ====================

@api_router.post("/user-records", response_model=dict)
async def create_user_record(record: UserRecordCreate, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if this is the first record for this client
    existing_records_count = await db.user_records.count_documents({"client_id": record.client_id, "is_deleted": {"$ne": True}})
    is_first_record = existing_records_count == 0
    
    # Calculate opportunity number
    opportunity_number = 1
    if record.previous_record_id:
        # This is a "New Opportunity" - count previous opportunities
        prev_record = await db.user_records.find_one({"id": record.previous_record_id})
        if prev_record:
            opportunity_number = prev_record.get("opportunity_number", 1) + 1
    
    record_doc = {
        "id": str(uuid.uuid4()),
        "client_id": record.client_id,
        "salesperson_id": current_user["id"],
        "salesperson_name": current_user["name"],
        **record.model_dump(exclude={"client_id"}),
        "opportunity_number": opportunity_number,
        "created_at": now,
        "is_deleted": False,
        "first_sms_sent": False,
        "last_reminder_sent": None
    }
    await db.user_records.insert_one(record_doc)
    
    # Update client last_record_date
    await db.clients.update_one({"id": record.client_id}, {"$set": {"last_record_date": now}})
    
    # Send automatic SMS if this is the first record for the client
    sms_sent = False
    if is_first_record and twilio_client:
        client = await db.clients.find_one({"id": record.client_id}, {"_id": 0})
        if client and client.get("phone"):
            client_name = f"{client['first_name']} {client['last_name']}"
            message = f"Hola {client_name}, gracias por visitarnos. Le mantendremos informado sobre su proceso de compra. Si tiene preguntas, no dude en contactarnos. - DealerCRM"
            
            result = await send_sms_twilio(client["phone"], message)
            
            # Log the automatic SMS
            sms_log = {
                "id": str(uuid.uuid4()),
                "client_id": record.client_id,
                "record_id": record_doc["id"],
                "phone": client["phone"],
                "message_type": "welcome_first_record",
                "message": message,
                "status": "sent" if result["success"] else "failed",
                "twilio_sid": result.get("sid"),
                "error": result.get("error"),
                "sent_at": now,
                "sent_by": current_user["id"],
                "automatic": True
            }
            await db.sms_logs.insert_one(sms_log)
            
            if result["success"]:
                sms_sent = True
                await db.user_records.update_one({"id": record_doc["id"]}, {"$set": {"first_sms_sent": True}})
                logger.info(f"Automatic welcome SMS sent to {client['phone']} for first record")
    
    del record_doc["_id"]
    record_doc["auto_sms_sent"] = sms_sent
    return record_doc

@api_router.get("/user-records", response_model=List[dict])
async def get_user_records(client_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {"is_deleted": {"$ne": True}}
    if client_id:
        query["client_id"] = client_id
    records = await db.user_records.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return records

@api_router.get("/user-records/{record_id}", response_model=UserRecordResponse)
async def get_user_record(record_id: str, current_user: dict = Depends(get_current_user)):
    record = await db.user_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="User record not found")
    return record

@api_router.put("/user-records/{record_id}", response_model=UserRecordResponse)
async def update_user_record(record_id: str, record: UserRecordCreate, current_user: dict = Depends(get_current_user)):
    update_data = record.model_dump(exclude_unset=True)
    result = await db.user_records.update_one({"id": record_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User record not found")
    
    # Update client last_contact
    await db.clients.update_one({"id": record.client_id}, {"$set": {"last_contact": datetime.now(timezone.utc).isoformat()}})
    
    updated = await db.user_records.find_one({"id": record_id}, {"_id": 0})
    return updated

@api_router.delete("/user-records/{record_id}")
async def delete_user_record(record_id: str, permanent: bool = False, current_user: dict = Depends(get_current_user)):
    if permanent:
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        await db.user_records.delete_one({"id": record_id})
    else:
        await db.user_records.update_one({"id": record_id}, {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "User record deleted"}

# ==================== APPOINTMENTS ROUTES ====================

@api_router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(appt: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    status = "agendado" if appt.date and appt.time else "sin_configurar"
    
    appt_doc = {
        "id": str(uuid.uuid4()),
        "user_record_id": appt.user_record_id,
        "client_id": appt.client_id,
        "salesperson_id": current_user["id"],
        "date": appt.date,
        "time": appt.time,
        "dealer": appt.dealer,
        "language": appt.language,
        "change_time": appt.change_time,
        "status": status,
        "link_sent_at": now,
        "reminder_count": 0,
        "created_at": now
    }
    await db.appointments.insert_one(appt_doc)
    del appt_doc["_id"]
    return appt_doc

@api_router.get("/appointments", response_model=List[AppointmentResponse])
async def get_appointments(
    salesperson_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if salesperson_id:
        query["salesperson_id"] = salesperson_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    appointments = await db.appointments.find(query, {"_id": 0}).sort("date", 1).to_list(1000)
    return appointments

@api_router.get("/appointments/agenda", response_model=List[dict])
async def get_agenda(current_user: dict = Depends(get_current_user)):
    """Get appointments for the current salesperson with client info"""
    pipeline = [
        {"$match": {"salesperson_id": current_user["id"]}},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "client"
        }},
        {"$unwind": {"path": "$client", "preserveNullAndEmptyArrays": True}},
        {"$project": {"_id": 0, "client._id": 0}},
        {"$sort": {"date": 1, "time": 1}}
    ]
    appointments = await db.appointments.aggregate(pipeline).to_list(1000)
    return appointments

@api_router.put("/appointments/{appt_id}", response_model=AppointmentResponse)
async def update_appointment(appt_id: str, appt: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    update_data = appt.model_dump(exclude_unset=True)
    
    # Determine status
    existing = await db.appointments.find_one({"id": appt_id})
    if appt.change_time and appt.change_time != existing.get("change_time"):
        update_data["status"] = "cambio_hora"
    elif appt.date and appt.time:
        update_data["status"] = "agendado"
    
    await db.appointments.update_one({"id": appt_id}, {"$set": update_data})
    updated = await db.appointments.find_one({"id": appt_id}, {"_id": 0})
    return updated

@api_router.put("/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, status: str, current_user: dict = Depends(get_current_user)):
    valid_statuses = ["agendado", "sin_configurar", "cambio_hora", "tres_semanas", "no_show", "cumplido"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    await db.appointments.update_one({"id": appt_id}, {"$set": {"status": status}})
    return {"message": "Status updated"}

@api_router.delete("/appointments/{appt_id}")
async def delete_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    await db.appointments.delete_one({"id": appt_id})
    return {"message": "Appointment deleted"}

# ==================== CO-SIGNER ROUTES ====================

@api_router.post("/cosigners", response_model=CoSignerRelationResponse)
async def create_cosigner_relation(relation: CoSignerRelationCreate, current_user: dict = Depends(get_current_user)):
    # Check if both clients exist
    buyer = await db.clients.find_one({"id": relation.buyer_client_id})
    cosigner = await db.clients.find_one({"id": relation.cosigner_client_id})
    
    if not buyer or not cosigner:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if relation already exists
    existing = await db.cosigner_relations.find_one({
        "buyer_client_id": relation.buyer_client_id,
        "cosigner_client_id": relation.cosigner_client_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Relation already exists")
    
    relation_doc = {
        "id": str(uuid.uuid4()),
        "buyer_client_id": relation.buyer_client_id,
        "cosigner_client_id": relation.cosigner_client_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.cosigner_relations.insert_one(relation_doc)
    del relation_doc["_id"]
    return relation_doc

@api_router.get("/cosigners/{buyer_client_id}", response_model=List[dict])
async def get_cosigners(buyer_client_id: str, current_user: dict = Depends(get_current_user)):
    """Get all co-signers for a buyer with their client info"""
    pipeline = [
        {"$match": {"buyer_client_id": buyer_client_id}},
        {"$lookup": {
            "from": "clients",
            "localField": "cosigner_client_id",
            "foreignField": "id",
            "as": "cosigner"
        }},
        {"$unwind": {"path": "$cosigner", "preserveNullAndEmptyArrays": True}},
        {"$project": {"_id": 0, "cosigner._id": 0}}
    ]
    relations = await db.cosigner_relations.aggregate(pipeline).to_list(100)
    return relations

@api_router.delete("/cosigners/{relation_id}")
async def delete_cosigner_relation(relation_id: str, current_user: dict = Depends(get_current_user)):
    await db.cosigner_relations.delete_one({"id": relation_id})
    return {"message": "Co-signer relation removed"}

@api_router.get("/clients/search/phone/{phone}")
async def search_client_by_phone(phone: str, current_user: dict = Depends(get_current_user)):
    """Search for a client by phone number (for adding existing co-signer)"""
    client = await db.clients.find_one({"phone": {"$regex": phone}, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    # Base query - admin sees all, salesperson sees their own
    base_query = {} if current_user["role"] == "admin" else {"salesperson_id": current_user["id"]}
    
    # Total clients
    total_clients = await db.clients.count_documents({"is_deleted": {"$ne": True}})
    
    # Appointments by status
    appt_stats = await db.appointments.aggregate([
        {"$match": base_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    appointment_counts = {stat["_id"]: stat["count"] for stat in appt_stats}
    
    # Documents status
    docs_complete = await db.clients.count_documents({"id_uploaded": True, "income_proof_uploaded": True, "is_deleted": {"$ne": True}})
    docs_pending = await db.clients.count_documents({"$or": [{"id_uploaded": False}, {"income_proof_uploaded": False}], "is_deleted": {"$ne": True}})
    
    # Sales count
    sales_count = await db.user_records.count_documents({"sold": True, "is_deleted": {"$ne": True}, **base_query} if base_query else {"sold": True, "is_deleted": {"$ne": True}})
    
    # Today's appointments
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_appointments = await db.appointments.count_documents({"date": today, **base_query})
    
    return {
        "total_clients": total_clients,
        "appointments": {
            "agendado": appointment_counts.get("agendado", 0),
            "sin_configurar": appointment_counts.get("sin_configurar", 0),
            "cambio_hora": appointment_counts.get("cambio_hora", 0),
            "tres_semanas": appointment_counts.get("tres_semanas", 0),
            "no_show": appointment_counts.get("no_show", 0),
            "cumplido": appointment_counts.get("cumplido", 0)
        },
        "documents": {
            "complete": docs_complete,
            "pending": docs_pending
        },
        "sales": sales_count,
        "today_appointments": today_appointments
    }

@api_router.get("/dashboard/salesperson-performance")
async def get_salesperson_performance(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pipeline = [
        {"$group": {
            "_id": "$salesperson_id",
            "salesperson_name": {"$first": "$salesperson_name"},
            "total_records": {"$sum": 1},
            "sales": {"$sum": {"$cond": ["$sold", 1, 0]}}
        }},
        {"$lookup": {
            "from": "appointments",
            "localField": "_id",
            "foreignField": "salesperson_id",
            "as": "appointments"
        }},
        {"$addFields": {
            "total_appointments": {"$size": "$appointments"},
            "completed_appointments": {
                "$size": {
                    "$filter": {
                        "input": "$appointments",
                        "as": "appt",
                        "cond": {"$eq": ["$$appt.status", "cumplido"]}
                    }
                }
            }
        }},
        {"$project": {
            "_id": 0,
            "salesperson_id": "$_id",
            "salesperson_name": 1,
            "total_records": 1,
            "sales": 1,
            "total_appointments": 1,
            "completed_appointments": 1
        }}
    ]
    
    performance = await db.user_records.aggregate(pipeline).to_list(100)
    return performance

# ==================== TRASH ROUTES (ADMIN) ====================

@api_router.get("/trash/clients", response_model=List[ClientResponse])
async def get_trash_clients(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    clients = await db.clients.find({"is_deleted": True}, {"_id": 0}).to_list(1000)
    return clients

@api_router.get("/trash/user-records", response_model=List[UserRecordResponse])
async def get_trash_user_records(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    records = await db.user_records.find({"is_deleted": True}, {"_id": 0}).to_list(1000)
    return records

# ==================== SMS ROUTES (TWILIO) ====================

async def send_sms_twilio(to_phone: str, message: str) -> dict:
    """Send SMS using Twilio. Returns status dict."""
    if not twilio_client:
        logger.warning("Twilio client not configured - SMS not sent")
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        # Ensure phone number is in E.164 format
        if not to_phone.startswith('+'):
            to_phone = '+1' + to_phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        message_obj = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        logger.info(f"SMS sent to {to_phone}: SID={message_obj.sid}")
        return {"success": True, "sid": message_obj.sid, "status": message_obj.status}
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
        return {"success": False, "error": str(e)}

@api_router.post("/sms/send-documents-link")
async def send_documents_sms(client_id: str, record_id: str, current_user: dict = Depends(get_current_user)):
    """Send SMS with documents upload link"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate public link token
    token = await create_public_link(client_id, record_id, "documents")
    
    # Get base URL from environment or use default
    base_url = os.environ.get('FRONTEND_URL', 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev')
    document_link = f"{base_url}/c/docs/{token}"
    
    # Create the message
    client_name = f"{client['first_name']} {client['last_name']}"
    message = f"Hola {client_name}, por favor suba sus documentos (ID y comprobante de ingresos) en: {document_link} - DealerCRM"
    
    # Send SMS via Twilio
    result = await send_sms_twilio(client["phone"], message)
    
    # Log the SMS
    sms_log = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "record_id": record_id,
        "phone": client["phone"],
        "message_type": "documents",
        "message": message,
        "link": document_link,
        "status": "sent" if result["success"] else "failed",
        "twilio_sid": result.get("sid"),
        "error": result.get("error"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"]
    }
    await db.sms_logs.insert_one(sms_log)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")
    
    return {"message": "Documents SMS sent successfully", "phone": client["phone"], "twilio_sid": result.get("sid"), "link": document_link}

@api_router.post("/sms/send-appointment-link")
async def send_appointment_sms(client_id: str, appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Send SMS with appointment scheduling/management link"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Generate public link token
    token = await create_public_link(client_id, appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one({"id": appointment_id}, {"$set": {"public_token": token}})
    
    # Get base URL from environment or use default
    base_url = os.environ.get('FRONTEND_URL', 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev')
    appointment_link = f"{base_url}/c/appointment/{token}"
    
    # Create the message
    client_name = f"{client['first_name']} {client['last_name']}"
    date_str = appointment.get("date", "pendiente")
    time_str = appointment.get("time", "")
    dealer_str = appointment.get("dealer", "")
    
    if appointment.get("language") == "es":
        message = f"Hola {client_name}, tiene una cita para el {date_str} a las {time_str} en {dealer_str}. Para ver, reprogramar o cancelar: {appointment_link} - DealerCRM"
    else:
        message = f"Hi {client_name}, you have an appointment for {date_str} at {time_str} at {dealer_str}. To view, reschedule or cancel: {appointment_link} - DealerCRM"
    
    # Send SMS via Twilio
    result = await send_sms_twilio(client["phone"], message)
    
    # Log the SMS
    sms_log = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "appointment_id": appointment_id,
        "phone": client["phone"],
        "message_type": "appointment",
        "message": message,
        "status": "sent" if result["success"] else "failed",
        "twilio_sid": result.get("sid"),
        "error": result.get("error"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"]
    }
    await db.sms_logs.insert_one(sms_log)
    
    # Update appointment link_sent_at
    await db.appointments.update_one(
        {"id": appointment_id}, 
        {"$set": {
            "link_sent_at": datetime.now(timezone.utc).isoformat(),
            "last_sms_sent": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")
    
    return {"message": "Appointment SMS sent successfully", "phone": client["phone"], "twilio_sid": result.get("sid")}

@api_router.post("/sms/send-reminder")
async def send_reminder_sms(client_id: str, record_id: str, current_user: dict = Depends(get_current_user)):
    """Send weekly reminder SMS for pending records"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    record = await db.user_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Don't send reminder if already sold
    if record.get("finance_status") in ["financiado", "least"]:
        return {"message": "No reminder needed - record already sold", "skipped": True}
    
    # Create reminder message
    client_name = f"{client['first_name']} {client['last_name']}"
    message = f"Hola {client_name}, le recordamos que tiene una oportunidad pendiente con nosotros. Por favor visite nuestro concesionario o contáctenos para más información. - DealerCRM"
    
    # Send SMS via Twilio
    result = await send_sms_twilio(client["phone"], message)
    
    # Log the SMS
    sms_log = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "record_id": record_id,
        "phone": client["phone"],
        "message_type": "reminder",
        "message": message,
        "status": "sent" if result["success"] else "failed",
        "twilio_sid": result.get("sid"),
        "error": result.get("error"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": current_user["id"]
    }
    await db.sms_logs.insert_one(sms_log)
    
    # Update record with last reminder date
    await db.user_records.update_one(
        {"id": record_id},
        {"$set": {"last_reminder_sent": datetime.now(timezone.utc).isoformat()}}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")
    
    return {"message": "Reminder SMS sent successfully", "phone": client["phone"], "twilio_sid": result.get("sid")}

@api_router.post("/sms/process-weekly-reminders")
async def process_weekly_reminders(current_user: dict = Depends(get_current_user)):
    """Process and send weekly reminders for all pending records (admin only or scheduled task)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not twilio_client:
        return {"message": "Twilio not configured", "sent": 0, "skipped": 0}
    
    now = datetime.now(timezone.utc)
    one_week_ago = (now - timedelta(days=7)).isoformat()
    
    # Find records that:
    # - Are NOT sold (finance_status != 'financiado' and != 'least')
    # - Haven't received a reminder in the last week
    # - Are not deleted
    query = {
        "is_deleted": {"$ne": True},
        "finance_status": {"$nin": ["financiado", "least"]},
        "$or": [
            {"last_reminder_sent": {"$lt": one_week_ago}},
            {"last_reminder_sent": None},
            {"last_reminder_sent": {"$exists": False}}
        ]
    }
    
    records = await db.user_records.find(query, {"_id": 0}).to_list(500)
    
    sent_count = 0
    skipped_count = 0
    errors = []
    
    for record in records:
        try:
            client = await db.clients.find_one({"id": record["client_id"], "is_deleted": {"$ne": True}}, {"_id": 0})
            if not client or not client.get("phone"):
                skipped_count += 1
                continue
            
            client_name = f"{client['first_name']} {client['last_name']}"
            message = f"Hola {client_name}, le recordamos que tiene una oportunidad pendiente con nosotros. Visite nuestro concesionario o contáctenos para más información. - DealerCRM"
            
            result = await send_sms_twilio(client["phone"], message)
            
            # Log the SMS
            sms_log = {
                "id": str(uuid.uuid4()),
                "client_id": record["client_id"],
                "record_id": record["id"],
                "phone": client["phone"],
                "message_type": "weekly_reminder",
                "message": message,
                "status": "sent" if result["success"] else "failed",
                "twilio_sid": result.get("sid"),
                "error": result.get("error"),
                "sent_at": now.isoformat(),
                "sent_by": "system_scheduler",
                "automatic": True
            }
            await db.sms_logs.insert_one(sms_log)
            
            if result["success"]:
                sent_count += 1
                await db.user_records.update_one(
                    {"id": record["id"]},
                    {"$set": {"last_reminder_sent": now.isoformat()}}
                )
            else:
                errors.append({"record_id": record["id"], "error": result.get("error")})
                
        except Exception as e:
            errors.append({"record_id": record["id"], "error": str(e)})
            skipped_count += 1
    
    return {
        "message": f"Weekly reminders processed",
        "sent": sent_count,
        "skipped": skipped_count,
        "total_processed": len(records),
        "errors": errors[:10]  # Return first 10 errors only
    }

@api_router.get("/sms/logs")
async def get_sms_logs(client_id: Optional[str] = None, limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get SMS logs for auditing"""
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    logs = await db.sms_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
    return logs

# ==================== PUBLIC CLIENT ROUTES (No Auth Required) ====================

import secrets
import base64

def generate_public_token(client_id: str, record_id: str, token_type: str) -> str:
    """Generate a unique token for public client links"""
    raw = f"{client_id}:{record_id}:{token_type}:{secrets.token_hex(8)}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

async def create_public_link(client_id: str, record_id: str, link_type: str) -> str:
    """Create and store a public link token"""
    token = generate_public_token(client_id, record_id, link_type)
    
    link_doc = {
        "id": str(uuid.uuid4()),
        "token": token,
        "client_id": client_id,
        "record_id": record_id,
        "link_type": link_type,  # 'documents' or 'appointment'
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "used": False
    }
    await db.public_links.insert_one(link_doc)
    return token

@api_router.post("/generate-document-link/{client_id}")
async def generate_document_link(client_id: str, record_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a public link for client to upload documents"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    token = await create_public_link(client_id, record_id, "documents")
    # The frontend URL would be: /c/docs/{token}
    return {"token": token, "link": f"/c/docs/{token}"}

@api_router.post("/generate-appointment-link/{appointment_id}")
async def generate_appointment_link(appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a public link for client to manage appointment"""
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    token = await create_public_link(appointment.get("client_id", ""), appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one({"id": appointment_id}, {"$set": {"public_token": token}})
    
    return {"token": token, "link": f"/c/appointment/{token}"}

# Public endpoints (no auth required)
@api_router.get("/public/documents/{token}")
async def get_public_document_info(token: str):
    """Get client info for document upload (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "documents"}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Link inválido o expirado")
    
    # Check expiration
    if datetime.fromisoformat(link["expires_at"].replace('Z', '+00:00')) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Este link ha expirado")
    
    client = await db.clients.find_one({"id": link["client_id"]}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Check if documents already submitted
    record = await db.user_records.find_one({"id": link["record_id"]}, {"_id": 0})
    documents_submitted = record.get("documents_submitted", False) if record else False
    
    return {
        "first_name": client["first_name"],
        "last_name": client["last_name"],
        "documents_submitted": documents_submitted
    }

@api_router.post("/public/documents/{token}/upload")
async def upload_public_documents(token: str):
    """Handle document upload from client (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "documents"}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Link inválido")
    
    # For now, just mark as submitted (actual file upload would need more setup)
    await db.user_records.update_one(
        {"id": link["record_id"]},
        {"$set": {
            "documents_submitted": True,
            "documents_submitted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Mark link as used
    await db.public_links.update_one({"token": token}, {"$set": {"used": True}})
    
    return {"message": "Documentos recibidos exitosamente"}

@api_router.get("/public/appointment/{token}")
async def get_public_appointment_info(token: str):
    """Get appointment info for client management (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    if not link:
        # Also try to find by appointment's public_token
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if not appointment:
            raise HTTPException(status_code=404, detail="Link inválido o expirado")
        client_id = appointment.get("client_id")
    else:
        appointment = await db.appointments.find_one({"id": link["record_id"]}, {"_id": 0})
        client_id = link["client_id"]
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    
    # Get dealers list for rescheduling
    dealers = await db.config_lists.find({"category": "dealer"}, {"_id": 0}).to_list(100)
    
    return {
        "appointment": appointment,
        "client": {
            "first_name": client["first_name"] if client else "Cliente",
            "last_name": client["last_name"] if client else ""
        },
        "dealers": dealers
    }

class RescheduleRequest(BaseModel):
    date: str
    time: str
    dealer: Optional[str] = None

@api_router.put("/public/appointment/{token}/reschedule")
async def reschedule_public_appointment(token: str, data: RescheduleRequest):
    """Reschedule appointment (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    appointment_id = link["record_id"] if link else None
    
    if not appointment_id:
        # Try by public_token
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if appointment:
            appointment_id = appointment["id"]
    
    if not appointment_id:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    update_data = {
        "date": data.date,
        "time": data.time,
        "status": "reagendado",
        "rescheduled_at": datetime.now(timezone.utc).isoformat()
    }
    if data.dealer:
        update_data["dealer"] = data.dealer
    
    await db.appointments.update_one({"id": appointment_id}, {"$set": update_data})
    return {"message": "Cita reprogramada exitosamente"}

@api_router.put("/public/appointment/{token}/cancel")
async def cancel_public_appointment(token: str):
    """Cancel appointment (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    appointment_id = link["record_id"] if link else None
    
    if not appointment_id:
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if appointment:
            appointment_id = appointment["id"]
    
    if not appointment_id:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "cancelado", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Cita cancelada"}

@api_router.put("/public/appointment/{token}/confirm")
async def confirm_public_appointment(token: str):
    """Confirm appointment (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    appointment_id = link["record_id"] if link else None
    
    if not appointment_id:
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if appointment:
            appointment_id = appointment["id"]
    
    if not appointment_id:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "confirmado", "confirmed_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Cita confirmada"}

class LateArrivalRequest(BaseModel):
    new_time: str

@api_router.put("/public/appointment/{token}/late")
async def notify_late_arrival(token: str, data: LateArrivalRequest):
    """Notify that client will arrive late and send SMS to salesperson (public, no auth)"""
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    appointment_id = link["record_id"] if link else None
    client_id = link["client_id"] if link else None
    
    if not appointment_id:
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if appointment:
            appointment_id = appointment["id"]
            # Get client_id from record
            record = await db.user_records.find_one({"id": appointment.get("record_id")}, {"_id": 0})
            if record:
                client_id = record.get("client_id")
    
    if not appointment_id:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    # Get appointment details
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    original_time = appointment.get("time", "N/A")
    
    # Get client info
    client = await db.clients.find_one({"id": client_id}, {"_id": 0}) if client_id else None
    client_name = f"{client['first_name']} {client['last_name']}" if client else "Cliente"
    
    # Get salesperson info to send notification
    record = await db.user_records.find_one({"id": appointment.get("record_id")}, {"_id": 0})
    if record:
        salesperson = await db.users.find_one({"id": record.get("salesperson_id")}, {"_id": 0})
        
        # Send SMS to salesperson if they have a phone number
        if salesperson and salesperson.get("phone") and twilio_client:
            message = f"AVISO: {client_name} llegará tarde a su cita. Hora original: {original_time}. Nueva hora de llegada: {data.new_time}. - DealerCRM"
            result = await send_sms_twilio(salesperson["phone"], message)
            
            # Log the SMS
            sms_log = {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "appointment_id": appointment_id,
                "phone": salesperson["phone"],
                "message_type": "late_notification",
                "message": message,
                "status": "sent" if result["success"] else "failed",
                "twilio_sid": result.get("sid"),
                "error": result.get("error"),
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": "client_public",
                "automatic": True
            }
            await db.sms_logs.insert_one(sms_log)
            logger.info(f"Late notification sent to salesperson {salesperson['name']}: {result}")
    
    # Update appointment with late arrival info
    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {
            "status": "llegará tarde",
            "original_time": original_time,
            "new_arrival_time": data.new_time,
            "late_notified_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Vendedor notificado exitosamente"}

# ==================== CONFIGURABLE LISTS (Banks, Dealers, Cars) ====================

class ConfigListItem(BaseModel):
    name: str
    category: str  # 'bank', 'dealer', 'car'

class ConfigListItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    created_at: str
    created_by: str

@api_router.get("/config-lists/{category}", response_model=List[ConfigListItemResponse])
async def get_config_list(category: str, current_user: dict = Depends(get_current_user)):
    """Get all items in a configurable list (bank, dealer, car)"""
    if category not in ['bank', 'dealer', 'car']:
        raise HTTPException(status_code=400, detail="Invalid category. Must be 'bank', 'dealer', or 'car'")
    items = await db.config_lists.find({"category": category}, {"_id": 0}).sort("name", 1).to_list(1000)
    return items

@api_router.post("/config-lists", response_model=ConfigListItemResponse)
async def create_config_list_item(item: ConfigListItem, current_user: dict = Depends(get_current_user)):
    """Add a new item to a configurable list (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if item.category not in ['bank', 'dealer', 'car']:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # Check for duplicate
    existing = await db.config_lists.find_one({"name": {"$regex": f"^{item.name}$", "$options": "i"}, "category": item.category})
    if existing:
        raise HTTPException(status_code=400, detail=f"{item.name} already exists in {item.category} list")
    
    item_doc = {
        "id": str(uuid.uuid4()),
        "name": item.name,
        "category": item.category,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    await db.config_lists.insert_one(item_doc)
    del item_doc["_id"]
    return item_doc

@api_router.delete("/config-lists/{item_id}")
async def delete_config_list_item(item_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an item from a configurable list (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.config_lists.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}

# ==================== CLIENT DELETE (Admin) ====================

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, permanent: bool = False, current_user: dict = Depends(get_current_user)):
    """Delete a client (soft delete by default, permanent if specified). Admin only."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to delete clients")
    
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if permanent:
        # Permanent delete
        await db.clients.delete_one({"id": client_id})
        # Also delete related records and appointments
        await db.user_records.delete_many({"client_id": client_id})
        await db.appointments.delete_many({"client_id": client_id})
        await db.cosigner_relations.delete_many({"$or": [{"buyer_client_id": client_id}, {"cosigner_client_id": client_id}]})
        return {"message": "Client permanently deleted"}
    else:
        # Soft delete
        await db.clients.update_one(
            {"id": client_id},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "Client moved to trash"}

@api_router.post("/clients/{client_id}/restore")
async def restore_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Restore a deleted client (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.clients.update_one(
        {"id": client_id, "is_deleted": True},
        {"$set": {"is_deleted": False}, "$unset": {"deleted_at": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deleted client not found")
    return {"message": "Client restored"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "DealerCRM Pro API", "version": "1.0.0"}

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def create_default_admin():
    """Create default admin account if it doesn't exist"""
    existing_admin = await db.users.find_one({"email": "xadmin"})
    if not existing_admin:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": "xadmin",
            "password": hash_password("Cali2020"),
            "name": "Administrator",
            "role": "admin",
            "phone": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        logger.info("Default admin account created: xadmin")
    
    # Initialize default config lists if empty
    await initialize_default_config_lists()

async def initialize_default_config_lists():
    """Initialize default banks, dealers, and cars if lists are empty"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Default US Banks
    default_banks = [
        "Chase", "Bank of America", "Wells Fargo", "Citibank", "US Bank",
        "Capital One", "PNC Bank", "TD Bank", "Truist", "Ally Bank",
        "Discover Bank", "Fifth Third Bank", "KeyBank", "Huntington Bank",
        "Santander", "BMO Harris", "Regions Bank", "Citizens Bank", "M&T Bank",
        "First Republic", "USAA", "Navy Federal", "Charles Schwab", "Goldman Sachs",
        "American Express", "Synchrony Bank", "Marcus by Goldman Sachs", "SoFi",
        "Chime", "Varo Bank", "Current", "Simple", "Aspiration"
    ]
    
    # Default Dealers
    default_dealers = ["Downey", "Long Beach"]
    
    # Default Car Makes/Models
    default_cars = [
        "Silverado", "Ram 1500", "F-150", "Tacoma", "Tundra", "Sierra",
        "Colorado", "Ranger", "Frontier", "Titan", "Gladiator",
        "Camry", "Accord", "Civic", "Corolla", "Altima", "Sentra",
        "Malibu", "Impala", "Fusion", "Sonata", "Elantra", "Optima",
        "CR-V", "RAV4", "Rogue", "Escape", "Explorer", "Highlander",
        "Pilot", "4Runner", "Pathfinder", "Tahoe", "Suburban", "Expedition",
        "Wrangler", "Grand Cherokee", "Cherokee", "Compass", "Durango",
        "Mustang", "Camaro", "Challenger", "Charger", "Corvette",
        "Model 3", "Model Y", "Model S", "Model X", "Mach-E",
        "BMW 3 Series", "BMW 5 Series", "Mercedes C-Class", "Mercedes E-Class",
        "Audi A4", "Audi Q5", "Lexus ES", "Lexus RX", "Acura TLX", "Acura MDX"
    ]
    
    # Check if lists are empty and populate
    for category, items in [('bank', default_banks), ('dealer', default_dealers), ('car', default_cars)]:
        count = await db.config_lists.count_documents({"category": category})
        if count == 0:
            docs = [
                {
                    "id": str(uuid.uuid4()),
                    "name": item,
                    "category": category,
                    "created_at": now,
                    "created_by": "system"
                }
                for item in items
            ]
            if docs:
                await db.config_lists.insert_many(docs)
                logger.info(f"Initialized {len(docs)} default {category}s")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
