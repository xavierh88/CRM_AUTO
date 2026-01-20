from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import shutil
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from twilio.rest import Client as TwilioClient
import pandas as pd
import io
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import resend
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi.responses import StreamingResponse
import json as json_lib

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
TWILIO_MESSAGING_SERVICE_SID = os.environ.get('TWILIO_MESSAGING_SERVICE_SID')

# Resend Email Configuration (optional - can use SMTP instead)
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# SMTP Email Configuration (FREE - Gmail, Outlook, etc.)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')  # Your email
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')  # App password
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'DealerCRM')

# Company Logo URL for emails and public forms
COMPANY_LOGO_URL = "https://carplusautosalesgroup.com/img/carplus.png"
COMPANY_NAME = "CARPLUS AUTOSALE"
COMPANY_TAGLINE = "Friendly Brokerage"

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

# Mount static files for uploads
from fastapi.staticfiles import StaticFiles
uploads_path = Path(__file__).parent / "uploads"
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== SCHEDULER ====================

scheduler = AsyncIOScheduler()

async def send_marketing_sms_job():
    """
    Scheduled job to send marketing SMS at 11:00 AM daily.
    Sends initial SMS to new contacts and weekly reminders to contacts without appointments.
    """
    logger.info("Running scheduled marketing SMS job...")
    
    if not twilio_client:
        logger.warning("Twilio client not configured - skipping SMS job")
        return
    
    now = datetime.now(timezone.utc)
    today = now.date()
    
    # Get contacts that need SMS
    # 1. New contacts that haven't received any SMS yet
    # 2. Contacts without appointments that need weekly reminders (up to 5 weeks)
    
    contacts_to_message = await db.imported_contacts.find({
        "opt_out": False,
        "appointment_created": False,
        "$or": [
            # Never sent SMS
            {"sms_sent": False},
            # Sent SMS but need weekly reminder (max 5 times)
            {
                "sms_sent": True,
                "sms_count": {"$lt": 5},
                "last_sms_sent": {"$lt": (now - timedelta(days=7)).isoformat()}
            }
        ]
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"Found {len(contacts_to_message)} contacts to message")
    
    # Get marketing template
    template_key = "marketing_initial"
    
    for contact in contacts_to_message:
        try:
            # Determine which template to use
            if contact.get("sms_count", 0) > 0:
                template_key = "marketing_reminder"
            
            template = await db.sms_templates.find_one({"template_key": template_key}, {"_id": 0})
            if not template:
                logger.warning(f"Template {template_key} not found")
                continue
            
            # Use Spanish message by default for marketing
            message_template = template.get("message_es", template.get("message_en", ""))
            
            # Generate appointment link
            token = generate_public_token(contact["id"], contact["id"], "marketing_appointment")
            base_url = os.environ.get('FRONTEND_URL', 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev')
            appointment_link = f"{base_url}/c/appointment/{token}"
            
            # Format message
            message = message_template.format(
                first_name=contact.get("first_name", ""),
                link=appointment_link
            )
            
            # Send SMS
            result = await send_sms_twilio(contact["phone_formatted"], message)
            
            # Update contact
            await db.imported_contacts.update_one(
                {"id": contact["id"]},
                {"$set": {
                    "sms_sent": True,
                    "sms_count": contact.get("sms_count", 0) + 1,
                    "last_sms_sent": now.isoformat(),
                    "status": "contacted"
                }}
            )
            
            # Log SMS
            sms_log = {
                "id": str(uuid.uuid4()),
                "contact_id": contact["id"],
                "phone": contact["phone_formatted"],
                "message_type": "marketing_scheduled",
                "message": message,
                "status": "sent" if result["success"] else "failed",
                "twilio_sid": result.get("sid"),
                "error": result.get("error"),
                "sent_at": now.isoformat(),
                "sent_by": "scheduler"
            }
            await db.sms_logs.insert_one(sms_log)
            
            if result["success"]:
                logger.info(f"Marketing SMS sent to {contact['phone_formatted']}")
            else:
                logger.error(f"Failed to send SMS to {contact['phone_formatted']}: {result.get('error')}")
            
            # Small delay between messages
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error sending SMS to contact {contact.get('id')}: {str(e)}")
    
    logger.info("Marketing SMS job completed")

async def check_comment_reminders_job():
    """
    Scheduled job to check for comment reminders that need to be sent.
    Runs every 5 minutes to check for comments with reminder_at in the past
    that haven't had their notification sent yet.
    """
    logger.info("Running comment reminders check job...")
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Find comments with reminders that are due
    due_reminders = await db.client_comments.find({
        "reminder_at": {"$ne": None, "$lte": now_iso},
        "reminder_sent": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"Found {len(due_reminders)} due reminders")
    
    for comment in due_reminders:
        try:
            # Get client info for the notification
            client = await db.clients.find_one({"id": comment["client_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
            
            # Create notification for the user who created the comment
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": comment["user_id"],
                "message": f"📝 Recordatorio: {client_name} - {comment['comment'][:50]}{'...' if len(comment['comment']) > 50 else ''}",
                "type": "reminder",
                "link": "/clientes",
                "is_read": False,
                "created_at": now_iso
            }
            await db.notifications.insert_one(notif_doc)
            
            # Mark reminder as sent
            await db.client_comments.update_one(
                {"id": comment["id"]},
                {"$set": {"reminder_sent": True}}
            )
            
            logger.info(f"Reminder notification sent for comment {comment['id']}")
        except Exception as e:
            logger.error(f"Error processing reminder {comment['id']}: {e}")
    
    logger.info("Comment reminders job completed")

async def check_appointment_reminders_job():
    """
    Scheduled job to check for appointments that are due tomorrow and send notifications.
    Runs once daily at 9:00 AM to notify users about appointments the next day.
    """
    logger.info("Running appointment reminders check job...")
    
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Find appointments scheduled for tomorrow that haven't been reminded
    tomorrow_appointments = await db.appointments.find({
        "date": tomorrow,
        "status": "agendado",
        "reminder_sent_day_before": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"Found {len(tomorrow_appointments)} appointments for tomorrow ({tomorrow})")
    
    for appt in tomorrow_appointments:
        try:
            # Get client info
            client = await db.clients.find_one({"id": appt["client_id"]}, {"_id": 0, "first_name": 1, "last_name": 1})
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
            
            # Get dealer info
            dealer_name = appt.get("dealer", "")
            
            # Create notification for the salesperson who created the appointment
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": appt["salesperson_id"],
                "message": f"📅 Recordatorio: Cita mañana con {client_name} a las {appt.get('time', '')} en {dealer_name}",
                "type": "appointment_reminder",
                "link": "/agenda",
                "is_read": False,
                "created_at": now.isoformat()
            }
            await db.notifications.insert_one(notif_doc)
            
            # Mark appointment as reminded
            await db.appointments.update_one(
                {"id": appt["id"]},
                {"$set": {"reminder_sent_day_before": True}}
            )
            
            logger.info(f"Appointment reminder sent for {appt['id']} - {client_name}")
        except Exception as e:
            logger.error(f"Error processing appointment reminder {appt['id']}: {e}")
    
    logger.info("Appointment reminders job completed")

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts"""
    # Schedule the marketing SMS job to run at 11:00 AM every day (US Eastern time)
    scheduler.add_job(
        send_marketing_sms_job,
        CronTrigger(hour=11, minute=0, timezone='America/Los_Angeles'),
        id='marketing_sms_job',
        replace_existing=True
    )
    
    # Schedule comment reminders job to run every 5 minutes
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        check_comment_reminders_job,
        IntervalTrigger(minutes=5),
        id='comment_reminders_job',
        replace_existing=True
    )
    
    # Schedule appointment reminders job to run daily at 9:00 AM Pacific
    scheduler.add_job(
        check_appointment_reminders_job,
        CronTrigger(hour=9, minute=0, timezone='America/Los_Angeles'),
        id='appointment_reminders_job',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started - Marketing SMS at 11:00 AM, Comment reminders every 5 min, Appointment reminders at 9:00 AM Pacific")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the app stops"""
    scheduler.shutdown()
    logger.info("SMS Scheduler stopped")

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
    # Date of birth
    date_of_birth: Optional[str] = None
    # ID fields (admin only for id_number)
    id_type: Optional[str] = None  # Licencia, Pasaporte, Matrícula Consular, etc.
    id_number: Optional[str] = None  # ID/License number (admin only)
    # SSN/ITIN fields
    ssn_type: Optional[str] = None  # SSN, ITIN, Ninguno
    ssn: Optional[str] = None  # Last 4 digits (admin only)
    # Time at address (accept str or int)
    time_at_address_years: Optional[Any] = None
    time_at_address_months: Optional[Any] = None
    # Housing type: Dueño, Renta, Vivo con familiares
    housing_type: Optional[str] = None
    rent_amount: Optional[str] = None  # Only when housing_type is "Renta"

class ClientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    # Date of birth
    date_of_birth: Optional[str] = None
    # ID fields (admin only for id_number)
    id_type: Optional[str] = None
    id_number: Optional[str] = None  # Admin only
    # SSN/ITIN fields
    ssn_type: Optional[str] = None
    ssn: Optional[str] = None  # Admin only
    # Time at address (can be int or str)
    time_at_address_years: Optional[Any] = None
    time_at_address_months: Optional[Any] = None
    # Housing type
    housing_type: Optional[str] = None
    rent_amount: Optional[str] = None
    id_uploaded: bool = False
    income_proof_uploaded: bool = False
    residence_proof_uploaded: bool = False
    id_file_url: Optional[str] = None
    income_proof_file_url: Optional[str] = None
    residence_proof_file_url: Optional[str] = None
    last_record_date: Optional[str] = None  # Date of last record created (not last_contact)
    created_at: str
    created_by: str
    is_deleted: bool = False

class UserRecordCreate(BaseModel):
    client_id: str
    # ID/DL fields (renamed from dl to id_type)
    has_id: bool = False
    id_type: Optional[str] = None  # DL, Passport, Matricula, Votacion ID, US Passport, Resident ID, Other
    # POI (Proof of Income) - renamed from checks
    has_poi: bool = False
    poi_type: Optional[str] = None  # Cash, Company Check, Personal Check, Talon de Cheque
    # SSN
    ssn: bool = False
    # ITIN
    itin: bool = False
    # Employment type: Company, Retired/workcomp/SSN/SDI, Unemployed, Self employed
    self_employed: bool = False  # Legacy field
    employment_type: Optional[str] = None  # Company, Retired/workcomp/SSN/SDI, Unemployed, Self employed
    employment_company_name: Optional[str] = None  # Company name when Company or Self employed
    employment_time_years: Optional[Any] = None  # Years at employment (accepts str or int)
    employment_time_months: Optional[Any] = None  # Months at employment (accepts str or int)
    # Income fields
    income_frequency: Optional[str] = None  # Semanal, Cada dos semanas, Dos veces al mes, Mensual
    net_income_amount: Optional[str] = None  # Net income amount
    # POR (Proof of Residence) - new
    has_por: bool = False
    por_types: Optional[List[str]] = None  # Agua, Luz, Gas, Internet, etc. (multiple selection)
    # Bank info with deposit type
    bank: Optional[str] = None
    bank_deposit_type: Optional[str] = None  # Deposito Directo, No deposito directo
    # Other fields
    auto: Optional[str] = None
    credit: Optional[str] = None
    # Auto Loan fields - Paid, Late, On Time (with bank and amount for On Time)
    first_time_buyer: bool = False  # New field
    auto_loan: Optional[str] = None  # Legacy field
    auto_loan_status: Optional[str] = None  # Paid, Late, On Time
    auto_loan_bank: Optional[str] = None  # Bank name when On Time
    auto_loan_amount: Optional[str] = None  # Amount when On Time
    # Down Payment with type
    down_payment_type: Optional[str] = None  # Cash, Tarjeta, Trade
    down_payment_types: Optional[List[str]] = None  # Multiple selection
    down_payment_cash: Optional[str] = None
    down_payment_card: Optional[str] = None
    # Trade-in vehicle info
    trade_make: Optional[str] = None
    trade_model: Optional[str] = None
    trade_year: Optional[str] = None
    trade_title: Optional[str] = None  # Clean Title, Salvaged
    trade_miles: Optional[str] = None
    trade_plate: Optional[str] = None  # CA, Out of State
    trade_estimated_value: Optional[str] = None
    # Dealer/Location
    dealer: Optional[str] = None
    # Finance status: financiado, lease, no (fixed typo)
    finance_status: str = "no"  # financiado, lease, no
    # Vehicle info (only when finance_status is financiado or lease)
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[int] = None
    sale_day: Optional[int] = None
    sale_year: Optional[int] = None
    previous_record_id: Optional[str] = None  # For "New Opportunity" - links to previous record
    # Collaborator - shared user working on this record
    collaborator_id: Optional[str] = None
    collaborator_name: Optional[str] = None
    # Record completion status: null, completed, no_show
    record_status: Optional[str] = None
    # Commission fields (admin only) - only visible when record_status is completed
    commission_percentage: Optional[float] = None  # 1-100
    commission_value: Optional[float] = None  # Dollar amount
    commission_locked: Optional[bool] = False  # When true, record_status cannot be changed by non-admins
    # Legacy fields for backward compatibility
    dl: Optional[bool] = None
    checks: Optional[bool] = None
    down_payment: Optional[str] = None

class UserRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    salesperson_id: Optional[str] = None
    salesperson_name: Optional[str] = None
    # ID fields
    has_id: bool = False
    id_type: Optional[str] = None
    # POI fields
    has_poi: bool = False
    poi_type: Optional[str] = None
    # Other checks
    ssn: bool = False
    itin: bool = False
    self_employed: bool = False  # Legacy
    # Employment fields
    employment_type: Optional[str] = None  # Company, Retired/workcomp/SSN/SDI, Unemployed, Self employed
    employment_company_name: Optional[str] = None
    employment_time_years: Optional[Any] = None
    employment_time_months: Optional[Any] = None
    # Income fields
    income_frequency: Optional[str] = None  # Semanal, Cada dos semanas, Dos veces al mes, Mensual
    net_income_amount: Optional[str] = None  # Net income amount
    # POR fields
    has_por: bool = False
    por_types: Optional[List[str]] = None
    # Bank info
    bank: Optional[str] = None
    bank_deposit_type: Optional[str] = None
    direct_deposit_amount: Optional[str] = None
    # Other fields
    auto: Optional[str] = None
    credit: Optional[str] = None
    # Auto Loan fields - Paid, Late, On Time (with bank and amount for On Time)
    auto_loan: Optional[str] = None  # Legacy field
    auto_loan_status: Optional[str] = None  # Paid, Late, On Time
    auto_loan_bank: Optional[str] = None  # Bank name when On Time
    auto_loan_amount: Optional[str] = None  # Amount when On Time
    # Down Payment
    down_payment_type: Optional[str] = None
    down_payment_types: Optional[List[str]] = None  # Multiple selection
    down_payment_cash: Optional[str] = None
    down_payment_card: Optional[str] = None
    # Trade-in
    trade_make: Optional[str] = None
    trade_model: Optional[str] = None
    trade_year: Optional[str] = None
    trade_title: Optional[str] = None
    trade_miles: Optional[str] = None
    trade_plate: Optional[str] = None
    trade_estimated_value: Optional[str] = None
    # Dealer
    dealer: Optional[str] = None
    # Finance status
    finance_status: str = "no"  # financiado, lease, no
    # Vehicle info
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[int] = None
    sale_day: Optional[int] = None
    sale_year: Optional[int] = None
    created_at: str
    is_deleted: bool = False
    previous_record_id: Optional[str] = None
    opportunity_number: int = 1
    # Collaborator
    collaborator_id: Optional[str] = None
    collaborator_name: Optional[str] = None
    # Record status
    record_status: Optional[str] = None
    # Commission fields (admin only)
    commission_percentage: Optional[float] = None
    commission_value: Optional[float] = None
    commission_locked: Optional[bool] = False
    # Legacy fields
    dl: Optional[bool] = False
    checks: Optional[bool] = False
    down_payment: Optional[str] = None

class AppointmentCreate(BaseModel):
    user_record_id: str
    client_id: str
    date: Optional[str] = None
    time: Optional[str] = None
    dealer: Optional[str] = None
    language: str = "en"  # en or es
    change_time: Optional[str] = None

class AppointmentUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    dealer: Optional[str] = None
    language: Optional[str] = None
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
        "role": "telemarketer",  # All new users are telemarketer by default (previously salesperson)
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
    
    # Valid roles: admin, bdc_manager, telemarketer (previously salesperson)
    valid_roles = ["admin", "bdc_manager", "telemarketer", "salesperson"]  # Keep salesperson for backwards compatibility
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    result = await db.users.update_one(
        {"id": data.user_id},
        {"$set": {"role": data.role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User role updated to {data.role}"}

@api_router.put("/users/{user_id}/email")
async def update_user_email(user_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Update user email - Admin only"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    new_email = data.get("email")
    if not new_email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": new_email, "id": {"$ne": user_id}})
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"email": new_email}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"Email updated to {new_email}"}

# ==================== CLIENTS ROUTES ====================

def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format for US numbers: +1XXXXXXXXXX
    Accepts various formats: 1234567890, (123) 456-7890, 123-456-7890, +1 123 456 7890, etc.
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters except +
    digits = re.sub(r'[^\d]', '', phone)
    
    # Handle different cases
    if len(digits) == 10:
        # US number without country code: 2134629914 -> +12134629914
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        # US number with country code: 12134629914 -> +12134629914
        return f"+{digits}"
    elif len(digits) > 11:
        # International number or has extra digits
        if not phone.startswith('+'):
            return f"+{digits}"
        return f"+{digits}"
    else:
        # Return as-is with + prefix if missing
        if not phone.startswith('+'):
            return f"+{digits}"
        return phone

@api_router.post("/clients", response_model=dict)
async def create_client(client: ClientCreate, current_user: dict = Depends(get_current_user)):
    # Normalize phone number to E.164 format
    normalized_phone = normalize_phone_number(client.phone)
    
    # Check for existing client by phone (check both original and normalized)
    existing = await db.clients.find_one({
        "$or": [
            {"phone": normalized_phone},
            {"phone": client.phone}
        ],
        "is_deleted": {"$ne": True}
    })
    
    if existing:
        # If client exists and belongs to someone else, return info to create a request
        if existing.get("created_by") != current_user["id"]:
            owner = await db.users.find_one({"id": existing.get("created_by")}, {"_id": 0, "name": 1})
            return {
                "error": "client_exists_other_user",
                "message": f"Este cliente ya existe y pertenece a {owner.get('name', 'otro usuario')}",
                "client_id": existing.get("id"),
                "owner_id": existing.get("created_by"),
                "owner_name": owner.get("name", "Unknown") if owner else "Unknown",
                "can_request": True
            }
        else:
            raise HTTPException(status_code=400, detail="Ya tienes este cliente registrado")
    
    now = datetime.now(timezone.utc).isoformat()
    client_doc = {
        "id": str(uuid.uuid4()),
        "first_name": client.first_name,
        "last_name": client.last_name,
        "phone": normalized_phone,  # Store normalized phone
        "email": client.email,
        "address": client.address,
        "apartment": client.apartment,
        "date_of_birth": client.date_of_birth,
        "time_at_address_years": client.time_at_address_years,
        "time_at_address_months": client.time_at_address_months,
        "housing_type": client.housing_type,
        "rent_amount": client.rent_amount,
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
async def get_clients(include_deleted: bool = False, search: Optional[str] = None, salesperson_id: Optional[str] = None, exclude_sold: bool = False, owner_filter: Optional[str] = None, sort_by: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {} if include_deleted and current_user["role"] == "admin" else {"is_deleted": {"$ne": True}}
    
    # Filter by owner - telemarketers can only see their own clients
    # Admin and BDC Manager can see all clients or filter by salesperson/owner
    if current_user["role"] in ["admin", "bdc", "bdc_manager"]:
        if salesperson_id:
            query["created_by"] = salesperson_id
        elif owner_filter:
            # owner_filter: 'mine' = only my clients, 'others' = clients from others, 'all' = no filter
            if owner_filter == 'mine':
                query["created_by"] = current_user["id"]
            elif owner_filter == 'others':
                query["created_by"] = {"$ne": current_user["id"]}
            # 'all' means no filter, show everything
    else:
        # Telemarketers (and legacy salesperson) only see their own clients
        query["created_by"] = current_user["id"]
    
    # Exclude sold clients if requested (for main Clients page)
    if exclude_sold:
        query["is_sold"] = {"$ne": True}
    
    # Add search filter for name and phone (escape special regex characters)
    if search:
        escaped_search = regex_module.escape(search)
        search_regex = {"$regex": escaped_search, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"phone": search_regex}
        ]
    
    # Determine sort field
    if sort_by == "activity":
        # Sort by last_contact (most recent activity first)
        sort_field = [("last_contact", -1), ("created_at", -1)]
    elif sort_by == "name":
        sort_field = [("first_name", 1), ("last_name", 1)]
    else:
        # Default: most recently created first
        sort_field = [("created_at", -1)]
    
    clients = await db.clients.find(query, {"_id": 0}).sort(sort_field).to_list(1000)
    
    now = datetime.now(timezone.utc)
    
    # For each client, get the last record date, sold count, and status color
    for client in clients:
        last_record = await db.user_records.find_one(
            {"client_id": client["id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "created_at": 1},
            sort=[("created_at", -1)]
        )
        client["last_record_date"] = last_record["created_at"] if last_record else None
        
        # Count sold records (record_status = 'completed' indicates a completed sale)
        sold_count = await db.user_records.count_documents({
            "client_id": client["id"],
            "is_deleted": {"$ne": True},
            "record_status": "completed"
        })
        client["sold_count"] = sold_count
        
        # Calculate status color based on last interaction
        # Use last_record_date or created_at as fallback
        last_interaction_str = client.get("last_record_date") or client.get("last_contact") or client.get("created_at")
        if last_interaction_str:
            try:
                # Parse the ISO date string
                if "T" in last_interaction_str:
                    last_interaction = datetime.fromisoformat(last_interaction_str.replace("Z", "+00:00"))
                else:
                    last_interaction = datetime.fromisoformat(last_interaction_str + "T00:00:00+00:00")
                
                days_since = (now - last_interaction).days
                
                if days_since >= 7:
                    client["status_color"] = "red"  # +7 days without interaction
                elif days_since >= 3:
                    client["status_color"] = "orange"  # +3 days without interaction
                else:
                    client["status_color"] = "green"  # Recent interaction
            except:
                client["status_color"] = "gray"  # Unable to determine
        else:
            client["status_color"] = "gray"
    
    return clients

@api_router.get("/clients/sold/list", response_model=List[dict])
async def get_sold_clients(search: Optional[str] = None, salesperson_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get clients that have been marked as sold"""
    query = {"is_deleted": {"$ne": True}, "is_sold": True}
    
    # Filter by owner - telemarketers can only see their own sold clients
    # Admin and BDC Manager can see all sold clients or filter by salesperson
    if current_user["role"] in ["admin", "bdc", "bdc_manager"]:
        if salesperson_id:
            query["created_by"] = salesperson_id
    else:
        # Telemarketers (and legacy salesperson) only see their own sold clients
        query["created_by"] = current_user["id"]
    
    # Add search filter for name and phone
    if search:
        escaped_search = regex_module.escape(search)
        search_regex = {"$regex": escaped_search, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"phone": search_regex}
        ]
    
    clients = await db.clients.find(query, {"_id": 0}).sort("sold_at", -1).to_list(1000)
    
    # For each client, get the sold record info
    for client in clients:
        sold_record = await db.user_records.find_one(
            {"client_id": client["id"], "is_deleted": {"$ne": True}, "record_status": "completed"},
            {"_id": 0, "finance_status": 1, "bank": 1, "auto": 1, "updated_at": 1}
        )
        if sold_record:
            client["sold_record"] = sold_record
    
    return clients

@api_router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Hide sensitive fields from non-admin users
    if current_user["role"] != "admin":
        client.pop("id_number", None)
        client.pop("ssn", None)
    
    return client

@api_router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(client_id: str, client: ClientCreate, current_user: dict = Depends(get_current_user)):
    update_data = client.model_dump(exclude_unset=True)
    update_data["last_contact"] = datetime.now(timezone.utc).isoformat()
    
    # Restrict sensitive fields to admin only
    if current_user["role"] != "admin":
        update_data.pop("id_number", None)
        update_data.pop("ssn", None)
    
    # Normalize phone number if provided
    if "phone" in update_data and update_data["phone"]:
        update_data["phone"] = normalize_phone_number(update_data["phone"])
    
    result = await db.clients.update_one({"id": client_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    
    # Hide sensitive fields from non-admin users
    if current_user["role"] != "admin":
        updated.pop("id_number", None)
        updated.pop("ssn", None)
    
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
async def update_client_documents(client_id: str, id_uploaded: bool = None, income_proof_uploaded: bool = None, residence_proof_uploaded: bool = None, current_user: dict = Depends(get_current_user)):
    update_data = {}
    if id_uploaded is not None:
        update_data["id_uploaded"] = id_uploaded
        if not id_uploaded:
            update_data["id_file_url"] = None
    if income_proof_uploaded is not None:
        update_data["income_proof_uploaded"] = income_proof_uploaded
        if not income_proof_uploaded:
            update_data["income_proof_file_url"] = None
    if residence_proof_uploaded is not None:
        update_data["residence_proof_uploaded"] = residence_proof_uploaded
        if not residence_proof_uploaded:
            update_data["residence_proof_file_url"] = None
    
    if update_data:
        await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return updated

# Document Upload/Download endpoints
import base64
from fastapi.responses import Response

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

@api_router.post("/clients/{client_id}/documents/upload")
async def upload_client_document(
    client_id: str, 
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document for a client (ID, income proof, or residence proof)"""
    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be 'id', 'income', or 'residence'")
    
    # Verify client exists
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Read file content
    content = await file.read()
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    
    # Create unique filename
    filename = f"{client_id}_{doc_type}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Update client document status
    update_data = {}
    file_url = f"/api/clients/{client_id}/documents/download/{doc_type}"
    
    if doc_type == 'id':
        update_data = {"id_uploaded": True, "id_file_url": str(file_path)}
    elif doc_type == 'income':
        update_data = {"income_proof_uploaded": True, "income_proof_file_url": str(file_path)}
    else:
        update_data = {"residence_proof_uploaded": True, "residence_proof_file_url": str(file_path)}
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    return {"message": "Document uploaded successfully", "file_url": file_url, "doc_type": doc_type}

@api_router.get("/clients/{client_id}/documents/download/{doc_type}")
async def download_client_document(
    client_id: str,
    doc_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a client document"""
    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get file path based on doc type
    if doc_type == 'id':
        file_url_field = "id_file_url"
    elif doc_type == 'income':
        file_url_field = "income_proof_file_url"
    else:  # residence
        file_url_field = "residence_proof_file_url"
    
    file_url = client.get(file_url_field)
    if not file_url:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Handle different path formats
    # Could be: /uploads/filename.pdf, uploads/filename.pdf, or full path
    if file_url.startswith('/uploads/'):
        file_path = UPLOAD_DIR / file_url.replace('/uploads/', '')
    elif file_url.startswith('uploads/'):
        file_path = UPLOAD_DIR / file_url.replace('uploads/', '')
    elif file_url.startswith('/api/'):
        # Extract filename from API URL
        filename = file_url.split('/')[-1]
        file_path = UPLOAD_DIR / filename
    else:
        file_path = Path(file_url)
    
    logger.info(f"Attempting to download document: {file_path}")
    
    if not file_path.exists():
        # Try looking in uploads directory with just the filename
        filename = Path(file_url).name if '/' in str(file_url) else file_url
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            logger.error(f"Document file not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"Document file not found: {filename}")
    
    # Read and return file
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading document file: {e}")
        raise HTTPException(status_code=500, detail="Error reading document file")
    
    # Determine content type
    file_ext = file_path.suffix.lower()
    content_type = 'application/pdf'
    if file_ext in ['.jpg', '.jpeg']:
        content_type = 'image/jpeg'
    elif file_ext == '.png':
        content_type = 'image/png'
    elif file_ext == '.webp':
        content_type = 'image/webp'
    
    # Sanitize filename for download
    safe_filename = f"{client.get('first_name', 'client')}_{client.get('last_name', 'doc')}_{doc_type}{file_ext}".replace(' ', '_')
    
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        }
    )

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
async def update_user_record(record_id: str, record_data: dict, current_user: dict = Depends(get_current_user)):
    # Clean the data - convert empty strings to None for numeric fields
    numeric_fields = ['sale_month', 'sale_day', 'sale_year', 'employment_time_years', 
                      'employment_time_months', 'commission_percentage', 'commission_value']
    
    cleaned_data = {}
    for key, value in record_data.items():
        if key in numeric_fields:
            if value == '' or value is None:
                cleaned_data[key] = None
            else:
                try:
                    if key in ['commission_percentage', 'commission_value']:
                        cleaned_data[key] = float(value) if value else None
                    else:
                        cleaned_data[key] = int(value) if value else None
                except (ValueError, TypeError):
                    cleaned_data[key] = None
        else:
            cleaned_data[key] = value
    
    # Get client_id from the data
    client_id = cleaned_data.get('client_id')
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")
    
    result = await db.user_records.update_one({"id": record_id}, {"$set": cleaned_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User record not found")
    
    # Update client last_contact
    client_update = {"last_contact": datetime.now(timezone.utc).isoformat()}
    
    # If record is marked as completed (sold), mark the client as sold too
    if cleaned_data.get("record_status") == "completed":
        client_update["is_sold"] = True
        client_update["sold_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.clients.update_one({"id": client_id}, {"$set": client_update})
    
    updated = await db.user_records.find_one({"id": record_id}, {"_id": 0})
    
    # Clean boolean fields that might have empty strings
    bool_fields = ['has_id', 'ssn', 'has_poi', 'has_por', 'self_employed', 'has_trade', 
                   'commission_locked', 'dl', 'checks', 'is_deleted']
    for field in bool_fields:
        if field in updated and updated[field] == '':
            updated[field] = False
        elif field in updated and updated[field] is None:
            updated[field] = False
    
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

# ==================== RECORD COMMENTS/NOTES ====================

@api_router.get("/user-records/{record_id}/comments")
async def get_record_comments(record_id: str, current_user: dict = Depends(get_current_user)):
    """Get all comments for a user record"""
    # Build query - if not admin, exclude admin_only comments
    query = {"record_id": record_id}
    if current_user["role"] != "admin":
        query["admin_only"] = {"$ne": True}
    
    comments = await db.record_comments.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return comments

@api_router.post("/user-records/{record_id}/comments")
async def add_record_comment(record_id: str, comment: str = Form(...), current_user: dict = Depends(get_current_user)):
    """Add a comment to a user record"""
    now = datetime.now(timezone.utc).isoformat()
    comment_doc = {
        "id": str(uuid.uuid4()),
        "record_id": record_id,
        "comment": comment,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", current_user.get("email", "Unknown")),
        "created_at": now
    }
    await db.record_comments.insert_one(comment_doc)
    return {k: v for k, v in comment_doc.items() if k != "_id"}

@api_router.delete("/user-records/{record_id}/comments/{comment_id}")
async def delete_record_comment(record_id: str, comment_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a comment (only admin can delete)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete comments")
    
    comment = await db.record_comments.find_one({"id": comment_id, "record_id": record_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    await db.record_comments.delete_one({"id": comment_id})
    return {"message": "Comment deleted"}

# ==================== CLIENT COMMENTS/NOTES ROUTES ====================

@api_router.get("/clients/{client_id}/comments")
async def get_client_comments(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get all comments/notes for a client"""
    comments = await db.client_comments.find(
        {"client_id": client_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return comments

@api_router.post("/clients/{client_id}/comments")
async def add_client_comment(client_id: str, comment: str = Form(...), reminder_at: Optional[str] = Form(None), current_user: dict = Depends(get_current_user)):
    """Add a comment/note to a client, optionally with a reminder"""
    now = datetime.now(timezone.utc).isoformat()
    comment_doc = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "comment": comment,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", current_user.get("email", "Unknown")),
        "created_at": now,
        "reminder_at": reminder_at,  # ISO datetime string for when to remind
        "reminder_sent": False  # Track if reminder notification was sent
    }
    await db.client_comments.insert_one(comment_doc)
    return {k: v for k, v in comment_doc.items() if k != "_id"}

@api_router.delete("/clients/{client_id}/comments/{comment_id}")
async def delete_client_comment(client_id: str, comment_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client comment (only admin can delete)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete comments")
    
    comment = await db.client_comments.find_one({"id": comment_id, "client_id": client_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    await db.client_comments.delete_one({"id": comment_id})
    return {"message": "Comment deleted"}

# ==================== SALESPERSONS LIST & EMAIL REPORT ====================

@api_router.get("/salespersons")
async def get_salespersons(current_user: dict = Depends(get_current_user)):
    """Get list of all active telemarketers for collaborator selection and filters"""
    # Define which roles to include based on current user's role
    if current_user["role"] == "admin":
        # Admin can see all users
        roles_to_include = ["salesperson", "telemarketer", "admin", "bdc_manager"]
    elif current_user["role"] == "bdc_manager":
        # BDC Manager can see telemarketers and other BDC managers, but NOT admins
        roles_to_include = ["salesperson", "telemarketer", "bdc_manager"]
    else:
        # Telemarketers only see other telemarketers (for collaboration)
        roles_to_include = ["salesperson", "telemarketer"]
    
    users = await db.users.find(
        {
            "role": {"$in": roles_to_include},
            "is_active": {"$ne": False},  # Only active users
            "is_deleted": {"$ne": True}   # Not deleted users
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(100)
    return users

class EmailReportRequest(BaseModel):
    emails: List[str]
    record_id: str
    client_id: str
    include_documents: bool = True
    attach_documents: bool = False  # Whether to attach actual document files

@api_router.post("/send-record-report")
async def send_record_report(request: EmailReportRequest, current_user: dict = Depends(get_current_user)):
    """Send record report via email to specified addresses"""
    
    # Get record data
    record = await db.user_records.find_one({"id": request.record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Get client data
    client = await db.clients.find_one({"id": request.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get co-signers for this client
    cosigner_relations = await db.cosigner_relations.find(
        {"buyer_client_id": request.client_id, "is_deleted": {"$ne": True}},
        {"_id": 0}
    ).to_list(10)
    
    cosigners_data = []
    for relation in cosigner_relations:
        cosigner = await db.clients.find_one({"id": relation.get("cosigner_client_id")}, {"_id": 0})
        if cosigner:
            # Get co-signer's records
            cosigner_records = await db.user_records.find(
                {"client_id": cosigner.get("id"), "is_deleted": {"$ne": True}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(5)
            cosigners_data.append({
                "info": cosigner,
                "records": cosigner_records,
                "relationship": relation.get("relationship", "Co-Signer")
            })
    
    # Build email body
    email_body = f"""
<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
.header {{ background: #1e3a8a; color: white; padding: 20px; text-align: center; }}
.header img {{ max-width: 150px; height: auto; margin-bottom: 10px; }}
.section {{ background: #f8fafc; padding: 15px; margin: 10px 0; border-radius: 8px; }}
.section-title {{ color: #1e40af; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #3b82f6; padding-bottom: 5px; }}
.info-row {{ padding: 5px 0; }}
.label {{ color: #64748b; font-weight: 500; }}
.value {{ color: #1e293b; }}
.badge {{ display: inline-block; background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }}
.badge-warning {{ background: #fef3c7; color: #92400e; }}
</style>
</head>
<body>
<div class="header">
<img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}" style="max-width: 150px; height: auto;">
<h1>📋 Reporte de Cliente</h1>
<p>Generado por: {current_user.get('name', current_user.get('email'))}</p>
</div>

<div class="section">
<div class="section-title">👤 Información del Cliente</div>
<div class="info-row"><span class="label">Nombre:</span> <span class="value">{client.get('first_name', '')} {client.get('last_name', '')}</span></div>
<div class="info-row"><span class="label">Teléfono:</span> <span class="value">{client.get('phone', 'N/A')}</span></div>
<div class="info-row"><span class="label">Email:</span> <span class="value">{client.get('email', 'N/A')}</span></div>
<div class="info-row"><span class="label">Dirección:</span> <span class="value">{client.get('address', 'N/A')} {client.get('apartment', '')}</span></div>
</div>

<div class="section">
<div class="section-title">📄 Documentación</div>
<div class="info-row">
"""
    
    # ID Information
    if record.get('has_id'):
        email_body += f'<span class="badge">✓ ID: {record.get("id_type", "Sí")}</span> '
    else:
        email_body += '<span class="badge badge-warning">✗ Sin ID</span> '
    
    # POI Information
    if record.get('has_poi'):
        email_body += f'<span class="badge">✓ POI: {record.get("poi_type", "Sí")}</span> '
    else:
        email_body += '<span class="badge badge-warning">✗ Sin POI</span> '
    
    # SSN/ITIN
    if record.get('ssn'):
        email_body += '<span class="badge">✓ SSN</span> '
    if record.get('itin'):
        email_body += '<span class="badge">✓ ITIN</span> '
    if record.get('self_employed'):
        email_body += '<span class="badge badge-warning">Self Employed</span> '
    
    # POR Information
    if record.get('has_por'):
        por_types = record.get('por_types', [])
        por_str = ', '.join(por_types) if por_types else 'Sí'
        email_body += f'<span class="badge">✓ POR: {por_str}</span> '
    
    email_body += """
</div>
</div>

<div class="section">
<div class="section-title">🏦 Información Bancaria y Financiera</div>
"""
    
    if record.get('bank'):
        email_body += f'<div class="info-row"><span class="label">Banco:</span> <span class="value">{record.get("bank")}</span></div>'
    if record.get('bank_deposit_type'):
        email_body += f'<div class="info-row"><span class="label">Tipo de Depósito:</span> <span class="value">{record.get("bank_deposit_type")}</span></div>'
    if record.get('direct_deposit_amount'):
        email_body += f'<div class="info-row"><span class="label">Monto Depósito Directo:</span> <span class="value">${record.get("direct_deposit_amount")}</span></div>'
    if record.get('credit'):
        email_body += f'<div class="info-row"><span class="label">Credit Score:</span> <span class="value">{record.get("credit")}</span></div>'
    if record.get('auto_loan'):
        email_body += f'<div class="info-row"><span class="label">Auto Loan:</span> <span class="value">${record.get("auto_loan")}</span></div>'
    
    email_body += """
</div>

<div class="section">
<div class="section-title">🚗 Vehículo de Interés</div>
"""
    
    if record.get('auto'):
        email_body += f'<div class="info-row"><span class="label">Auto:</span> <span class="value">{record.get("auto")}</span></div>'
    if record.get('dealer'):
        email_body += f'<div class="info-row"><span class="label">Dealer:</span> <span class="value">{record.get("dealer")}</span></div>'
    
    email_body += """
</div>

<div class="section">
<div class="section-title">💰 Down Payment</div>
"""
    
    if record.get('down_payment_type'):
        email_body += f'<div class="info-row"><span class="label">Tipo:</span> <span class="value">{record.get("down_payment_type")}</span></div>'
    if record.get('down_payment_cash'):
        email_body += f'<div class="info-row"><span class="label">Efectivo:</span> <span class="value">${record.get("down_payment_cash")}</span></div>'
    if record.get('down_payment_card'):
        email_body += f'<div class="info-row"><span class="label">Tarjeta:</span> <span class="value">${record.get("down_payment_card")}</span></div>'
    
    # Trade-in info
    if record.get('trade_make'):
        email_body += f"""
<div class="info-row"><span class="label">Trade-in:</span> <span class="value">{record.get('trade_make', '')} {record.get('trade_model', '')} {record.get('trade_year', '')}</span></div>
<div class="info-row"><span class="label">Title:</span> <span class="value">{record.get('trade_title', 'N/A')}</span></div>
<div class="info-row"><span class="label">Millas:</span> <span class="value">{record.get('trade_miles', 'N/A')}</span></div>
<div class="info-row"><span class="label">Valor Estimado:</span> <span class="value">${record.get('trade_estimated_value', 'N/A')}</span></div>
"""
    
    email_body += """
</div>
"""
    
    # Documents status
    if request.include_documents:
        email_body += """
<div class="section">
<div class="section-title">📎 Documentos del Cliente</div>
"""
        if client.get('id_uploaded'):
            email_body += '<div class="info-row"><span class="badge">✓ ID Subido</span></div>'
        else:
            email_body += '<div class="info-row"><span class="badge badge-warning">✗ ID Pendiente</span></div>'
        
        if client.get('income_proof_uploaded'):
            email_body += '<div class="info-row"><span class="badge">✓ Comprobante de Ingresos Subido</span></div>'
        else:
            email_body += '<div class="info-row"><span class="badge badge-warning">✗ Comprobante de Ingresos Pendiente</span></div>'
        
        if client.get('residence_proof_uploaded'):
            email_body += '<div class="info-row"><span class="badge">✓ Comprobante de Residencia Subido</span></div>'
        else:
            email_body += '<div class="info-row"><span class="badge badge-warning">✗ Comprobante de Residencia Pendiente</span></div>'
        
        email_body += """
</div>
"""
    
    # Finance status
    if record.get('finance_status') and record.get('finance_status') != 'no':
        email_body += f"""
<div class="section">
<div class="section-title">✅ Estado de Financiamiento</div>
<div class="info-row"><span class="label">Estado:</span> <span class="value" style="color: green; font-weight: bold;">{record.get('finance_status').upper()}</span></div>
"""
        if record.get('vehicle_make'):
            email_body += f'<div class="info-row"><span class="label">Vehículo:</span> <span class="value">{record.get("vehicle_make")} {record.get("vehicle_year", "")}</span></div>'
        if record.get('sale_month') and record.get('sale_day') and record.get('sale_year'):
            email_body += f'<div class="info-row"><span class="label">Fecha de Venta:</span> <span class="value">{record.get("sale_month")}/{record.get("sale_day")}/{record.get("sale_year")}</span></div>'
        email_body += """
</div>
"""
    
    # Collaborator info
    if record.get('collaborator_name'):
        email_body += f"""
<div class="section">
<div class="section-title">👥 Colaborador</div>
<div class="info-row"><span class="label">Trabajando con:</span> <span class="value">{record.get('collaborator_name')}</span></div>
</div>
"""
    
    # Co-signers section
    if cosigners_data:
        email_body += f"""
<div class="section" style="background: #faf5ff; border: 1px solid #e9d5ff;">
<div class="section-title" style="color: #7c3aed;">👥 Co-Signers ({len(cosigners_data)})</div>
"""
        for idx, cosigner in enumerate(cosigners_data, 1):
            cs_info = cosigner['info']
            cs_records = cosigner['records']
            relationship = cosigner['relationship']
            
            email_body += f"""
<div style="background: white; padding: 12px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #8b5cf6;">
<h4 style="margin: 0 0 10px 0; color: #6d28d9;">Co-Signer #{idx}: {cs_info.get('first_name', '')} {cs_info.get('last_name', '')} <span style="font-size: 12px; color: #a78bfa;">({relationship})</span></h4>
<div class="info-row"><span class="label">Teléfono:</span> <span class="value">{cs_info.get('phone', 'N/A')}</span></div>
<div class="info-row"><span class="label">Email:</span> <span class="value">{cs_info.get('email', 'N/A')}</span></div>
<div class="info-row"><span class="label">Dirección:</span> <span class="value">{cs_info.get('address', 'N/A')} {cs_info.get('apartment', '')}</span></div>
"""
            # Co-signer documents status
            email_body += '<div class="info-row" style="margin-top: 8px;"><span class="label">Documentos:</span> '
            if cs_info.get('id_uploaded'):
                email_body += '<span class="badge">✓ ID</span> '
            else:
                email_body += '<span class="badge badge-warning">✗ ID</span> '
            if cs_info.get('income_proof_uploaded'):
                email_body += '<span class="badge">✓ Ingresos</span> '
            else:
                email_body += '<span class="badge badge-warning">✗ Ingresos</span> '
            if cs_info.get('residence_proof_uploaded'):
                email_body += '<span class="badge">✓ Residencia</span> '
            else:
                email_body += '<span class="badge badge-warning">✗ Residencia</span> '
            email_body += '</div>'
            
            # Co-signer records
            if cs_records:
                email_body += '<div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e9d5ff;">'
                email_body += '<span class="label" style="display: block; margin-bottom: 5px;">Records del Co-Signer:</span>'
                for rec in cs_records:
                    email_body += '<div style="background: #faf5ff; padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 13px;">'
                    # ID/POI/SSN badges
                    if rec.get('has_id'):
                        email_body += f'<span class="badge">ID: {rec.get("id_type", "Sí")}</span> '
                    if rec.get('has_poi'):
                        email_body += f'<span class="badge">POI: {rec.get("poi_type", "Sí")}</span> '
                    if rec.get('ssn'):
                        email_body += '<span class="badge">SSN</span> '
                    if rec.get('itin'):
                        email_body += '<span class="badge">ITIN</span> '
                    
                    # Bank & Credit info
                    details = []
                    if rec.get('bank'):
                        bank_info = rec.get('bank')
                        if rec.get('bank_deposit_type'):
                            bank_info += f" ({rec.get('bank_deposit_type')})"
                        details.append(f"Bank: {bank_info}")
                    if rec.get('credit'):
                        details.append(f"Credit: {rec.get('credit')}")
                    if rec.get('auto'):
                        details.append(f"Auto: {rec.get('auto')}")
                    if rec.get('down_payment_type'):
                        dp_info = rec.get('down_payment_type')
                        if rec.get('down_payment_cash'):
                            dp_info += f" (Cash: ${rec.get('down_payment_cash')})"
                        if rec.get('down_payment_card'):
                            dp_info += f" (Tarjeta: ${rec.get('down_payment_card')})"
                        details.append(f"Down: {dp_info}")
                    
                    if details:
                        email_body += '<br><span style="color: #64748b; font-size: 12px;">' + ' • '.join(details) + '</span>'
                    email_body += '</div>'
                email_body += '</div>'
            
            email_body += '</div>'
        
        email_body += '</div>'
    
    email_body += f"""
<div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">
<p>Este reporte fue generado automáticamente desde DealerCRM</p>
<p>Vendedor: {record.get('salesperson_name', 'N/A')}</p>
<p>Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</p>
</div>
</body>
</html>
"""
    
    # Send email using SMTP
    smtp_email = os.environ.get('SMTP_USER') or os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        raise HTTPException(status_code=500, detail="Email configuration not set. Please configure SMTP_EMAIL and SMTP_PASSWORD.")
    
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        # Collect document attachments if requested
        attachments = []
        if request.attach_documents:
            uploads_dir = "/app/backend/uploads"
            
            # Client documents
            if client.get('id_file_url'):
                file_path = os.path.join(uploads_dir, os.path.basename(client['id_file_url']))
                if os.path.exists(file_path):
                    attachments.append({
                        'path': file_path,
                        'name': f"{client.get('first_name', 'Cliente')}_{client.get('last_name', '')}_ID{os.path.splitext(file_path)[1]}"
                    })
            
            if client.get('income_proof_file_url'):
                file_path = os.path.join(uploads_dir, os.path.basename(client['income_proof_file_url']))
                if os.path.exists(file_path):
                    attachments.append({
                        'path': file_path,
                        'name': f"{client.get('first_name', 'Cliente')}_{client.get('last_name', '')}_Ingresos{os.path.splitext(file_path)[1]}"
                    })
            
            if client.get('residence_proof_file_url'):
                file_path = os.path.join(uploads_dir, os.path.basename(client['residence_proof_file_url']))
                if os.path.exists(file_path):
                    attachments.append({
                        'path': file_path,
                        'name': f"{client.get('first_name', 'Cliente')}_{client.get('last_name', '')}_Residencia{os.path.splitext(file_path)[1]}"
                    })
            
            # Also include co-signer documents if available
            for idx, cosigner in enumerate(cosigners_data, 1):
                cs_info = cosigner['info']
                cs_name = f"CoSigner{idx}_{cs_info.get('first_name', '')}"
                
                if cs_info.get('id_file_url'):
                    file_path = os.path.join(uploads_dir, os.path.basename(cs_info['id_file_url']))
                    if os.path.exists(file_path):
                        attachments.append({
                            'path': file_path,
                            'name': f"{cs_name}_ID{os.path.splitext(file_path)[1]}"
                        })
                
                if cs_info.get('income_proof_file_url'):
                    file_path = os.path.join(uploads_dir, os.path.basename(cs_info['income_proof_file_url']))
                    if os.path.exists(file_path):
                        attachments.append({
                            'path': file_path,
                            'name': f"{cs_name}_Ingresos{os.path.splitext(file_path)[1]}"
                        })
                
                if cs_info.get('residence_proof_file_url'):
                    file_path = os.path.join(uploads_dir, os.path.basename(cs_info['residence_proof_file_url']))
                    if os.path.exists(file_path):
                        attachments.append({
                            'path': file_path,
                            'name': f"{cs_name}_Residencia{os.path.splitext(file_path)[1]}"
                        })
        
        for recipient_email in request.emails:
            msg = MIMEMultipart('mixed')  # Changed to 'mixed' to support attachments
            msg['Subject'] = f"📋 Reporte de Cliente: {client.get('first_name', '')} {client.get('last_name', '')}"
            msg['From'] = smtp_email
            msg['To'] = recipient_email.strip()
            
            # Create alternative part for HTML content
            alt_part = MIMEMultipart('alternative')
            html_part = MIMEText(email_body, 'html')
            alt_part.attach(html_part)
            msg.attach(alt_part)
            
            # Attach documents if requested
            for attachment in attachments:
                try:
                    with open(attachment['path'], 'rb') as f:
                        file_data = f.read()
                    
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{attachment["name"]}"')
                    msg.attach(part)
                except Exception as att_error:
                    print(f"Error attaching file {attachment['path']}: {str(att_error)}")
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, recipient_email.strip(), msg.as_string())
        
        attachment_msg = f" con {len(attachments)} documento(s) adjunto(s)" if attachments else ""
        return {"message": f"Reporte enviado exitosamente a {len(request.emails)} destinatario(s){attachment_msg}", "sent_to": request.emails, "attachments_count": len(attachments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

# ==================== NOTIFICATIONS SYSTEM ====================

@api_router.post("/notifications/collaborator")
async def send_collaborator_notification(
    record_id: str,
    action: str,  # record_updated, appointment_created, appointment_changed, comment_added
    details: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Send notification to collaborator about record changes"""
    
    record = await db.user_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Get client info
    client = await db.clients.find_one({"id": record.get("client_id")}, {"_id": 0})
    client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
    
    # Determine who to notify (the other person)
    notify_user_id = None
    if record.get('collaborator_id') and record.get('collaborator_id') != current_user['id']:
        notify_user_id = record.get('collaborator_id')
    elif record.get('salesperson_id') != current_user['id']:
        notify_user_id = record.get('salesperson_id')
    
    if not notify_user_id:
        return {"message": "No collaborator to notify"}
    
    # Get user to notify
    notify_user = await db.users.find_one({"id": notify_user_id}, {"_id": 0})
    if not notify_user or not notify_user.get('email'):
        return {"message": "Collaborator has no email configured"}
    
    # Action messages
    action_messages = {
        "record_updated": f"actualizó el record del cliente {client_name}",
        "appointment_created": f"creó una cita para el cliente {client_name}",
        "appointment_changed": f"modificó la cita del cliente {client_name}",
        "comment_added": f"agregó un comentario al record de {client_name}",
        "collaborator_added": f"te agregó como colaborador en el record de {client_name}"
    }
    
    action_text = action_messages.get(action, f"realizó una acción en el record de {client_name}")
    
    # Send email notification
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if smtp_email and smtp_password:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            email_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<div style="background: #1e3a8a; color: white; padding: 20px; text-align: center;">
<img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}" style="max-width: 150px; height: auto; margin-bottom: 10px;">
<h2>🔔 Notificación de Colaboración</h2>
</div>
<div style="padding: 20px;">
<p>Hola {notify_user.get('name', notify_user.get('email'))},</p>
<p><strong>{current_user.get('name', current_user.get('email'))}</strong> {action_text}.</p>
{f'<p style="background: #f1f5f9; padding: 10px; border-radius: 5px;">{details}</p>' if details else ''}
<p>Ingresa a DealerCRM para ver los detalles.</p>
<p style="color: #64748b; font-size: 12px;">Este es un mensaje automático del sistema de colaboración.</p>
</div>
</body>
</html>
"""
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🔔 {current_user.get('name', 'Usuario')} {action_text}"
            msg['From'] = smtp_email
            msg['To'] = notify_user.get('email')
            
            html_part = MIMEText(email_body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, notify_user.get('email'), msg.as_string())
            
            return {"message": "Notification sent", "notified": notify_user.get('email')}
        except Exception as e:
            print(f"Failed to send collaborator notification: {e}")
            return {"message": "Notification failed", "error": str(e)}
    
    return {"message": "Email not configured"}

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
        "salesperson_name": current_user.get("name", current_user.get("email", "")),
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
    
    try:
        await db.appointments.insert_one(appt_doc)
    except Exception as e:
        logger.error(f"Error inserting appointment: {e}")
        raise HTTPException(status_code=500, detail="Error al crear la cita")
    
    # Remove MongoDB _id if it was added
    appt_doc.pop("_id", None)
    
    # Get client name for notification
    client = await db.clients.find_one({"id": appt.client_id}, {"_id": 0, "first_name": 1, "last_name": 1})
    client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
    
    # Notify all admins about the new appointment
    try:
        admins = await db.users.find({"role": "admin", "is_active": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(100)
        for admin in admins:
            if admin["id"] != current_user["id"]:  # Don't notify the creator if they're admin
                notif_doc = {
                    "id": str(uuid.uuid4()),
                    "user_id": admin["id"],
                    "message": f"Nueva cita: {client_name} - {appt.date} {appt.time} ({appt.dealer}) por {current_user.get('name', '')}",
                    "type": "appointment",
                    "link": "/agenda",
                    "is_read": False,
                    "created_at": now
                }
                await db.notifications.insert_one(notif_doc)
    except Exception as e:
        logger.error(f"Error creating notifications: {e}")
        # Don't fail the appointment creation if notifications fail
    
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
    """Get appointments for the agenda view with client info.
    Admins see ALL appointments, others see only their own."""
    
    # Build match query based on role
    if current_user["role"] == "admin":
        # Admins see all appointments
        match_query = {}
    elif current_user["role"] == "bdc_manager":
        # BDC Managers see all non-admin appointments
        # First get all admin user IDs to exclude
        admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
        admin_ids = [u["id"] for u in admin_users]
        match_query = {"salesperson_id": {"$nin": admin_ids}}
    else:
        # Telemarketers see only their own appointments
        match_query = {"salesperson_id": current_user["id"]}
    
    pipeline = [
        {"$match": match_query},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "client"
        }},
        {"$unwind": {"path": "$client", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "salesperson_id",
            "foreignField": "id",
            "as": "salesperson"
        }},
        {"$unwind": {"path": "$salesperson", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0, 
            "client._id": 0,
            "salesperson._id": 0,
            "salesperson.password": 0
        }},
        {"$sort": {"date": 1, "time": 1}}
    ]
    appointments = await db.appointments.aggregate(pipeline).to_list(1000)
    return appointments

@api_router.put("/appointments/{appt_id}", response_model=AppointmentResponse)
async def update_appointment(appt_id: str, appt: AppointmentUpdate, current_user: dict = Depends(get_current_user)):
    update_data = appt.model_dump(exclude_unset=True, exclude_none=True)
    
    # Determine status
    existing = await db.appointments.find_one({"id": appt_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
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
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    period: str = "all",  # "all", "6months", "month", or specific "YYYY-MM"
    month: str = None  # Optional specific month in format "YYYY-MM"
):
    # Base query - admin sees all, salesperson sees their own
    base_query = {} if current_user["role"] == "admin" else {"salesperson_id": current_user["id"]}
    
    # Calculate date filters based on period
    now = datetime.now(timezone.utc)
    date_filter = {}
    
    if month:  # Specific month selected (e.g., "2026-01")
        year, mon = month.split("-")
        start_date = datetime(int(year), int(mon), 1, tzinfo=timezone.utc)
        if int(mon) == 12:
            end_date = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(int(year), int(mon) + 1, 1, tzinfo=timezone.utc)
        date_filter = {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
    elif period == "month":  # Current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"$gte": start_date.isoformat()}
    elif period == "6months":  # Last 6 months
        start_date = now - timedelta(days=180)
        date_filter = {"$gte": start_date.isoformat()}
    # else "all" - no date filter
    
    # Build queries with date filter
    clients_query = {"is_deleted": {"$ne": True}}
    if date_filter:
        clients_query["created_at"] = date_filter
    
    # Total clients (filtered by period)
    total_clients = await db.clients.count_documents(clients_query)
    
    # Total clients overall (for reference)
    total_clients_all = await db.clients.count_documents({"is_deleted": {"$ne": True}})
    
    # New clients this month (always current month for comparison)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_clients_month = await db.clients.count_documents({
        "is_deleted": {"$ne": True},
        "created_at": {"$gte": first_of_month.isoformat()}
    })
    
    # Appointments query with date filter
    appt_query = {**base_query}
    if date_filter:
        appt_query["created_at"] = date_filter
    
    # Appointments by status
    appt_stats = await db.appointments.aggregate([
        {"$match": appt_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    appointment_counts = {stat["_id"]: stat["count"] for stat in appt_stats}
    
    # Documents status (not filtered by date - shows current state)
    docs_complete = await db.clients.count_documents({"id_uploaded": True, "income_proof_uploaded": True, "is_deleted": {"$ne": True}})
    docs_pending = await db.clients.count_documents({"$or": [{"id_uploaded": False}, {"income_proof_uploaded": False}], "is_deleted": {"$ne": True}})
    
    # Sales count with date filter
    sales_query = {"finance_status": {"$in": ["financiado", "lease"]}, "is_deleted": {"$ne": True}}
    if base_query:
        sales_query.update(base_query)
    if date_filter:
        sales_query["created_at"] = date_filter
    sales_count = await db.user_records.count_documents(sales_query)
    
    # Sales this month
    sales_month_query = {
        "finance_status": {"$in": ["financiado", "lease"]}, 
        "is_deleted": {"$ne": True},
        "created_at": {"$gte": first_of_month.isoformat()}
    }
    if base_query:
        sales_month_query.update(base_query)
    sales_month = await db.user_records.count_documents(sales_month_query)
    
    # Today's appointments
    today = now.strftime("%Y-%m-%d")
    today_appointments = await db.appointments.count_documents({"date": today, **base_query})
    
    # This week's appointments
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_end = (now + timedelta(days=6-now.weekday())).strftime("%Y-%m-%d")
    week_appointments = await db.appointments.count_documents({
        "date": {"$gte": week_start, "$lte": week_end},
        **base_query
    })
    
    # Total records with date filter
    records_query = {"is_deleted": {"$ne": True}}
    if base_query:
        records_query.update(base_query)
    if date_filter:
        records_query["created_at"] = date_filter
    total_records = await db.user_records.count_documents(records_query)
    
    # Co-signers count
    total_cosigners = await db.cosigner_relations.count_documents({})
    
    # Sold clients count (clients with is_sold = true)
    sold_clients = await db.clients.count_documents({"is_sold": True, "is_deleted": {"$ne": True}})
    
    # Recent activity - clients contacted in last 7 days
    week_ago = (now - timedelta(days=7)).isoformat()
    active_clients = await db.clients.count_documents({
        "is_deleted": {"$ne": True},
        "last_contact": {"$gte": week_ago}
    })
    
    # Finance type breakdown with date filter
    finance_match = {"finance_status": {"$in": ["financiado", "lease"]}, "is_deleted": {"$ne": True}}
    if date_filter:
        finance_match["created_at"] = date_filter
    finance_stats = await db.user_records.aggregate([
        {"$match": finance_match},
        {"$group": {"_id": "$finance_status", "count": {"$sum": 1}}}
    ]).to_list(10)
    finance_breakdown = {stat["_id"]: stat["count"] for stat in finance_stats}
    
    # Monthly sales trend (last 6 months or based on period)
    trend_start = now - timedelta(days=180)
    monthly_sales = await db.user_records.aggregate([
        {
            "$match": {
                "finance_status": {"$in": ["financiado", "lease"]},
                "is_deleted": {"$ne": True},
                "created_at": {"$gte": trend_start.isoformat()}
            }
        },
        {
            "$group": {
                "_id": {"$substr": ["$created_at", 0, 7]},  # YYYY-MM
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(12)
    
    # Get available months for filter dropdown
    available_months = await db.user_records.aggregate([
        {"$match": {"is_deleted": {"$ne": True}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 7]}}},
        {"$sort": {"_id": -1}},
        {"$limit": 12}
    ]).to_list(12)
    
    # Calculate total down payment collected
    dp_match = {"is_deleted": {"$ne": True}}
    if date_filter:
        dp_match["created_at"] = date_filter
    
    # Get all records with down payment info
    records_with_dp = await db.user_records.find(
        dp_match,
        {"down_payment_cash": 1, "down_payment_card": 1, "trade_estimated_value": 1, "_id": 0}
    ).to_list(None)
    
    total_down_payment = 0
    for rec in records_with_dp:
        # Parse and sum down_payment_cash
        if rec.get("down_payment_cash"):
            try:
                cash_str = str(rec["down_payment_cash"]).replace("$", "").replace(",", "").strip()
                if cash_str:
                    total_down_payment += float(cash_str)
            except (ValueError, TypeError):
                pass
        # Parse and sum down_payment_card
        if rec.get("down_payment_card"):
            try:
                card_str = str(rec["down_payment_card"]).replace("$", "").replace(",", "").strip()
                if card_str:
                    total_down_payment += float(card_str)
            except (ValueError, TypeError):
                pass
        # Parse and sum trade_estimated_value
        if rec.get("trade_estimated_value"):
            try:
                trade_str = str(rec["trade_estimated_value"]).replace("$", "").replace(",", "").strip()
                if trade_str:
                    total_down_payment += float(trade_str)
            except (ValueError, TypeError):
                pass
    
    return {
        "total_clients": total_clients,
        "total_clients_all": total_clients_all,
        "new_clients_month": new_clients_month,
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
        "sales_month": sales_month,
        "today_appointments": today_appointments,
        "week_appointments": week_appointments,
        "total_records": total_records,
        "total_cosigners": total_cosigners,
        "sold_clients": sold_clients,
        "active_clients": active_clients,
        "finance_breakdown": finance_breakdown,
        "monthly_sales": [{"month": s["_id"], "sales": s["count"]} for s in monthly_sales],
        "available_months": [m["_id"] for m in available_months],
        "current_period": month or period,
        "total_down_payment": round(total_down_payment, 2)
    }

@api_router.get("/dashboard/salesperson-performance")
async def get_salesperson_performance(current_user: dict = Depends(get_current_user)):
    # Admin and BDC Manager can see salesperson performance
    if current_user["role"] not in ["admin", "bdc", "bdc_manager"]:
        raise HTTPException(status_code=403, detail="Admin or BDC Manager access required")
    
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
    """Send SMS using Twilio with A2P 10DLC Messaging Service. Returns status dict."""
    if not twilio_client:
        logger.warning("Twilio client not configured - SMS not sent")
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        # Ensure phone number is in E.164 format
        if not to_phone.startswith('+'):
            to_phone = '+1' + to_phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Use Messaging Service SID for A2P 10DLC compliance (required)
        # Falls back to phone number if Messaging Service not configured
        if TWILIO_MESSAGING_SERVICE_SID:
            message_obj = twilio_client.messages.create(
                body=message,
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                to=to_phone
            )
            logger.info(f"SMS sent via Messaging Service to {to_phone}: SID={message_obj.sid}")
        else:
            message_obj = twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            logger.info(f"SMS sent via phone number to {to_phone}: SID={message_obj.sid}")
        
        return {"success": True, "sid": message_obj.sid, "status": message_obj.status}
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
        return {"success": False, "error": str(e)}

@api_router.post("/sms/test")
async def test_sms(phone: str, message: str = "Prueba de SMS desde CARPLUS CRM", current_user: dict = Depends(get_current_user)):
    """Test SMS endpoint - Admin only"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await send_sms_twilio(phone, message)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"SMS failed: {result.get('error', 'Unknown error')}")
    return {"message": "SMS sent successfully", "sid": result.get("sid"), "status": result.get("status")}

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

@api_router.post("/email/send-documents-link")
async def send_documents_email(client_id: str, current_user: dict = Depends(get_current_user)):
    """Send Email with documents upload link - Alternative to SMS"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.get("email"):
        raise HTTPException(status_code=400, detail="El cliente no tiene email registrado")
    
    # Generate public link token (use client_id as record_id since we're sending from client info)
    token = await create_public_link(client_id, client_id, "documents")
    
    # Get base URL from environment or use default
    base_url = os.environ.get('FRONTEND_URL', os.environ.get('REACT_APP_BACKEND_URL', '').replace('/api', ''))
    if not base_url:
        base_url = 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev'
    document_link = f"{base_url}/c/docs/{token}"
    
    # Create email content
    client_name = f"{client['first_name']} {client['last_name']}"
    salesperson_name = current_user.get('name', current_user.get('email', 'Su vendedor'))
    
    email_body = f"""
<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
.container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
.header {{ background: #1e3a8a; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
.header img {{ max-width: 180px; height: auto; margin-bottom: 15px; }}
.content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
.button {{ display: inline-block; background: #dc2626; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 20px 0; }}
.button:hover {{ background: #b91c1c; }}
.documents-list {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
.doc-item {{ padding: 10px 0; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; }}
.doc-item:last-child {{ border-bottom: none; }}
.doc-icon {{ margin-right: 10px; }}
.footer {{ text-align: center; padding: 20px; color: #64748b; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}">
<h1 style="margin: 0;">📄 Suba sus Documentos</h1>
<p style="margin: 10px 0 0 0; color: #dc2626;">{COMPANY_TAGLINE}</p>
</div>
<div class="content">
<p>Hola <strong>{client_name}</strong>,</p>
<p>{salesperson_name} le solicita que suba los siguientes documentos para continuar con su proceso:</p>

<div class="documents-list">
<div class="doc-item">
<span class="doc-icon">🪪</span>
<div>
<strong>Identificación (ID)</strong><br>
<span style="color: #64748b; font-size: 14px;">Licencia de conducir, Pasaporte, o ID estatal</span>
</div>
</div>
<div class="doc-item">
<span class="doc-icon">💵</span>
<div>
<strong>Comprobante de Ingresos</strong><br>
<span style="color: #64748b; font-size: 14px;">Pay stub, declaración de impuestos, o carta de empleo</span>
</div>
</div>
<div class="doc-item">
<span class="doc-icon">🏠</span>
<div>
<strong>Comprobante de Residencia</strong><br>
<span style="color: #64748b; font-size: 14px;">Factura de servicios, estado de cuenta bancario</span>
</div>
</div>
</div>

<p style="text-align: center;">
<a href="{document_link}" class="button">Subir Documentos</a>
</p>

<p style="color: #64748b; font-size: 14px;">
<strong>Nota:</strong> Puede subir múltiples archivos por cada documento. Se combinarán automáticamente en un solo PDF.
</p>

<p style="color: #64748b; font-size: 13px;">
Si el botón no funciona, copie y pegue este enlace en su navegador:<br>
<a href="{document_link}" style="color: #1e3a8a; word-break: break-all;">{document_link}</a>
</p>
</div>
<div class="footer">
<p>Este mensaje fue enviado automáticamente por {COMPANY_NAME}.<br>
Sus documentos están protegidos y solo serán utilizados para su proceso.</p>
</div>
</div>
</body>
</html>
"""
    
    # Send email using SMTP
    smtp_email = os.environ.get('SMTP_USER') or os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        raise HTTPException(status_code=500, detail="Configuración de email no disponible. Contacte al administrador.")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📄 {client_name} - Por favor suba sus documentos"
        msg['From'] = smtp_email
        msg['To'] = client['email']
        
        html_part = MIMEText(email_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, client['email'], msg.as_string())
        
        # Log the email
        email_log = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "email": client['email'],
            "message_type": "documents",
            "link": document_link,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sent_by": current_user["id"]
        }
        await db.email_logs.insert_one(email_log)
        
        return {"message": "Email enviado exitosamente", "email": client['email'], "link": document_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")

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
    dealer_name = appointment.get("dealer", "")
    
    # Get dealer address if available
    dealer_location = dealer_name
    if dealer_name:
        dealer_doc = await db.config_lists.find_one(
            {"category": "dealer", "name": dealer_name},
            {"_id": 0, "address": 1}
        )
        if dealer_doc and dealer_doc.get("address"):
            dealer_location = dealer_doc["address"]
    
    if appointment.get("language") == "es":
        message = f"Hola {client_name}, tiene una cita para el {date_str} a las {time_str} en {dealer_location}. Para ver, reprogramar o cancelar: {appointment_link} - DealerCRM"
    else:
        message = f"Hi {client_name}, you have an appointment for {date_str} at {time_str} at {dealer_location}. To view, reschedule or cancel: {appointment_link} - DealerCRM"
    
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

@api_router.post("/email/send-appointment-link")
async def send_appointment_email(client_id: str, appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Send Email with appointment management link - Alternative to SMS"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.get("email"):
        raise HTTPException(status_code=400, detail="El cliente no tiene email registrado")
    
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Generate public link token
    token = await create_public_link(client_id, appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one({"id": appointment_id}, {"$set": {"public_token": token}})
    
    # Get base URL
    base_url = os.environ.get('FRONTEND_URL', 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev')
    appointment_link = f"{base_url}/c/appointment/{token}"
    
    # Build email content
    client_name = f"{client['first_name']} {client['last_name']}"
    salesperson_name = current_user.get('name', current_user.get('email', 'Su vendedor'))
    date_str = appointment.get("date", "Por confirmar")
    time_str = appointment.get("time", "")
    dealer_name = appointment.get("dealer", "")
    
    # Get dealer address if available (use full address instead of just name)
    dealer_str = dealer_name
    if dealer_name:
        dealer_doc = await db.config_lists.find_one(
            {"category": "dealer", "name": dealer_name},
            {"_id": 0, "address": 1}
        )
        if dealer_doc and dealer_doc.get("address"):
            dealer_str = dealer_doc["address"]
    
    email_body = f"""
<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
.container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
.header {{ background: #1e3a8a; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
.header img {{ max-width: 180px; height: auto; margin-bottom: 15px; }}
.content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
.appointment-box {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #1e3a8a; }}
.detail-row {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
.detail-row:last-child {{ border-bottom: none; }}
.label {{ color: #64748b; font-weight: 500; }}
.value {{ color: #1e293b; font-weight: bold; }}
.button {{ display: inline-block; background: #dc2626; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 10px 5px; }}
.button:hover {{ background: #b91c1c; }}
.button-secondary {{ background: #64748b; }}
.footer {{ text-align: center; padding: 20px; color: #64748b; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}">
<h1 style="margin: 0;">📅 Su Cita</h1>
<p style="margin: 10px 0 0 0; opacity: 0.9; color: #dc2626;">{COMPANY_TAGLINE}</p>
</div>
<div class="content">
<p>Hola <strong>{client_name}</strong>,</p>
<p>{salesperson_name} le ha enviado los detalles de su cita:</p>

<div class="appointment-box">
<div class="detail-row">
<span class="label">📅 Fecha:</span>
<span class="value">{date_str}</span>
</div>
<div class="detail-row">
<span class="label">🕐 Hora:</span>
<span class="value">{time_str}</span>
</div>
<div class="detail-row">
<span class="label">📍 Ubicación:</span>
<span class="value">{dealer_str}</span>
</div>
</div>

<p style="text-align: center;">
<a href="{appointment_link}" class="button">Ver Detalles de la Cita</a>
</p>

<p style="text-align: center; color: #64748b; font-size: 14px;">
Desde el link podrá ver los detalles, reprogramar o cancelar su cita.
</p>

<p style="color: #64748b; font-size: 13px;">
Si el botón no funciona, copie y pegue este enlace en su navegador:<br>
<a href="{appointment_link}" style="color: #1e3a8a; word-break: break-all;">{appointment_link}</a>
</p>
</div>
<div class="footer">
<p>Este mensaje fue enviado automáticamente por {COMPANY_NAME}.<br>
Si tiene preguntas, contacte a su vendedor.</p>
</div>
</div>
</body>
</html>
"""
    
    # Send email using SMTP
    smtp_email = os.environ.get('SMTP_USER') or os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        raise HTTPException(status_code=500, detail="Configuración de email no disponible. Contacte al administrador.")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📅 {client_name} - Detalles de su cita para {date_str}"
        msg['From'] = smtp_email
        msg['To'] = client['email']
        
        html_part = MIMEText(email_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, client['email'], msg.as_string())
        
        # Update appointment link_sent_at
        await db.appointments.update_one(
            {"id": appointment_id}, 
            {"$set": {
                "link_sent_at": datetime.now(timezone.utc).isoformat(),
                "last_email_sent": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Log the email
        email_log = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "appointment_id": appointment_id,
            "email": client['email'],
            "message_type": "appointment",
            "link": appointment_link,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sent_by": current_user["id"]
        }
        await db.email_logs.insert_one(email_log)
        
        return {"message": "Email de cita enviado exitosamente", "email": client['email'], "link": appointment_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")

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
    if record.get("finance_status") in ["financiado", "lease"]:
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
    # - Are NOT sold (finance_status != 'financiado' and != 'lease')
    # - Haven't received a reminder in the last week
    # - Are not deleted
    query = {
        "is_deleted": {"$ne": True},
        "finance_status": {"$nin": ["financiado", "lease"]},
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

# ==================== SMS INBOX & CONVERSATIONS ====================

def is_valid_email(email: str) -> bool:
    """Check if email is valid format"""
    if not email or '@' not in email:
        return False
    # Basic email validation - must have @ and a domain
    parts = email.split('@')
    if len(parts) != 2:
        return False
    local, domain = parts
    if not local or not domain:
        return False
    if '.' not in domain:
        return False
    # Exclude test/fake emails
    fake_domains = ['dealer.com', 'test.com', 'example.com', 'localhost']
    if any(domain.lower().endswith(fake) for fake in fake_domains):
        logger.warning(f"Skipping email to test/fake domain: {email}")
        return False
    return True

async def send_email_notification(to_email: str, subject: str, html_content: str) -> dict:
    """
    Send email notification using SMTP (FREE) or Resend (paid).
    Supports Gmail, Outlook, Yahoo, etc.
    """
    # Validate email before sending
    if not is_valid_email(to_email):
        logger.warning(f"Invalid email address, skipping: {to_email}")
        return {"success": False, "error": f"Invalid email: {to_email}"}
    
    # Try SMTP first (FREE)
    if SMTP_USER and SMTP_PASSWORD:
        try:
            def send_smtp_email():
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
                msg['To'] = to_email
                
                # Create HTML part
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
                # Connect and send
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_USER, to_email, msg.as_string())
                
                return True
            
            # Run in thread to not block async
            result = await asyncio.to_thread(send_smtp_email)
            logger.info(f"Email notification sent via SMTP to {to_email}")
            return {"success": True, "method": "smtp"}
            
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {str(e)}")
            # Fall through to try Resend if configured
    
    # Try Resend as fallback (paid)
    if RESEND_API_KEY:
        try:
            params = {
                "from": SENDER_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            email = await asyncio.to_thread(resend.Emails.send, params)
            logger.info(f"Email notification sent via Resend to {to_email}")
            return {"success": True, "email_id": email.get("id"), "method": "resend"}
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {str(e)}")
            return {"success": False, "error": str(e)}
    
    logger.warning("No email service configured - skipping email notification")
    return {"success": False, "error": "Email not configured"}

@api_router.get("/inbox/{client_id}")
async def get_client_inbox(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get all SMS messages for a client (conversation inbox)"""
    # Get client info
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all messages for this client (both sent and received)
    messages = await db.sms_conversations.find(
        {"client_id": client_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(500)
    
    # Also get SMS logs for historical messages
    sms_logs = await db.sms_logs.find(
        {"client_id": client_id},
        {"_id": 0}
    ).sort("sent_at", 1).to_list(500)
    
    # Merge logs into conversation format if not already in conversations
    existing_sids = {m.get("twilio_sid") for m in messages if m.get("twilio_sid")}
    for log in sms_logs:
        if log.get("twilio_sid") and log["twilio_sid"] not in existing_sids:
            messages.append({
                "id": log.get("id", str(uuid.uuid4())),
                "client_id": client_id,
                "direction": "outbound",
                "message": log.get("message", ""),
                "timestamp": log.get("sent_at"),
                "sender_id": log.get("sent_by"),
                "sender_name": log.get("sender_name", "System"),
                "twilio_sid": log.get("twilio_sid"),
                "status": log.get("status", "sent")
            })
    
    # Sort by timestamp
    messages.sort(key=lambda x: x.get("timestamp", ""))
    
    # Get unread count
    unread_count = await db.sms_conversations.count_documents({
        "client_id": client_id,
        "direction": "inbound",
        "read": False
    })
    
    return {
        "client": client,
        "messages": messages,
        "unread_count": unread_count
    }

@api_router.post("/inbox/{client_id}/send")
async def send_inbox_message(client_id: str, message: str = Form(...), current_user: dict = Depends(get_current_user)):
    """Send a message from the inbox to a client"""
    # Get client info
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.get("phone"):
        raise HTTPException(status_code=400, detail="Client has no phone number")
    
    # Send SMS
    result = await send_sms_twilio(client["phone"], message)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Store in conversations
    conversation_msg = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "direction": "outbound",
        "message": message,
        "timestamp": now,
        "sender_id": current_user["id"],
        "sender_name": current_user.get("name", current_user.get("email", "Unknown")),
        "twilio_sid": result.get("sid"),
        "status": "sent" if result["success"] else "failed",
        "read": True
    }
    await db.sms_conversations.insert_one(conversation_msg)
    
    # Update client's last activity
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {"last_sms_activity": now, "last_active_user_id": current_user["id"]}}
    )
    
    if result["success"]:
        return {"message": "SMS sent successfully", "conversation": {**conversation_msg, "_id": None}}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")

@api_router.post("/inbox/{client_id}/mark-read")
async def mark_messages_read(client_id: str, current_user: dict = Depends(get_current_user)):
    """Mark all inbound messages for a client as read"""
    result = await db.sms_conversations.update_many(
        {"client_id": client_id, "direction": "inbound", "read": False},
        {"$set": {"read": True, "read_by": current_user["id"], "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Marked {result.modified_count} messages as read"}

@api_router.get("/inbox/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread messages count for notification badge"""
    count = await db.sms_conversations.count_documents({
        "direction": "inbound",
        "read": False
    })
    return {"unread_count": count}

@api_router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user), limit: int = 20):
    """Get in-app notifications for the current user"""
    notifications = await db.notifications.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    
    return {"notifications": notifications, "unread_count": unread_count}

@api_router.post("/notifications/mark-read")
async def mark_notifications_read(notification_ids: List[str] = None, current_user: dict = Depends(get_current_user)):
    """Mark notifications as read"""
    query = {"user_id": current_user["id"]}
    if notification_ids:
        query["id"] = {"$in": notification_ids}
    
    result = await db.notifications.update_many(
        query,
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

# ==================== TWILIO WEBHOOK (Receive SMS) ====================

@app.post("/webhook/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """
    Webhook endpoint to receive incoming SMS messages from Twilio.
    Configure this URL in your Twilio console: https://your-domain.com/webhook/twilio/sms
    """
    try:
        form_data = await request.form()
        
        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        
        logger.info(f"Received SMS from {from_number}: {body[:50]}...")
        
        now = datetime.now(timezone.utc)
        
        # Find client by phone number
        # Normalize phone number for matching
        normalized_phone = re.sub(r'[^\d+]', '', from_number)
        client = await db.clients.find_one({
            "$or": [
                {"phone": from_number},
                {"phone": normalized_phone},
                {"phone": {"$regex": normalized_phone[-10:] + "$"}}
            ]
        }, {"_id": 0})
        
        if not client:
            # Try imported contacts
            contact = await db.imported_contacts.find_one({
                "$or": [
                    {"phone_formatted": from_number},
                    {"phone_formatted": normalized_phone}
                ]
            }, {"_id": 0})
            
            if contact:
                client = {
                    "id": contact["id"],
                    "first_name": contact.get("first_name", ""),
                    "last_name": contact.get("last_name", ""),
                    "phone": contact.get("phone_formatted", from_number),
                    "is_imported_contact": True
                }
        
        if client:
            # Store the message
            conversation_msg = {
                "id": str(uuid.uuid4()),
                "client_id": client["id"],
                "direction": "inbound",
                "message": body,
                "timestamp": now.isoformat(),
                "from_phone": from_number,
                "twilio_sid": message_sid,
                "status": "received",
                "read": False
            }
            await db.sms_conversations.insert_one(conversation_msg)
            
            # Update client's last activity
            await db.clients.update_one(
                {"id": client["id"]},
                {"$set": {
                    "last_sms_activity": now.isoformat(),
                    "last_client_response": now.isoformat()
                }}
            )
            
            # Find assigned salesperson(s) - get the most recent record's salesperson
            recent_record = await db.user_records.find_one(
                {"client_id": client["id"]},
                {"_id": 0}
            )
            
            salespeople_to_notify = set()
            
            if recent_record and recent_record.get("salesperson_id"):
                salespeople_to_notify.add(recent_record["salesperson_id"])
            
            # Also check if there's a collaboration
            if client.get("collaboration_users"):
                salespeople_to_notify.update(client["collaboration_users"])
            
            # Also check last_active_user_id
            if client.get("last_active_user_id"):
                salespeople_to_notify.add(client["last_active_user_id"])
            
            # Create notifications for each salesperson
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip() or "Unknown Client"
            
            for user_id in salespeople_to_notify:
                user = await db.users.find_one({"id": user_id}, {"_id": 0})
                if not user:
                    continue
                
                # Create in-app notification
                notification = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "type": "sms_received",
                    "title": f"Nuevo SMS de {client_name}",
                    "message": body[:100] + ("..." if len(body) > 100 else ""),
                    "client_id": client["id"],
                    "client_name": client_name,
                    "read": False,
                    "created_at": now.isoformat()
                }
                await db.notifications.insert_one(notification)
                
                # Send email notification if user has email
                if user.get("email"):
                    email_html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #3b82f6;">📱 Nuevo mensaje SMS</h2>
                        <p><strong>Cliente:</strong> {client_name}</p>
                        <p><strong>Teléfono:</strong> {from_number}</p>
                        <div style="background-color: #f1f5f9; padding: 15px; border-radius: 8px; margin: 15px 0;">
                            <p style="margin: 0; color: #334155;">{body}</p>
                        </div>
                        <p style="color: #64748b; font-size: 12px;">
                            Responde desde el CRM para mantener el historial de conversación.
                        </p>
                    </div>
                    """
                    # Send email in background (don't wait)
                    asyncio.create_task(send_email_notification(
                        user["email"],
                        f"Nuevo SMS de {client_name}",
                        email_html
                    ))
            
            logger.info(f"Processed incoming SMS from {from_number} for client {client['id']}")
        else:
            # Unknown sender - log it anyway
            unknown_msg = {
                "id": str(uuid.uuid4()),
                "client_id": None,
                "direction": "inbound",
                "message": body,
                "timestamp": now.isoformat(),
                "from_phone": from_number,
                "twilio_sid": message_sid,
                "status": "received_unknown",
                "read": False
            }
            await db.sms_conversations.insert_one(unknown_msg)
            logger.warning(f"Received SMS from unknown number: {from_number}")
        
        # Return TwiML response (empty response = don't auto-reply)
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {str(e)}")
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

# ==================== CLIENT COLLABORATION ====================

@api_router.post("/clients/{client_id}/request-collaboration")
async def request_collaboration(client_id: str, current_user: dict = Depends(get_current_user)):
    """Request to collaborate on a client with the original salesperson"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Find the original salesperson
    original_user_id = client.get("last_active_user_id") or client.get("created_by")
    
    if original_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You are already the primary salesperson for this client")
    
    original_user = await db.users.find_one({"id": original_user_id}, {"_id": 0})
    if not original_user:
        raise HTTPException(status_code=404, detail="Original salesperson not found")
    
    now = datetime.now(timezone.utc).isoformat()
    client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
    
    # Create collaboration request
    collab_request = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "client_name": client_name,
        "requester_id": current_user["id"],
        "requester_name": current_user.get("name", current_user.get("email")),
        "original_user_id": original_user_id,
        "original_user_name": original_user.get("name", original_user.get("email")),
        "status": "pending",
        "created_at": now
    }
    await db.collaboration_requests.insert_one(collab_request)
    
    # Notify the original salesperson
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": original_user_id,
        "type": "collaboration_request",
        "title": f"Solicitud de colaboración",
        "message": f"{current_user.get('name', 'Un vendedor')} quiere trabajar juntos el cliente {client_name}",
        "client_id": client_id,
        "client_name": client_name,
        "request_id": collab_request["id"],
        "read": False,
        "created_at": now
    }
    await db.notifications.insert_one(notification)
    
    # Send email notification
    if original_user.get("email"):
        email_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #3b82f6;">🤝 Solicitud de Colaboración</h2>
            <p><strong>{current_user.get('name', 'Un vendedor')}</strong> quiere trabajar contigo el cliente:</p>
            <div style="background-color: #f1f5f9; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 0; font-size: 18px; color: #334155;"><strong>{client_name}</strong></p>
                <p style="margin: 5px 0 0 0; color: #64748b;">{client.get('phone', '')}</p>
            </div>
            <p>Ingresa al CRM para aceptar o rechazar esta solicitud.</p>
        </div>
        """
        asyncio.create_task(send_email_notification(
            original_user["email"],
            f"Solicitud de colaboración - {client_name}",
            email_html
        ))
    
    return {"message": "Collaboration request sent", "request_id": collab_request["id"]}

@api_router.get("/collaboration-requests")
async def get_collaboration_requests(current_user: dict = Depends(get_current_user)):
    """Get pending collaboration requests for the current user"""
    requests = await db.collaboration_requests.find({
        "original_user_id": current_user["id"],
        "status": "pending"
    }, {"_id": 0}).to_list(100)
    return requests

@api_router.post("/collaboration-requests/{request_id}/respond")
async def respond_to_collaboration(request_id: str, accept: bool, current_user: dict = Depends(get_current_user)):
    """Accept or reject a collaboration request"""
    collab_request = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not collab_request:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    
    if collab_request["original_user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You are not authorized to respond to this request")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if accept:
        # Add requester to client's collaboration list
        await db.clients.update_one(
            {"id": collab_request["client_id"]},
            {"$addToSet": {"collaboration_users": collab_request["requester_id"]}}
        )
        
        # Update request status
        await db.collaboration_requests.update_one(
            {"id": request_id},
            {"$set": {"status": "accepted", "responded_at": now}}
        )
        
        # Notify requester
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": collab_request["requester_id"],
            "type": "collaboration_accepted",
            "title": "Colaboración aceptada",
            "message": f"{current_user.get('name', 'El vendedor')} aceptó trabajar juntos el cliente {collab_request['client_name']}",
            "client_id": collab_request["client_id"],
            "read": False,
            "created_at": now
        }
        await db.notifications.insert_one(notification)
        
        return {"message": "Collaboration accepted", "client_id": collab_request["client_id"]}
    else:
        # Reject request
        await db.collaboration_requests.update_one(
            {"id": request_id},
            {"$set": {"status": "rejected", "responded_at": now}}
        )
        
        # Notify requester
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": collab_request["requester_id"],
            "type": "collaboration_rejected",
            "title": "Colaboración rechazada",
            "message": f"{current_user.get('name', 'El vendedor')} rechazó la solicitud de colaboración para {collab_request['client_name']}",
            "client_id": collab_request["client_id"],
            "read": False,
            "created_at": now
        }
        await db.notifications.insert_one(notification)
        
        return {"message": "Collaboration rejected"}

# ==================== IMPORT WITH DUPLICATE DETECTION ====================

@api_router.post("/import-contacts/check-duplicates")
async def check_import_duplicates(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Check for duplicate contacts before importing.
    Returns list of duplicates with their status (72h rule, active, etc.)
    """
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Find phone column
        phone_col = None
        for col in df.columns:
            if 'phone' in col or 'telefono' in col or 'tel' in col:
                phone_col = col
                break
        
        if not phone_col:
            raise HTTPException(status_code=400, detail="No phone column found in file")
        
        now = datetime.now(timezone.utc)
        seventy_two_hours_ago = (now - timedelta(hours=72)).isoformat()
        
        results = []
        
        for _, row in df.iterrows():
            phone_raw = str(row.get(phone_col, ''))
            phone_clean = re.sub(r'[^\d]', '', phone_raw)
            
            if len(phone_clean) < 10:
                continue
            
            # Check if client exists
            existing_client = await db.clients.find_one({
                "$or": [
                    {"phone": {"$regex": phone_clean[-10:] + "$"}},
                    {"phone": phone_raw}
                ]
            }, {"_id": 0})
            
            if existing_client:
                # Get last activity info
                last_activity = existing_client.get("last_sms_activity") or existing_client.get("last_client_response")
                last_active_user_id = existing_client.get("last_active_user_id") or existing_client.get("created_by")
                
                # Get salesperson info
                salesperson = None
                if last_active_user_id:
                    salesperson = await db.users.find_one({"id": last_active_user_id}, {"_id": 0, "password": 0})
                
                # Determine status
                is_own_client = last_active_user_id == current_user["id"]
                is_inactive_72h = not last_activity or last_activity < seventy_two_hours_ago
                
                status = "own" if is_own_client else ("available" if is_inactive_72h else "active")
                
                results.append({
                    "phone": phone_raw,
                    "phone_clean": phone_clean,
                    "first_name": row.get('first_name') or row.get('nombre') or row.get('first name') or '',
                    "last_name": row.get('last_name') or row.get('apellido') or row.get('last name') or '',
                    "existing_client": {
                        "id": existing_client["id"],
                        "first_name": existing_client.get("first_name", ""),
                        "last_name": existing_client.get("last_name", ""),
                        "phone": existing_client.get("phone", ""),
                        "last_activity": last_activity,
                        "salesperson": {
                            "id": salesperson["id"] if salesperson else None,
                            "name": salesperson.get("name", salesperson.get("email")) if salesperson else "Unknown"
                        } if salesperson else None
                    },
                    "status": status,
                    "can_take_over": is_inactive_72h and not is_own_client,
                    "is_own_client": is_own_client,
                    "can_request_collaboration": not is_inactive_72h and not is_own_client
                })
            else:
                results.append({
                    "phone": phone_raw,
                    "phone_clean": phone_clean,
                    "first_name": row.get('first_name') or row.get('nombre') or row.get('first name') or '',
                    "last_name": row.get('last_name') or row.get('apellido') or row.get('last name') or '',
                    "existing_client": None,
                    "status": "new",
                    "can_take_over": True,
                    "is_own_client": False,
                    "can_request_collaboration": False
                })
        
        return {
            "total_rows": len(results),
            "new_contacts": len([r for r in results if r["status"] == "new"]),
            "duplicates": len([r for r in results if r["status"] != "new"]),
            "available_to_take": len([r for r in results if r["can_take_over"] and r["status"] != "new"]),
            "active_with_others": len([r for r in results if r["can_request_collaboration"]]),
            "contacts": results
        }
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/import-contacts/take-over/{client_id}")
async def take_over_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Take over an inactive client (72h+ without activity)"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    now = datetime.now(timezone.utc)
    seventy_two_hours_ago = (now - timedelta(hours=72)).isoformat()
    
    last_activity = client.get("last_sms_activity") or client.get("last_client_response")
    
    if last_activity and last_activity >= seventy_two_hours_ago:
        raise HTTPException(
            status_code=400, 
            detail="Client has been active in the last 72 hours. Request collaboration instead."
        )
    
    # Update client ownership
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {
            "last_active_user_id": current_user["id"],
            "taken_over_at": now.isoformat(),
            "taken_over_by": current_user["id"]
        }}
    )
    
    return {"message": "Client taken over successfully", "client_id": client_id}

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
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    # Check expiration
    if datetime.fromisoformat(link["expires_at"].replace('Z', '+00:00')) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This link has expired")
    
    client = await db.clients.find_one({"id": link["client_id"]}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if documents already submitted and get language preference
    record = await db.user_records.find_one({"id": link["record_id"]}, {"_id": 0})
    documents_submitted = record.get("documents_submitted", False) if record else False
    preferred_language = link.get("preferred_language") or (record.get("preferred_language") if record else None)
    
    # Check if client already has an ID document from pre-qualify
    has_existing_id_document = client.get("id_uploaded", False)
    existing_id_file_url = client.get("id_file_url") if has_existing_id_document else None
    
    return {
        "first_name": client["first_name"],
        "last_name": client["last_name"],
        "documents_submitted": documents_submitted,
        "preferred_language": preferred_language,
        "has_existing_id_document": has_existing_id_document,
        "existing_id_message": "Ya tiene un documento de ID previamente subido. Puede subir uno nuevo si lo desea." if has_existing_id_document else None
    }

class DocumentLanguageRequest(BaseModel):
    language: str  # 'en' or 'es'

@api_router.put("/public/documents/{token}/language")
async def update_document_language_preference(token: str, data: DocumentLanguageRequest):
    """Update client's language preference for documents (public, no auth)"""
    if data.language not in ['en', 'es']:
        raise HTTPException(status_code=400, detail="Invalid language. Must be 'en' or 'es'")
    
    link = await db.public_links.find_one({"token": token, "link_type": "documents"}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Update record with language preference
    await db.user_records.update_one(
        {"id": link["record_id"]},
        {"$set": {"preferred_language": data.language}}
    )
    
    # Also update the link itself
    await db.public_links.update_one({"token": token}, {"$set": {"preferred_language": data.language}})
    
    return {"message": f"Language preference updated to {data.language}"}

@api_router.post("/public/documents/{token}/upload")
async def upload_public_documents(
    token: str,
    id_documents: List[UploadFile] = File(default=[]),
    income_documents: List[UploadFile] = File(default=[]),
    residence_documents: List[UploadFile] = File(default=[]),
    language: str = Form(default="en")
):
    """Handle document upload from client (public, no auth) - supports multiple files per type"""
    from PIL import Image as PILImage
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io
    
    link = await db.public_links.find_one({"token": token, "link_type": "documents"}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    client_id = link.get("client_id")
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Create uploads directory
    upload_dir = Path(__file__).parent / "uploads" / "clients" / client_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def combine_files_to_pdf(files: List[UploadFile], output_name: str) -> str:
        """Combine multiple files (images/PDFs) into a single PDF"""
        if not files:
            return None
        
        pdf_writer = PdfWriter()
        
        for file in files:
            content = await file.read()
            await file.seek(0)  # Reset for potential reuse
            
            if file.content_type == 'application/pdf':
                # Add PDF pages directly
                try:
                    pdf_reader = PdfReader(io.BytesIO(content))
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                except Exception as e:
                    print(f"Error reading PDF {file.filename}: {e}")
            elif file.content_type.startswith('image/'):
                # Convert image to PDF page
                try:
                    img = PILImage.open(io.BytesIO(content))
                    
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = PILImage.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Create PDF from image
                    img_buffer = io.BytesIO()
                    
                    # Calculate size to fit on letter page with margins
                    page_width, page_height = letter
                    margin = 36  # 0.5 inch margin
                    max_width = page_width - 2 * margin
                    max_height = page_height - 2 * margin
                    
                    # Scale image to fit
                    img_width, img_height = img.size
                    scale = min(max_width / img_width, max_height / img_height, 1.0)
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    if scale < 1.0:
                        img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    
                    # Save as temporary PDF
                    img_pdf_buffer = io.BytesIO()
                    c = canvas.Canvas(img_pdf_buffer, pagesize=letter)
                    
                    # Center on page
                    x = (page_width - img.width) / 2
                    y = (page_height - img.height) / 2
                    
                    # Save image to buffer
                    img.save(img_buffer, format='JPEG', quality=85)
                    img_buffer.seek(0)
                    
                    # Draw image on PDF
                    from reportlab.lib.utils import ImageReader
                    c.drawImage(ImageReader(img_buffer), x, y, width=img.width, height=img.height)
                    c.save()
                    
                    img_pdf_buffer.seek(0)
                    img_reader = PdfReader(img_pdf_buffer)
                    for page in img_reader.pages:
                        pdf_writer.add_page(page)
                except Exception as e:
                    print(f"Error processing image {file.filename}: {e}")
        
        if len(pdf_writer.pages) == 0:
            return None
        
        # Save combined PDF
        output_path = upload_dir / f"{output_name}.pdf"
        with open(output_path, 'wb') as f:
            pdf_writer.write(f)
        
        return str(output_path)
    
    update_data = {
        "documents_submitted": True,
        "documents_submitted_at": datetime.now(timezone.utc).isoformat(),
        "preferred_language": language
    }
    
    # Process ID documents
    if id_documents and len(id_documents) > 0 and id_documents[0].filename:
        id_path = await combine_files_to_pdf(id_documents, "id_document")
        if id_path:
            update_data["id_uploaded"] = True
            update_data["id_file_url"] = id_path
    
    # Process Income documents
    if income_documents and len(income_documents) > 0 and income_documents[0].filename:
        income_path = await combine_files_to_pdf(income_documents, "income_proof")
        if income_path:
            update_data["income_proof_uploaded"] = True
            update_data["income_proof_file_url"] = income_path
    
    # Process Residence documents
    if residence_documents and len(residence_documents) > 0 and residence_documents[0].filename:
        residence_path = await combine_files_to_pdf(residence_documents, "residence_proof")
        if residence_path:
            update_data["residence_proof_uploaded"] = True
            update_data["residence_proof_file_url"] = residence_path
    
    # Update client with document info
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Also update record if exists
    if link.get("record_id"):
        await db.user_records.update_one(
            {"id": link["record_id"]},
            {"$set": {
                "documents_submitted": True,
                "documents_submitted_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Mark link as used
    await db.public_links.update_one({"token": token}, {"$set": {"used": True}})
    
    return {"message": "Documents received successfully"}

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
    
    # Get full dealer address for current appointment
    dealer_name = appointment.get("dealer", "")
    dealer_address = dealer_name  # Default to name if no address found
    if dealer_name:
        dealer_doc = await db.config_lists.find_one(
            {"category": "dealer", "name": dealer_name},
            {"_id": 0, "address": 1}
        )
        if dealer_doc and dealer_doc.get("address"):
            dealer_address = dealer_doc["address"]
    
    # Add dealer_address to appointment for display
    appointment_with_address = {**appointment, "dealer_address": dealer_address}
    
    return {
        "appointment": appointment_with_address,
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

class LanguagePreferenceRequest(BaseModel):
    language: str  # 'en' or 'es'

@api_router.put("/public/appointment/{token}/language")
async def update_language_preference(token: str, data: LanguagePreferenceRequest):
    """Update client's language preference for the appointment (public, no auth)"""
    if data.language not in ['en', 'es']:
        raise HTTPException(status_code=400, detail="Invalid language. Must be 'en' or 'es'")
    
    link = await db.public_links.find_one({"token": token, "link_type": "appointment"}, {"_id": 0})
    appointment_id = link["record_id"] if link else None
    
    if not appointment_id:
        appointment = await db.appointments.find_one({"public_token": token}, {"_id": 0})
        if appointment:
            appointment_id = appointment["id"]
    
    if not appointment_id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update appointment with language preference
    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"preferred_language": data.language, "language_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"Language preference updated to {data.language}"}

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

# ==================== SMS TEMPLATES ====================

class SMSTemplateUpdate(BaseModel):
    template_key: str
    message_en: str
    message_es: str

@api_router.get("/sms-templates")
async def get_sms_templates(current_user: dict = Depends(get_current_user)):
    """Get all SMS templates"""
    templates = await db.sms_templates.find({}, {"_id": 0}).to_list(100)
    
    # If no templates exist, create defaults
    if not templates:
        await initialize_default_sms_templates()
        templates = await db.sms_templates.find({}, {"_id": 0}).to_list(100)
    
    return templates

@api_router.put("/sms-templates/{template_key}")
async def update_sms_template(template_key: str, data: SMSTemplateUpdate, current_user: dict = Depends(get_current_user)):
    """Update an SMS template (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.sms_templates.update_one(
        {"template_key": template_key},
        {"$set": {
            "message_en": data.message_en,
            "message_es": data.message_es,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user["id"]
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template updated successfully"}

async def initialize_default_sms_templates():
    """Initialize default SMS templates"""
    templates = [
        {
            "id": str(uuid.uuid4()),
            "template_key": "marketing_initial",
            "name": "Marketing - Initial Contact",
            "description": "First SMS sent to imported contacts",
            "message_en": "Hi {first_name}! Are you interested in a car? We can help you with everything - financing, trade-ins, and more. Schedule your appointment here: {link} - DealerCRM",
            "message_es": "¡Hola {first_name}! ¿Te interesa un auto? Te ayudamos con todo - financiamiento, trade-ins y más. Agenda tu cita aquí: {link} - DealerCRM",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "template_key": "marketing_reminder",
            "name": "Marketing - Weekly Reminder",
            "description": "Weekly reminder for contacts who haven't scheduled",
            "message_en": "Hi {first_name}! Don't miss out on your dream car. We're here to help. Schedule your appointment: {link} - DealerCRM",
            "message_es": "¡Hola {first_name}! No te pierdas el auto de tus sueños. Estamos para ayudarte. Agenda tu cita: {link} - DealerCRM",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "template_key": "appointment_notification",
            "name": "Appointment Notification",
            "description": "Sent when salesperson creates appointment for client",
            "message_en": "Hi {first_name}! Your appointment has been scheduled for {date} at {time} at {dealer}. Manage your appointment here: {link} - DealerCRM",
            "message_es": "¡Hola {first_name}! Tu cita ha sido programada para el {date} a las {time} en {dealer}. Gestiona tu cita aquí: {link} - DealerCRM",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "template_key": "welcome_first_record",
            "name": "Welcome - First Record",
            "description": "Sent when first record is created for a client",
            "message_en": "Hi {first_name}! Thanks for visiting us. We'll keep you informed about your purchase process. Questions? Contact us anytime. - DealerCRM",
            "message_es": "¡Hola {first_name}! Gracias por visitarnos. Te mantendremos informado sobre tu proceso de compra. ¿Preguntas? Contáctanos. - DealerCRM",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.sms_templates.insert_many(templates)
    logger.info("Initialized default SMS templates")

async def get_sms_template(template_key: str, language: str = "en") -> str:
    """Get SMS template message by key and language"""
    template = await db.sms_templates.find_one({"template_key": template_key}, {"_id": 0})
    if not template:
        return ""
    return template.get(f"message_{language}", template.get("message_en", ""))

# ==================== CONTACT IMPORT (Leads/Prospects) ====================

def extract_phone_last_10(phone_str: str) -> str:
    """Extract last 10 digits from phone number (assuming US numbers)"""
    if not phone_str:
        return ""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone_str))
    # Get last 10 digits
    if len(digits) >= 10:
        return digits[-10:]
    return digits

class ImportedContact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    first_name: str
    last_name: str
    phone: str
    imported_by: str
    imported_at: str
    sms_sent: bool = False
    sms_count: int = 0
    last_sms_sent: Optional[str] = None
    appointment_created: bool = False
    appointment_id: Optional[str] = None
    opt_out: bool = False  # If true, no automatic SMS

@api_router.post("/import-contacts")
async def import_contacts(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import contacts from Excel or CSV file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload CSV or Excel file (.csv, .xlsx, .xls)")
    
    try:
        contents = await file.read()
        
        # Read file based on type
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Normalize column names (lowercase, strip spaces)
        df.columns = df.columns.str.lower().str.strip()
        
        # Map possible column names
        name_columns = ['first_name', 'firstname', 'first name', 'nombre', 'name']
        lastname_columns = ['last_name', 'lastname', 'last name', 'apellido', 'surname']
        phone_columns = ['phone', 'phone_number', 'phonenumber', 'telefono', 'teléfono', 'tel', 'mobile', 'cell']
        
        # Find matching columns
        first_name_col = next((col for col in df.columns if col in name_columns), None)
        last_name_col = next((col for col in df.columns if col in lastname_columns), None)
        phone_col = next((col for col in df.columns if col in phone_columns), None)
        
        if not phone_col:
            raise HTTPException(status_code=400, detail="Phone column not found. Please ensure your file has a column named 'Phone', 'Telefono', or similar.")
        
        now = datetime.now(timezone.utc).isoformat()
        imported_count = 0
        skipped_count = 0
        contacts_to_insert = []
        
        for _, row in df.iterrows():
            phone = extract_phone_last_10(str(row.get(phone_col, '')))
            
            if not phone or len(phone) < 10:
                skipped_count += 1
                continue
            
            # Check if phone already exists
            existing = await db.imported_contacts.find_one({"phone": phone})
            if existing:
                skipped_count += 1
                continue
            
            first_name = str(row.get(first_name_col, '')).strip() if first_name_col else ''
            last_name = str(row.get(last_name_col, '')).strip() if last_name_col else ''
            
            # Clean up names
            if first_name.lower() == 'nan' or not first_name:
                first_name = 'Customer'
            if last_name.lower() == 'nan':
                last_name = ''
            
            contact = {
                "id": str(uuid.uuid4()),
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "phone_formatted": f"+1{phone}",
                "imported_by": current_user["id"],
                "imported_by_name": current_user["name"],
                "imported_at": now,
                "sms_sent": False,
                "sms_count": 0,
                "last_sms_sent": None,
                "next_sms_scheduled": None,
                "appointment_created": False,
                "appointment_id": None,
                "opt_out": False,
                "status": "pending"  # pending, contacted, scheduled, converted
            }
            contacts_to_insert.append(contact)
            imported_count += 1
        
        if contacts_to_insert:
            await db.imported_contacts.insert_many(contacts_to_insert)
        
        return {
            "message": f"Import completed. {imported_count} contacts imported, {skipped_count} skipped.",
            "imported": imported_count,
            "skipped": skipped_count
        }
        
    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/imported-contacts")
async def get_imported_contacts(
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get imported contacts"""
    query = {}
    
    # Non-admin users only see their own imports
    if current_user["role"] != "admin":
        query["imported_by"] = current_user["id"]
    
    if status:
        query["status"] = status
    
    contacts = await db.imported_contacts.find(query, {"_id": 0}).sort("imported_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.imported_contacts.count_documents(query)
    
    return {"contacts": contacts, "total": total}

@api_router.post("/imported-contacts/{contact_id}/send-sms-now")
async def send_marketing_sms_now(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Send marketing SMS immediately to an imported contact"""
    contact = await db.imported_contacts.find_one({"id": contact_id}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if contact.get("opt_out"):
        raise HTTPException(status_code=400, detail="Contact has opted out of SMS")
    
    if contact.get("appointment_created"):
        raise HTTPException(status_code=400, detail="Contact already has an appointment")
    
    # Get marketing template
    template_msg = await get_sms_template("marketing_initial", "en")
    
    # Generate appointment link for this contact
    # First create a temporary public link
    token = await create_public_link(contact_id, contact_id, "marketing_appointment")
    base_url = os.environ.get('FRONTEND_URL', 'https://work-1-hxroqbnbaygfdbdd.prod-runtime.all-hands.dev')
    appointment_link = f"{base_url}/c/schedule/{token}"
    
    # Format message
    message = template_msg.format(
        first_name=contact.get("first_name", ""),
        link=appointment_link
    )
    
    # Send SMS
    result = await send_sms_twilio(contact["phone_formatted"], message)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update contact
    await db.imported_contacts.update_one(
        {"id": contact_id},
        {"$set": {
            "sms_sent": True,
            "sms_count": contact.get("sms_count", 0) + 1,
            "last_sms_sent": now,
            "status": "contacted",
            "next_sms_scheduled": None  # Clear scheduled since we sent now
        }}
    )
    
    # Log SMS
    sms_log = {
        "id": str(uuid.uuid4()),
        "contact_id": contact_id,
        "phone": contact["phone_formatted"],
        "message_type": "marketing",
        "message": message,
        "status": "sent" if result["success"] else "failed",
        "twilio_sid": result.get("sid"),
        "error": result.get("error"),
        "sent_at": now,
        "sent_by": current_user["id"]
    }
    await db.sms_logs.insert_one(sms_log)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")
    
    return {"message": "SMS sent successfully", "twilio_sid": result.get("sid")}

@api_router.put("/imported-contacts/{contact_id}/opt-out")
async def toggle_contact_opt_out(contact_id: str, opt_out: bool, current_user: dict = Depends(get_current_user)):
    """Toggle opt-out status for a contact (disable/enable automatic SMS)"""
    result = await db.imported_contacts.update_one(
        {"id": contact_id},
        {"$set": {"opt_out": opt_out, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"message": f"Contact {'opted out' if opt_out else 'opted in'} successfully"}

@api_router.delete("/imported-contacts/{contact_id}")
async def delete_imported_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an imported contact"""
    contact = await db.imported_contacts.find_one({"id": contact_id}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Only owner or admin can delete
    if current_user["role"] != "admin" and contact.get("imported_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contact")
    
    await db.imported_contacts.delete_one({"id": contact_id})
    return {"message": "Contact deleted"}

# Also add opt_out field to clients
@api_router.put("/clients/{client_id}/opt-out")
async def toggle_client_opt_out(client_id: str, opt_out: bool, current_user: dict = Depends(get_current_user)):
    """Toggle opt-out status for a client (disable/enable automatic appointment SMS)"""
    result = await db.clients.update_one(
        {"id": client_id},
        {"$set": {"opt_out_sms": opt_out, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {"message": f"Client SMS {'disabled' if opt_out else 'enabled'} successfully"}

# ==================== CONFIGURABLE LISTS (Banks, Dealers, Cars) ====================

class ConfigListItem(BaseModel):
    name: str
    category: str  # 'bank', 'dealer', 'car'
    address: Optional[str] = None  # Only for dealers

class ConfigListItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: Optional[str] = None  # For banks, dealers, cars
    value: Optional[str] = None  # For id_type, poi_type, por_type
    category: str
    address: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None

@api_router.get("/config-lists/{category}", response_model=List[ConfigListItemResponse])
async def get_config_list(category: str, current_user: dict = Depends(get_current_user)):
    """Get all items in a configurable list"""
    valid_categories = ['bank', 'dealer', 'car', 'id_type', 'poi_type', 'por_type']
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    
    items = await db.config_lists.find({"category": category}, {"_id": 0}).to_list(1000)
    
    # Normalize items - ensure 'name' field exists for frontend compatibility
    normalized_items = []
    for item in items:
        if 'value' in item and 'name' not in item:
            item['name'] = item['value']
        normalized_items.append(item)
    
    # Sort by name/value
    normalized_items.sort(key=lambda x: x.get('name') or x.get('value') or '')
    
    return normalized_items

@api_router.post("/config-lists", response_model=ConfigListItemResponse)
async def create_config_list_item(item: ConfigListItem, current_user: dict = Depends(get_current_user)):
    """Add a new item to a configurable list (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_categories = ['bank', 'dealer', 'car', 'id_type', 'poi_type', 'por_type']
    if item.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    
    # Check for duplicate
    existing = await db.config_lists.find_one({"name": {"$regex": f"^{item.name}$", "$options": "i"}, "category": item.category})
    if existing:
        raise HTTPException(status_code=400, detail=f"{item.name} already exists in {item.category} list")
    
    item_doc = {
        "id": str(uuid.uuid4()),
        "name": item.name,
        "category": item.category,
        "address": item.address if item.category == "dealer" else None,
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

@api_router.put("/config-lists/{item_id}")
async def update_config_list_item(item_id: str, item: ConfigListItem, current_user: dict = Depends(get_current_user)):
    """Update an item in a configurable list (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {"name": item.name}
    if item.category == "dealer" and item.address:
        update_data["address"] = item.address
    
    result = await db.config_lists.update_one(
        {"id": item_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    updated = await db.config_lists.find_one({"id": item_id}, {"_id": 0})
    return updated

# ==================== FORCE INITIALIZE CONFIG LISTS (Admin) ====================

@api_router.post("/admin/init-config-lists")
async def force_init_config_lists(current_user: dict = Depends(get_current_user)):
    """Force initialize default config lists - Admin only"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await initialize_default_config_lists()
    
    # Return counts
    counts = {}
    for category in ['bank', 'dealer', 'car', 'id_type', 'poi_type', 'por_type']:
        counts[category] = await db.config_lists.count_documents({"category": category})
    
    return {"message": "Config lists initialized", "counts": counts}

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

# ==================== CLIENT ACCESS REQUESTS ====================

@api_router.post("/client-requests")
async def create_client_request(client_id: str, current_user: dict = Depends(get_current_user)):
    """Create a request to access another user's client"""
    # Get the client
    client = await db.clients.find_one({"id": client_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if user already owns this client
    if client.get("created_by") == current_user["id"]:
        raise HTTPException(status_code=400, detail="You already own this client")
    
    # Check if there's already a pending request
    existing = await db.client_requests.find_one({
        "client_id": client_id,
        "requester_id": current_user["id"],
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Request already pending")
    
    # Get owner info
    owner = await db.users.find_one({"id": client.get("created_by")}, {"_id": 0, "name": 1, "email": 1})
    
    request_doc = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "client_name": f"{client.get('first_name', '')} {client.get('last_name', '')}",
        "client_phone": client.get("phone", ""),
        "owner_id": client.get("created_by"),
        "owner_name": owner.get("name", "") if owner else "Unknown",
        "requester_id": current_user["id"],
        "requester_name": current_user.get("name", current_user.get("email", "")),
        "status": "pending",  # pending, approved, rejected
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.client_requests.insert_one(request_doc)
    
    # Create notification for owner
    notif_doc = {
        "id": str(uuid.uuid4()),
        "user_id": client.get("created_by"),
        "message": f"{current_user.get('name', 'A user')} solicita acceso al cliente {client.get('first_name', '')} {client.get('last_name', '')}",
        "type": "client_request",
        "link": "/solicitudes",
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif_doc)
    
    return {"message": "Request sent", "request_id": request_doc["id"]}

@api_router.get("/client-requests")
async def get_client_requests(current_user: dict = Depends(get_current_user)):
    """Get all client requests (sent and received)"""
    # Get requests I sent
    sent = await db.client_requests.find(
        {"requester_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Get requests I received (as owner) or all if admin/bdc/bdc_manager
    if current_user["role"] in ["admin", "bdc", "bdc_manager"]:
        received = await db.client_requests.find(
            {"status": "pending"},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    else:
        received = await db.client_requests.find(
            {"owner_id": current_user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    return {"sent": sent, "received": received}

@api_router.put("/client-requests/{request_id}")
async def respond_to_request(request_id: str, action: str, current_user: dict = Depends(get_current_user)):
    """Approve or reject a client request"""
    if action not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Action must be 'approved' or 'rejected'")
    
    request = await db.client_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Only owner, admin, bdc, or bdc_manager can respond
    if current_user["role"] not in ["admin", "bdc", "bdc_manager"] and request.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.client_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": action,
            "responded_by": current_user["id"],
            "responded_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If approved, transfer the client
    if action == "approved":
        await db.clients.update_one(
            {"id": request.get("client_id")},
            {"$set": {
                "created_by": request.get("requester_id"),
                "transferred_from": request.get("owner_id"),
                "transferred_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Notify the requester
    notif_doc = {
        "id": str(uuid.uuid4()),
        "user_id": request.get("requester_id"),
        "message": f"Tu solicitud para el cliente {request.get('client_name', '')} fue {'aprobada' if action == 'approved' else 'rechazada'}",
        "type": "client_request_response",
        "link": "/solicitudes",
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif_doc)
    
    return {"message": f"Request {action}"}

# ==================== SALESPERSON PERFORMANCE (BDC) ====================

@api_router.get("/bdc/salesperson-performance")
async def get_bdc_salesperson_performance(current_user: dict = Depends(get_current_user)):
    """Get performance metrics for all active telemarketers (BDC Manager and Admin only)"""
    if current_user["role"] not in ["admin", "bdc", "bdc_manager"]:
        raise HTTPException(status_code=403, detail="BDC Manager or Admin access required")
    
    # Get all active telemarketers (exclude inactive and deleted users)
    salespeople = await db.users.find(
        {
            "role": {"$in": ["salesperson", "telemarketer", "vendedor"]},
            "is_active": {"$ne": False},  # Only active users
            "is_deleted": {"$ne": True}   # Not deleted users
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1}
    ).to_list(100)
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    performance = []
    for sp in salespeople:
        sp_id = sp["id"]
        
        # Clients created
        clients_today = await db.clients.count_documents({
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": today.isoformat()}
        })
        clients_week = await db.clients.count_documents({
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": week_ago.isoformat()}
        })
        clients_month = await db.clients.count_documents({
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": month_ago.isoformat()}
        })
        clients_total = await db.clients.count_documents({
            "created_by": sp_id,
            "is_deleted": {"$ne": True}
        })
        
        # Appointments created
        appts_today = await db.appointments.count_documents({
            "salesperson_id": sp_id,
            "created_at": {"$gte": today.isoformat()}
        })
        appts_week = await db.appointments.count_documents({
            "salesperson_id": sp_id,
            "created_at": {"$gte": week_ago.isoformat()}
        })
        appts_month = await db.appointments.count_documents({
            "salesperson_id": sp_id,
            "created_at": {"$gte": month_ago.isoformat()}
        })
        
        # Sales (completed records)
        sales_today = await db.user_records.count_documents({
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": today.isoformat()}
        })
        sales_week = await db.user_records.count_documents({
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": week_ago.isoformat()}
        })
        sales_month = await db.user_records.count_documents({
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": month_ago.isoformat()}
        })
        sales_total = await db.user_records.count_documents({
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True}
        })
        
        # Records total
        records_total = await db.user_records.count_documents({
            "salesperson_id": sp_id,
            "is_deleted": {"$ne": True}
        })
        
        performance.append({
            "id": sp_id,
            "name": sp.get("name", sp.get("email", "")),
            "email": sp.get("email", ""),
            "clients": {
                "today": clients_today,
                "week": clients_week,
                "month": clients_month,
                "total": clients_total
            },
            "appointments": {
                "today": appts_today,
                "week": appts_week,
                "month": appts_month
            },
            "sales": {
                "today": sales_today,
                "week": sales_week,
                "month": sales_month,
                "total": sales_total
            },
            "records_total": records_total
        })
    
    return performance

# ==================== BACKUP & RESTORE ENDPOINTS (Admin Only) ====================

@api_router.get("/admin/backup")
async def download_backup(current_user: dict = Depends(get_current_user)):
    """Download complete database backup as JSON (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden descargar backups")
    
    try:
        backup_data = {
            "backup_date": datetime.now(timezone.utc).isoformat(),
            "backup_version": "1.0",
            "collections": {}
        }
        
        # List of collections to backup - ALL important collections
        collections_to_backup = [
            "users",
            "clients",
            "user_records",          # Changed from "records" to correct name
            "cosigner_records",
            "cosigner_relations",    # Added
            "appointments",
            "prequalify_submissions",
            "config_lists",
            "record_comments",
            "client_comments",       # Added - client notes
            "client_requests",       # Added - ownership transfer requests
            "notifications",         # Added - in-app notifications
            "sms_logs",              # Added - SMS history
            "email_logs",            # Added - Email history
            "sms_templates",         # Added - SMS templates
            "sms_conversations",     # Added - SMS conversation threads
            "imported_contacts",     # Added - Marketing contacts
            "public_links",          # Added - Public appointment links
            "collaboration_requests" # Added - Collaboration requests
        ]
        
        for collection_name in collections_to_backup:
            try:
                collection = db[collection_name]
                # Get all documents, excluding MongoDB _id
                documents = await collection.find({}, {"_id": 0}).to_list(length=None)
                backup_data["collections"][collection_name] = documents
                logger.info(f"Backup: {collection_name} - {len(documents)} documents")
            except Exception as e:
                logger.warning(f"Could not backup {collection_name}: {str(e)}")
                backup_data["collections"][collection_name] = []
        
        # Convert to JSON
        json_data = json_lib.dumps(backup_data, ensure_ascii=False, indent=2, default=str)
        
        # Return as downloadable file
        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=carplus_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    except Exception as e:
        logger.error(f"Backup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear backup: {str(e)}")


@api_router.post("/admin/restore")
async def restore_backup(
    file: UploadFile = File(...),
    merge_mode: str = Form("replace"),
    current_user: dict = Depends(get_current_user)
):
    """Restore database from JSON backup file (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden restaurar backups")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="El archivo debe ser .json")
    
    try:
        # Read and parse JSON
        content = await file.read()
        backup_data = json_lib.loads(content.decode('utf-8'))
        
        # Validate backup structure
        if "collections" not in backup_data:
            raise HTTPException(status_code=400, detail="Formato de backup inválido")
        
        # Validate merge_mode
        if merge_mode not in ["replace", "merge"]:
            merge_mode = "replace"
        
        # Collections to restore - ALL data collections (not users to avoid lockout)
        collections_to_restore = [
            "clients",
            "user_records",          # Changed from "records" to correct name
            "cosigner_records",
            "cosigner_relations",    # Added
            "appointments",
            "prequalify_submissions",
            "config_lists",
            "record_comments",
            "client_comments",       # Added - client notes
            "client_requests",       # Added - ownership transfer requests
            "notifications",         # Added - in-app notifications
            "sms_logs",              # Added - SMS history
            "email_logs",            # Added - Email history
            "sms_templates",         # Added - SMS templates
            "sms_conversations",     # Added - SMS conversation threads
            "imported_contacts",     # Added - Marketing contacts
            "public_links",          # Added - Public appointment links
            "collaboration_requests" # Added - Collaboration requests
        ]
        
        # Also support old backup files that used "records" instead of "user_records"
        if "records" in backup_data["collections"] and "user_records" not in backup_data["collections"]:
            backup_data["collections"]["user_records"] = backup_data["collections"]["records"]
        
        # Note: We don't restore 'users' to avoid locking out the current admin
        
        restore_stats = {}
        
        for collection_name in collections_to_restore:
            if collection_name in backup_data["collections"]:
                documents = backup_data["collections"][collection_name]
                
                if documents:
                    if merge_mode == "merge":
                        # Merge mode: Update existing documents by ID, insert new ones
                        inserted = 0
                        updated = 0
                        for doc in documents:
                            doc_id = doc.get("id")
                            if doc_id:
                                result = await db[collection_name].update_one(
                                    {"id": doc_id},
                                    {"$set": doc},
                                    upsert=True
                                )
                                if result.upserted_id:
                                    inserted += 1
                                else:
                                    updated += 1
                            else:
                                # Document without ID, just insert
                                await db[collection_name].insert_one(doc)
                                inserted += 1
                        restore_stats[collection_name] = {"inserted": inserted, "updated": updated, "total": len(documents)}
                        logger.info(f"Merged {collection_name}: {inserted} inserted, {updated} updated")
                    else:
                        # Replace mode: Clear and insert all
                        await db[collection_name].delete_many({})
                        await db[collection_name].insert_many(documents)
                        restore_stats[collection_name] = {"replaced": len(documents)}
                        logger.info(f"Restored {collection_name}: {len(documents)} documents")
                else:
                    if merge_mode != "merge":
                        # Only clear collection in replace mode
                        await db[collection_name].delete_many({})
                    restore_stats[collection_name] = {"replaced": 0} if merge_mode != "merge" else {"merged": 0}
        
        # Create restore log
        restore_log = {
            "id": str(uuid.uuid4()),
            "restored_by": current_user["email"],
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "backup_date": backup_data.get("backup_date"),
            "merge_mode": merge_mode,
            "stats": restore_stats
        }
        
        # Save restore log
        await db.restore_logs.insert_one(restore_log)
        
        total_docs = sum(
            s.get("total", s.get("replaced", 0)) if isinstance(s, dict) else s 
            for s in restore_stats.values()
        )
        
        return {
            "message": f"Backup restaurado exitosamente ({merge_mode} mode). {total_docs} registros procesados.",
            "stats": restore_stats,
            "merge_mode": merge_mode
        }
        
    except json_lib.JSONDecodeError:
        raise HTTPException(status_code=400, detail="El archivo JSON no es válido")
    except Exception as e:
        logger.error(f"Restore error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al restaurar: {str(e)}")


@api_router.delete("/admin/delete-all-data")
async def delete_all_data(current_user: dict = Depends(get_current_user)):
    """Delete ALL CRM data permanently (Admin only) - DANGEROUS OPERATION"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar datos")
    
    try:
        delete_stats = {}
        
        # Collections to delete (NOT including users to keep admin access)
        collections_to_delete = [
            "clients",
            "user_records",          # Changed from "records" to correct name
            "cosigner_records",
            "cosigner_relations",
            "appointments",
            "prequalify_submissions",
            "record_comments",
            "client_comments",
            "client_requests",
            "notifications",
            "sms_logs",
            "email_logs",
            "sms_conversations",
            "imported_contacts",
            "public_links",
            "collaboration_requests"
        ]
        
        for collection_name in collections_to_delete:
            try:
                result = await db[collection_name].delete_many({})
                delete_stats[collection_name] = result.deleted_count
                logger.warning(f"DELETED ALL from {collection_name}: {result.deleted_count} documents")
            except Exception as e:
                logger.error(f"Error deleting {collection_name}: {str(e)}")
                delete_stats[collection_name] = f"Error: {str(e)}"
        
        # Log the deletion
        delete_log = {
            "id": str(uuid.uuid4()),
            "deleted_by": current_user["email"],
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "stats": delete_stats
        }
        await db.delete_logs.insert_one(delete_log)
        
        total_deleted = sum(v for v in delete_stats.values() if isinstance(v, int))
        
        return {
            "message": f"Todos los datos eliminados. {total_deleted} registros eliminados en total.",
            "stats": delete_stats
        }
        
    except Exception as e:
        logger.error(f"Delete all error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar datos: {str(e)}")


@api_router.post("/admin/reset-id-types")
async def reset_id_types(current_user: dict = Depends(get_current_user)):
    """Reset ID Type options to new Spanish values (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden resetear opciones")
    
    try:
        # New ID types in Spanish
        new_id_types = [
            "Licencia de Conducir", "Pasaporte", "Pasaporte USA", "Matrícula", 
            "Credencial de Elector", "ID de Residente", "Otro"
        ]
        
        # Delete existing id_type entries
        await db.config_lists.delete_many({"category": "id_type"})
        
        # Insert new values
        for item in new_id_types:
            await db.config_lists.insert_one({
                "id": str(uuid.uuid4()),
                "category": "id_type",
                "value": item,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        logger.info(f"ID Types reset by {current_user['email']}")
        
        return {
            "message": f"Opciones de ID Type actualizadas: {len(new_id_types)} opciones",
            "options": new_id_types
        }
        
    except Exception as e:
        logger.error(f"Reset ID types error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@api_router.post("/admin/sync-sold-clients")
async def sync_sold_clients(current_user: dict = Depends(get_current_user)):
    """Synchronize sold clients - mark clients as sold based on completed records (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden sincronizar clientes vendidos")
    
    try:
        # Find all clients with completed records that aren't marked as sold
        completed_records = await db.user_records.find(
            {"record_status": "completed", "is_deleted": {"$ne": True}},
            {"_id": 0, "client_id": 1, "created_at": 1}
        ).to_list(1000)
        
        synced_count = 0
        for record in completed_records:
            client_id = record["client_id"]
            
            # Check if client is already marked as sold
            client = await db.clients.find_one({"id": client_id}, {"_id": 0, "is_sold": 1})
            if client and not client.get("is_sold", False):
                # Mark client as sold
                await db.clients.update_one(
                    {"id": client_id},
                    {"$set": {
                        "is_sold": True,
                        "sold_at": record["created_at"]
                    }}
                )
                synced_count += 1
        
        logger.info(f"Sold clients synchronized by {current_user['email']}: {synced_count} clients updated")
        
        return {
            "message": f"Sincronización completada: {synced_count} clientes marcados como vendidos",
            "synced_count": synced_count,
            "total_completed_records": len(completed_records)
        }
        
    except Exception as e:
        logger.error(f"Sync sold clients error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al sincronizar: {str(e)}")

# ==================== SCHEDULER ENDPOINTS ====================

@api_router.get("/scheduler/status")
async def get_scheduler_status(current_user: dict = Depends(get_current_user)):
    """Get the status of the SMS scheduler (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    # Get stats on pending contacts
    pending_initial = await db.imported_contacts.count_documents({
        "opt_out": False,
        "appointment_created": False,
        "sms_sent": False
    })
    
    pending_reminder = await db.imported_contacts.count_documents({
        "opt_out": False,
        "appointment_created": False,
        "sms_sent": True,
        "sms_count": {"$lt": 5}
    })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "pending_stats": {
            "contacts_awaiting_initial_sms": pending_initial,
            "contacts_eligible_for_reminder": pending_reminder
        }
    }

@api_router.post("/scheduler/run-now")
async def run_marketing_sms_now(current_user: dict = Depends(get_current_user)):
    """Manually trigger the marketing SMS job (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Run the job in background
    asyncio.create_task(send_marketing_sms_job())
    
    return {"message": "Marketing SMS job started. Check logs for progress."}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "DealerCRM Pro API", "version": "1.0.0"}

# ==================== PRE-QUALIFY SUBMISSIONS ====================

class PreQualifySubmission(BaseModel):
    email: str
    firstName: str
    lastName: str
    phone: str
    idNumber: Optional[str] = None
    ssn: Optional[str] = None
    dateOfBirth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    housingType: Optional[str] = None
    rentAmount: Optional[str] = None
    # Time at address - separated fields
    timeAtAddressYears: Optional[int] = None
    timeAtAddressMonths: Optional[int] = None
    employerName: Optional[str] = None
    # Time with employer - separated fields
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    estimatedDownPayment: Optional[str] = None
    consentAccepted: bool = False

class PreQualifyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    firstName: str
    lastName: str
    phone: str
    idNumber: Optional[str] = None
    idType: Optional[str] = None
    ssn: Optional[str] = None
    ssnType: Optional[str] = None
    dateOfBirth: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    housingType: Optional[str] = None
    rentAmount: Optional[str] = None
    # Time at address - separated fields
    timeAtAddressYears: Optional[int] = None
    timeAtAddressMonths: Optional[int] = None
    employerName: Optional[str] = None
    # Time with employer - separated fields
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    estimatedDownPayment: Optional[str] = None
    consentAccepted: bool = False
    language: Optional[str] = None
    created_at: str
    status: str = "pending"
    matched_client_id: Optional[str] = None
    matched_client_name: Optional[str] = None
    id_file_url: Optional[str] = None  # URL del documento de ID subido

@api_router.post("/prequalify/submit")
async def submit_prequalify(submission: PreQualifySubmission):
    existing_client = await db.clients.find_one(
        {"phone": {"$regex": submission.phone[-10:], "$options": "i"}, "is_deleted": {"$ne": True}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1}
    )
    doc = {
        "id": str(uuid.uuid4()),
        **submission.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "matched_client_id": existing_client["id"] if existing_client else None,
        "matched_client_name": f"{existing_client['first_name']} {existing_client['last_name']}" if existing_client else None
    }
    await db.prequalify_submissions.insert_one(doc)
    del doc["_id"]
    
    # Send email notification to ALL admins
    try:
        admin_users = await db.users.find(
            {"role": "admin", "approved": {"$ne": False}},
            {"_id": 0, "id": 1, "email": 1, "full_name": 1}
        ).to_list(100)
        
        if admin_users:
            frontend_url = os.environ.get('FRONTEND_URL', '')
            prequalify_link = f"{frontend_url}/prequalify" if frontend_url else ""
            
            # Build HTML email with ALL submission data
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}" style="max-width: 200px; height: auto; margin-bottom: 10px;">
                        <p style="color: #dc2626; font-weight: 600; margin: 5px 0;">{COMPANY_TAGLINE}</p>
                        <p style="color: #6b7280; margin: 5px 0;">Nueva Solicitud de Pre-Calificación</p>
                    </div>
                    
                    <div style="background: #dbeafe; border-left: 4px solid #1e40af; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
                        <strong style="color: #1e40af;">¡Nueva solicitud recibida!</strong>
                        <p style="margin: 5px 0 0 0; color: #374151;">Se ha recibido una nueva solicitud de pre-calificación.</p>
                    </div>
                    
                    <h2 style="color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📋 Información Personal</h2>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">Nombre Completo</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.firstName} {submission.lastName}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Email</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.email}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Teléfono</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.phone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">ID/Licencia</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.idNumber or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">SSN</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.ssn or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Fecha de Nacimiento</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.dateOfBirth or 'No proporcionado'}</td>
                        </tr>
                    </table>
                    
                    <h2 style="color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">🏠 Información de Vivienda</h2>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">Dirección</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.address or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Ciudad</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.city or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Estado</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.state or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Código Postal</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.zipCode or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Tipo de Vivienda</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.housingType or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Monto de Renta</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.rentAmount or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Tiempo en Dirección</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.timeAtAddress or 'No proporcionado'}</td>
                        </tr>
                    </table>
                    
                    <h2 style="color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">💼 Información Laboral</h2>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">Empleador</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.employerName or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Tiempo con Empleador</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.timeWithEmployer or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Tipo de Ingreso</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.incomeType or 'No proporcionado'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Ingreso Neto</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.netIncome or 'No proporcionado'}</td>
                        </tr>
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Frecuencia de Pago</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.incomeFrequency or 'No proporcionado'}</td>
                        </tr>
                    </table>
                    
                    <h2 style="color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">💰 Información Financiera</h2>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr style="background: #f9fafb;">
                            <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; width: 40%;">Enganche Estimado</td>
                            <td style="padding: 10px; border: 1px solid #e5e7eb;">{submission.estimatedDownPayment or 'No proporcionado'}</td>
                        </tr>
                    </table>
                    
                    {"<div style='background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-bottom: 20px; border-radius: 5px;'><strong style='color: #b45309;'>⚠️ Cliente Existente Encontrado</strong><p style='margin: 5px 0 0 0; color: #374151;'>Se encontró un cliente con el mismo teléfono: <strong>" + existing_client['first_name'] + " " + existing_client['last_name'] + "</strong></p></div>" if existing_client else ""}
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{prequalify_link}" style="background: #1e40af; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Ver en Panel de Pre-Calificación</a>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 12px;">
                        <p>Este es un mensaje automático del sistema CRM CARPLUS AUTOSALE</p>
                        <p>Fecha de recepción: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send to all admin emails
            for admin in admin_users:
                admin_email = admin.get('email')
                if admin_email:
                    try:
                        await send_email_notification(
                            to_email=admin_email,
                            subject=f"🚗 Nueva Pre-Calificación: {submission.firstName} {submission.lastName}",
                            html_content=html_content
                        )
                        logger.info(f"Pre-qualify notification sent to admin: {admin_email}")
                    except Exception as email_error:
                        logger.error(f"Failed to send pre-qualify notification to {admin_email}: {str(email_error)}")
        
        # Create in-app notification for all admins
        for admin in admin_users:
            notification_doc = {
                "id": str(uuid.uuid4()),
                "user_id": admin.get("id") or admin.get("email"),
                "type": "prequalify",
                "title": "Nueva Pre-Calificación",
                "message": f"Nueva solicitud de {submission.firstName} {submission.lastName} - Tel: {submission.phone}",
                "link": "/prequalify",
                "data": {
                    "submission_id": doc["id"],
                    "name": f"{submission.firstName} {submission.lastName}",
                    "phone": submission.phone,
                    "email": submission.email,
                    "matched": existing_client is not None
                },
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification_doc)
            logger.info(f"In-app notification created for admin: {admin.get('email')}")
            
    except Exception as e:
        logger.error(f"Error sending pre-qualify admin notifications: {str(e)}")
        # Don't fail the submission if email fails
    
    return {"message": "Pre-qualify submission received", "id": doc["id"], "matched": existing_client is not None}

# New endpoint with file upload support (multiple files)
@api_router.post("/prequalify/submit-with-file")
async def submit_prequalify_with_file(
    email: str = Form(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    phone: str = Form(...),
    idNumber: Optional[str] = Form(None),
    idType: Optional[str] = Form(None),
    ssn: Optional[str] = Form(None),
    ssnType: Optional[str] = Form(None),
    # Support both date field naming conventions
    dateOfBirth: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),  # Alternative from website
    address: Optional[str] = Form(None),
    apartment: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    zipCode: Optional[str] = Form(None),
    housingType: Optional[str] = Form(None),
    rentAmount: Optional[str] = Form(None),
    # Time at address - separated fields (accept as str for robustness)
    timeAtAddressYears: Optional[str] = Form(None),
    timeAtAddressMonths: Optional[str] = Form(None),
    employerName: Optional[str] = Form(None),
    # Time with employer - separated fields (support both naming conventions)
    timeWithEmployerYears: Optional[str] = Form(None),
    timeWithEmployerMonths: Optional[str] = Form(None),
    # Alternative names from website form
    employmentTimeYears: Optional[str] = Form(None),
    employmentTimeMonths: Optional[str] = Form(None),
    incomeType: Optional[str] = Form(None),
    netIncome: Optional[str] = Form(None),
    incomeFrequency: Optional[str] = Form(None),
    # Support both down payment field naming conventions
    estimatedDownPayment: Optional[str] = Form(None),
    downPayment: Optional[str] = Form(None),  # Alternative from website
    consentAccepted: bool = Form(False),
    language: Optional[str] = Form(None),
    # Support multiple file field names
    id_file: Optional[UploadFile] = File(None),
    id_files: List[UploadFile] = File(default=[]),
    idFile: Optional[UploadFile] = File(None)  # Alternative from website
):
    """Submit pre-qualify form with optional ID document upload (supports multiple files)"""
    from PyPDF2 import PdfMerger, PdfReader
    from PIL import Image
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    # === HELPER FUNCTION to safely convert to int ===
    def safe_int(value):
        """Convert value to int, return None if not possible"""
        if value is None or value == '' or value == 'null' or value == 'undefined':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    # === NORMALIZE FIELD NAMES (support both naming conventions) ===
    # Date of birth
    final_dateOfBirth = dateOfBirth or date_of_birth
    # Down payment
    final_downPayment = estimatedDownPayment or downPayment
    
    # Time at address - convert to int safely
    final_timeAtAddressYears = safe_int(timeAtAddressYears)
    final_timeAtAddressMonths = safe_int(timeAtAddressMonths)
    
    # Employment time (use whichever is provided) - convert to int safely
    final_employmentYears = safe_int(timeWithEmployerYears) or safe_int(employmentTimeYears)
    final_employmentMonths = safe_int(timeWithEmployerMonths) or safe_int(employmentTimeMonths)
    
    # Debug log - DETAILED for all critical fields
    logger.info(f"=== PRE-QUALIFY SUBMISSION RECEIVED ===")
    logger.info(f"Name: {firstName} {lastName}")
    logger.info(f"idNumber: '{idNumber}'")
    logger.info(f"idType: '{idType}'")
    logger.info(f"ssn: '{ssn}'")
    logger.info(f"ssnType: '{ssnType}'")
    logger.info(f"dateOfBirth: '{dateOfBirth}' | date_of_birth: '{date_of_birth}' -> final: '{final_dateOfBirth}'")
    logger.info(f"timeAtAddressYears RAW: '{timeAtAddressYears}' -> final: '{final_timeAtAddressYears}'")
    logger.info(f"timeAtAddressMonths RAW: '{timeAtAddressMonths}' -> final: '{final_timeAtAddressMonths}'")
    logger.info(f"employmentTimeYears: '{employmentTimeYears}' | timeWithEmployerYears: '{timeWithEmployerYears}' -> final: '{final_employmentYears}'")
    logger.info(f"employmentTimeMonths: '{employmentTimeMonths}' | timeWithEmployerMonths: '{timeWithEmployerMonths}' -> final: '{final_employmentMonths}'")
    logger.info(f"estimatedDownPayment: '{estimatedDownPayment}' | downPayment: '{downPayment}' -> final: '{final_downPayment}'")
    logger.info(f"=== END SUBMISSION DATA ===")
    
    # Check for existing client by phone
    existing_client = await db.clients.find_one(
        {"phone": {"$regex": phone[-10:], "$options": "i"}, "is_deleted": {"$ne": True}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1}
    )
    
    submission_id = str(uuid.uuid4())
    id_file_url = None
    
    # Collect all files (single file + multiple files + alternative name)
    all_files = []
    if id_file and id_file.filename:
        all_files.append(id_file)
    if idFile and idFile.filename:  # Alternative name from website
        all_files.append(idFile)
    if id_files:
        all_files.extend([f for f in id_files if f.filename])
    
    # Handle file upload if provided
    if all_files:
        try:
            upload_dir = Path(__file__).parent / "uploads"
            upload_dir.mkdir(exist_ok=True)
            temp_dir = upload_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            temp_files = []
            
            for idx, file in enumerate(all_files):
                file_extension = Path(file.filename).suffix.lower()
                if file_extension not in ['.pdf', '.jpg', '.jpeg', '.png']:
                    continue  # Skip invalid files
                
                content = await file.read()
                temp_filename = f"temp_{submission_id}_{idx}{file_extension}"
                temp_path = temp_dir / temp_filename
                
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                temp_files.append((temp_path, file_extension))
            
            if temp_files:
                # If only one file and it's a PDF, just use it directly
                if len(temp_files) == 1 and temp_files[0][1] == '.pdf':
                    final_filename = f"prequalify_{submission_id}_id.pdf"
                    final_path = upload_dir / final_filename
                    shutil.move(str(temp_files[0][0]), str(final_path))
                    id_file_url = f"/uploads/{final_filename}"
                
                # If only one file and it's an image, convert to PDF
                elif len(temp_files) == 1 and temp_files[0][1] in ['.jpg', '.jpeg', '.png']:
                    final_filename = f"prequalify_{submission_id}_id.pdf"
                    final_path = upload_dir / final_filename
                    
                    img = Image.open(temp_files[0][0])
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    img.save(str(final_path), 'PDF', resolution=100.0)
                    
                    # Remove temp file
                    temp_files[0][0].unlink()
                    id_file_url = f"/uploads/{final_filename}"
                
                # Multiple files - combine into single PDF
                else:
                    final_filename = f"prequalify_{submission_id}_id.pdf"
                    final_path = upload_dir / final_filename
                    merger = PdfMerger()
                    
                    for temp_path, ext in temp_files:
                        if ext == '.pdf':
                            try:
                                merger.append(str(temp_path))
                            except Exception as e:
                                logger.error(f"Error merging PDF {temp_path}: {e}")
                        elif ext in ['.jpg', '.jpeg', '.png']:
                            # Convert image to PDF first
                            img_pdf_path = temp_path.with_suffix('.temp.pdf')
                            try:
                                img = Image.open(temp_path)
                                if img.mode == 'RGBA':
                                    img = img.convert('RGB')
                                img.save(str(img_pdf_path), 'PDF', resolution=100.0)
                                merger.append(str(img_pdf_path))
                                img_pdf_path.unlink()  # Remove temp PDF
                            except Exception as e:
                                logger.error(f"Error converting image {temp_path}: {e}")
                    
                    if merger.pages:
                        merger.write(str(final_path))
                        merger.close()
                        id_file_url = f"/uploads/{final_filename}"
                    
                    # Clean up temp files
                    for temp_path, _ in temp_files:
                        try:
                            if temp_path.exists():
                                temp_path.unlink()
                        except:
                            pass
                
                logger.info(f"Pre-qualify ID file(s) uploaded and combined: {id_file_url}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading/combining pre-qualify ID files: {str(e)}")
            import traceback
            traceback.print_exc()
    
    doc = {
        "id": submission_id,
        "email": email,
        "firstName": firstName,
        "lastName": lastName,
        "phone": phone,
        "idNumber": idNumber,
        "idType": idType,
        "ssn": ssn,
        "ssnType": ssnType,
        "dateOfBirth": final_dateOfBirth,  # Use normalized value
        "address": address,
        "apartment": apartment,
        "city": city,
        "state": state,
        "zipCode": zipCode,
        "housingType": housingType,
        "rentAmount": rentAmount,
        # Time at address - use normalized int values
        "timeAtAddressYears": final_timeAtAddressYears,
        "timeAtAddressMonths": final_timeAtAddressMonths,
        "employerName": employerName,
        # Time with employer - use normalized int values
        "timeWithEmployerYears": final_employmentYears,
        "timeWithEmployerMonths": final_employmentMonths,
        "incomeType": incomeType,
        "netIncome": netIncome,
        "incomeFrequency": incomeFrequency,
        "estimatedDownPayment": final_downPayment,  # Use normalized value
        "consentAccepted": consentAccepted,
        "language": language,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "matched_client_id": existing_client["id"] if existing_client else None,
        "matched_client_name": f"{existing_client['first_name']} {existing_client['last_name']}" if existing_client else None,
        "id_file_url": id_file_url
    }
    
    await db.prequalify_submissions.insert_one(doc)
    del doc["_id"]
    
    # Send email notification to ALL admins (same as original endpoint)
    try:
        admin_users = await db.users.find(
            {"role": "admin", "approved": {"$ne": False}},
            {"_id": 0, "id": 1, "email": 1, "full_name": 1}
        ).to_list(100)
        
        if admin_users:
            frontend_url = os.environ.get('FRONTEND_URL', '')
            prequalify_link = f"{frontend_url}/prequalify" if frontend_url else ""
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <img src="{COMPANY_LOGO_URL}" alt="{COMPANY_NAME}" style="max-width: 200px; height: auto;">
                        <p style="color: #dc2626; font-weight: 600;">{COMPANY_TAGLINE}</p>
                    </div>
                    <p>Nueva Solicitud de Pre-Calificación</p>
                    <hr/>
                    <h3>📋 Información Personal</h3>
                    <p><strong>Nombre:</strong> {firstName} {lastName}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Teléfono:</strong> {phone}</p>
                    <p><strong>Fecha de Nacimiento:</strong> {final_dateOfBirth or 'No proporcionado'}</p>
                    <p><strong>Tipo de ID:</strong> {idType or 'No proporcionado'}</p>
                    <p><strong>Número de ID:</strong> {idNumber or 'No proporcionado'}</p>
                    <p><strong>Tipo SSN/ITIN:</strong> {ssnType or 'No proporcionado'}</p>
                    <p><strong>SSN/ITIN (últimos 4):</strong> {ssn or 'No proporcionado'}</p>
                    <p><strong>Documento ID Adjunto:</strong> {'✅ Sí' if id_file_url else '❌ No'}</p>
                    <hr/>
                    <h3>🏠 Información de Vivienda</h3>
                    <p><strong>Dirección:</strong> {address or ''}, {city or ''}, {state or ''} {zipCode or ''}</p>
                    <p><strong>Apartamento:</strong> {apartment or 'N/A'}</p>
                    <p><strong>Tipo de Vivienda:</strong> {housingType or 'No proporcionado'}</p>
                    <p><strong>Monto de Renta:</strong> {rentAmount or 'N/A'}</p>
                    <p><strong>Tiempo en Dirección:</strong> {final_timeAtAddressYears or 0} años, {final_timeAtAddressMonths or 0} meses</p>
                    <hr/>
                    <h3>💼 Información de Empleo</h3>
                    <p><strong>Empleador:</strong> {employerName or 'No proporcionado'}</p>
                    <p><strong>Tiempo de Empleo:</strong> {final_employmentYears or 0} años, {final_employmentMonths or 0} meses</p>
                    <p><strong>Tipo de Ingreso:</strong> {incomeType or 'No proporcionado'}</p>
                    <p><strong>Ingreso Neto:</strong> {netIncome or 'No proporcionado'}</p>
                    <p><strong>Frecuencia de Pago:</strong> {incomeFrequency or 'No proporcionado'}</p>
                    <p><strong>Enganche Estimado:</strong> {final_downPayment or 'No proporcionado'}</p>
                    {"<p style='color: orange;'><strong>⚠️ Cliente existente encontrado: " + existing_client['first_name'] + " " + existing_client['last_name'] + "</strong></p>" if existing_client else ""}
                    <br/>
                    <a href="{prequalify_link}" style="background: #dc2626; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ver en Panel</a>
                </div>
            </body>
            </html>
            """
            
            for admin in admin_users:
                admin_email = admin.get('email')
                if admin_email:
                    try:
                        await send_email_notification(
                            to_email=admin_email,
                            subject=f"🚗 Nueva Pre-Calificación: {firstName} {lastName}",
                            html_content=html_content
                        )
                        logger.info(f"Pre-qualify notification sent to admin: {admin_email}")
                    except Exception as email_error:
                        logger.error(f"Failed to send pre-qualify notification to {admin_email}: {str(email_error)}")
        
        # Create in-app notification for all admins
        for admin in admin_users:
            notification_doc = {
                "id": str(uuid.uuid4()),
                "user_id": admin.get("id") or admin.get("email"),
                "type": "prequalify",
                "title": "Nueva Pre-Calificación",
                "message": f"Nueva solicitud de {firstName} {lastName} - Tel: {phone}",
                "link": "/prequalify",
                "data": {
                    "submission_id": submission_id,
                    "name": f"{firstName} {lastName}",
                    "phone": phone,
                    "email": email,
                    "matched": existing_client is not None
                },
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification_doc)
            logger.info(f"In-app notification created for admin: {admin.get('email')}")
            
    except Exception as e:
        logger.error(f"Error sending pre-qualify admin notifications: {str(e)}")
    
    return {
        "message": "Pre-qualify submission received", 
        "id": submission_id, 
        "matched": existing_client is not None,
        "id_file_uploaded": id_file_url is not None
    }

@api_router.get("/prequalify/submissions", response_model=List[PreQualifyResponse])
async def get_prequalify_submissions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submissions = await db.prequalify_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for sub in submissions:
        if not sub.get("matched_client_id"):
            phone = sub.get("phone", "")
            if phone:
                existing_client = await db.clients.find_one(
                    {"phone": {"$regex": phone[-10:], "$options": "i"}, "is_deleted": {"$ne": True}},
                    {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
                )
                if existing_client:
                    sub["matched_client_id"] = existing_client["id"]
                    sub["matched_client_name"] = f"{existing_client['first_name']} {existing_client['last_name']}"
    return submissions

@api_router.get("/prequalify/submissions/{submission_id}")
async def get_prequalify_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    comparison = None
    if submission.get("matched_client_id"):
        client = await db.clients.find_one({"id": submission["matched_client_id"]}, {"_id": 0})
        if client:
            # Get the most recent record for this client
            latest_record = await db.user_records.find_one(
                {"client_id": client["id"], "is_deleted": {"$ne": True}},
                {"_id": 0, "id": 1},
                sort=[("created_at", -1)]
            )
            comparison = {
                "client": client, 
                "differences": [],
                "latest_record_id": latest_record["id"] if latest_record else None
            }
            if client.get("first_name", "").lower() != submission.get("firstName", "").lower():
                comparison["differences"].append({"field": "Nombre", "prequalify": submission.get("firstName"), "client": client.get("first_name")})
            if client.get("last_name", "").lower() != submission.get("lastName", "").lower():
                comparison["differences"].append({"field": "Apellido", "prequalify": submission.get("lastName"), "client": client.get("last_name")})
            if client.get("email", "").lower() != submission.get("email", "").lower():
                comparison["differences"].append({"field": "Email", "prequalify": submission.get("email"), "client": client.get("email")})
    return {"submission": submission, "comparison": comparison}

@api_router.post("/prequalify/submissions/{submission_id}/create-client")
async def create_client_from_prequalify(submission_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    client_id = str(uuid.uuid4())
    full_address = f"{submission.get('address', '')} {submission.get('city', '')} {submission.get('state', '')} {submission.get('zipCode', '')}".strip()
    
    # Transfer ID document if exists
    id_file_url = None
    id_uploaded = False
    prequalify_id_file = submission.get("id_file_url")
    
    if prequalify_id_file:
        try:
            # Copy file to client's document location
            upload_dir = Path(__file__).parent / "uploads"
            old_path = upload_dir / Path(prequalify_id_file).name
            logger.info(f"Looking for file at: {old_path}")
            if old_path.exists():
                file_extension = old_path.suffix
                new_filename = f"{client_id}_id{file_extension}"
                new_path = upload_dir / new_filename
                
                shutil.copy2(old_path, new_path)
                
                id_file_url = f"/uploads/{new_filename}"
                id_uploaded = True
                logger.info(f"Transferred ID document from pre-qualify to client: {id_file_url}")
            else:
                logger.warning(f"Pre-qualify ID file not found at: {old_path}")
        except Exception as e:
            logger.error(f"Error transferring ID document: {str(e)}")
    
    # Map ID type from pre-qualify to CRM format
    id_type_mapping = {
        # From website form
        "DL": "Licencia de Conducir",
        "Passport": "Pasaporte",
        "Matricula": "Matrícula",
        "Votacion ID": "Credencial de Elector",
        "US Passport": "Pasaporte USA",
        "Resident ID": "ID de Residente",
        "Other": "Otro",
        # Also accept Spanish values directly
        "Licencia de Conducir": "Licencia de Conducir",
        "Pasaporte": "Pasaporte",
        "Matrícula": "Matrícula",
        "Credencial de Elector": "Credencial de Elector",
        "Pasaporte USA": "Pasaporte USA",
        "ID de Residente": "ID de Residente",
        "Otro": "Otro"
    }
    
    raw_id_type = submission.get("idType", "")
    mapped_id_type = id_type_mapping.get(raw_id_type, raw_id_type) if raw_id_type else ""
    
    logger.info(f"ID Type mapping: '{raw_id_type}' -> '{mapped_id_type}'")
    
    client_doc = {
        "id": client_id,
        "first_name": submission.get("firstName", ""),
        "last_name": submission.get("lastName", ""),
        "phone": submission.get("phone", ""),
        "email": submission.get("email", ""),
        "address": full_address,
        "apartment": submission.get("apartment", ""),
        "date_of_birth": submission.get("dateOfBirth", ""),
        "id_type": mapped_id_type,  # Use mapped value
        "id_number": submission.get("idNumber", ""),  # ID/License number
        "ssn_type": submission.get("ssnType", ""),
        "ssn": submission.get("ssn", ""),
        "housing_type": submission.get("housingType", ""),
        "rent_amount": submission.get("rentAmount", ""),
        "time_at_address_years": submission.get("timeAtAddressYears"),
        "time_at_address_months": submission.get("timeAtAddressMonths"),
        "id_uploaded": id_uploaded,
        "id_file_url": id_file_url,
        "income_proof_uploaded": False,
        "residence_proof_uploaded": False,
        "salesperson_id": current_user["id"],
        "salesperson_name": current_user.get("name") or current_user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
        "is_deleted": False
    }
    await db.clients.insert_one(client_doc)
    
    # Format time at address for notes
    time_at_addr_str = "N/A"
    if submission.get('timeAtAddressYears') or submission.get('timeAtAddressMonths'):
        years = submission.get('timeAtAddressYears', 0) or 0
        months = submission.get('timeAtAddressMonths', 0) or 0
        time_at_addr_str = f"{years} años, {months} meses"
    
    # Format time with employer for notes
    time_with_emp_str = "N/A"
    if submission.get('timeWithEmployerYears') or submission.get('timeWithEmployerMonths'):
        years = submission.get('timeWithEmployerYears', 0) or 0
        months = submission.get('timeWithEmployerMonths', 0) or 0
        time_with_emp_str = f"{years} años, {months} meses"
    
    notes_content = f"""--- Pre-Qualify Data ---
Fecha Nacimiento: {submission.get('dateOfBirth', 'N/A')}
Tipo de ID: {submission.get('idType', 'N/A')}
ID/Pasaporte: {submission.get('idNumber', 'N/A')}
SSN/ITIN: {submission.get('ssn', 'N/A')}
Dirección: {full_address}
Tiempo en Dirección: {time_at_addr_str}
Tipo Vivienda: {submission.get('housingType', 'N/A')}
Renta Mensual: {submission.get('rentAmount', 'N/A')}
Empleador: {submission.get('employerName', 'N/A')}
Tiempo con Empleador: {time_with_emp_str}
Tipo de Ingreso: {submission.get('incomeType', 'N/A')}
Ingreso Neto: {submission.get('netIncome', 'N/A')}
Frecuencia de Ingreso: {submission.get('incomeFrequency', 'N/A')}
Down Payment: {submission.get('estimatedDownPayment', 'N/A')}"""

    record_doc = {
        "id": str(uuid.uuid4()),
        "client_id": client_doc["id"],
        "salesperson_id": current_user["id"],
        "salesperson_name": current_user.get("name") or current_user.get("email"),
        "opportunity_number": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "has_id": bool(submission.get("idNumber")) or id_uploaded,
        "id_type": mapped_id_type,  # Add ID type to record
        "ssn": bool(submission.get("ssn")),
        "employment_type": submission.get("incomeType", ""),
        "employment_company_name": submission.get("employerName", ""),
        "employment_time_years": submission.get("timeWithEmployerYears"),
        "employment_time_months": submission.get("timeWithEmployerMonths"),
        "income_frequency": submission.get("incomeFrequency", ""),
        "net_income_amount": submission.get("netIncome", ""),
        "finance_status": "no",
        "is_deleted": False
    }
    await db.user_records.insert_one(record_doc)
    note_doc = {
        "id": str(uuid.uuid4()),
        "record_id": record_doc["id"],
        "comment": notes_content,
        "user_id": current_user["id"],
        "user_name": current_user.get("name") or current_user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_id": current_user["id"],
        "created_by_name": current_user.get("name") or current_user.get("email"),
        "admin_only": True  # Only admin can see pre-qualify data
    }
    await db.record_comments.insert_one(note_doc)
    await db.prequalify_submissions.update_one(
        {"id": submission_id},
        {"$set": {"status": "converted", "matched_client_id": client_doc["id"], "matched_client_name": f"{client_doc['first_name']} {client_doc['last_name']}"}}
    )
    return {"message": "Cliente creado exitosamente", "client_id": client_doc["id"], "record_id": record_doc["id"], "id_transferred": id_uploaded}

@api_router.post("/prequalify/submissions/{submission_id}/add-to-notes")
async def add_prequalify_to_notes(submission_id: str, record_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    notes_content = f"--- Pre-Qualify Data ---\nEmail: {submission.get('email', 'N/A')}\nNombre: {submission.get('firstName', '')} {submission.get('lastName', '')}\nTeléfono: {submission.get('phone', 'N/A')}\nDirección: {submission.get('address', '')} {submission.get('city', '')} {submission.get('state', '')}\nEmpleador: {submission.get('employerName', 'N/A')}\nIngreso: {submission.get('netIncome', 'N/A')}\nDown Payment: {submission.get('estimatedDownPayment', 'N/A')}"
    note_doc = {
        "id": str(uuid.uuid4()),
        "record_id": record_id,
        "comment": notes_content,
        "user_id": current_user["id"],
        "user_name": current_user.get("name") or current_user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_id": current_user["id"],
        "created_by_name": current_user.get("name") or current_user.get("email"),
        "admin_only": True  # Only admin can see this note
    }
    await db.record_comments.insert_one(note_doc)
    await db.prequalify_submissions.update_one({"id": submission_id}, {"$set": {"status": "reviewed"}})
    return {"message": "Data added to record notes", "note_id": note_doc["id"]}

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
    """Initialize default banks, dealers, cars, ID types, POI types, and POR types if lists are empty"""
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
    
    # Default Dealers with addresses
    default_dealers = [
        {"name": "Downey", "address": "7444 Florence Ave, Downey, CA 90240"},
        {"name": "Fullerton", "address": "1100 S Harbor Blvd, Fullerton, CA 92832"},
        {"name": "Hollywood", "address": "6200 Hollywood Blvd, Los Angeles, CA 90028"},
        {"name": "Long Beach", "address": "1500 E Anaheim St, Long Beach, CA 90813"}
    ]
    
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
    
    # Default ID Types (for identification documents) - in Spanish
    default_id_types = [
        "Licencia de Conducir", "Pasaporte", "Pasaporte USA", "Matrícula", 
        "Credencial de Elector", "ID de Residente", "Otro"
    ]
    
    # Default POI Types (Proof of Income)
    default_poi_types = [
        "Cash", "Company Check", "Personal Check", "Talon de Cheque"
    ]
    
    # Default POR Types (Proof of Residence)
    default_por_types = [
        "Agua", "Luz", "Gas", "Internet", "TV Cable", "Telefono", "Car Insurance", "Bank Statements"
    ]
    
    # Initialize dealers with addresses (special handling)
    dealer_count = await db.config_lists.count_documents({"category": "dealer"})
    if dealer_count == 0:
        dealer_docs = [
            {
                "id": str(uuid.uuid4()),
                "name": dealer["name"],
                "address": dealer["address"],
                "category": "dealer",
                "created_at": now,
                "created_by": "system"
            }
            for dealer in default_dealers
        ]
        if dealer_docs:
            await db.config_lists.insert_many(dealer_docs)
            logger.info(f"Initialized {len(dealer_docs)} default dealers with addresses")
    
    # Check if other lists are empty and populate
    simple_categories = [
        ('bank', default_banks), 
        ('car', default_cars),
        ('id_type', default_id_types),
        ('poi_type', default_poi_types),
        ('por_type', default_por_types)
    ]
    
    for category, items in simple_categories:
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

