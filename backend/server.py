from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import shutil
from pathlib import Path
from document_authorization import can_access_documents, redact_documents
from document_paths import resolve_document_path
from document_attachments import collect_document_attachments
from crm_authorization import CRMAccess, SCOPED_COLLECTIONS
from runtime_security import jwt_secret, mock_delivery
from public_tokens import resolve_appointment_token
from upload_validation import validate_documents, upload_directory, bounded_read, validate_import
from webhook_security import validate_twilio_webhook
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from authentication.foundation import hash_password as safe_hash_password, passkey_options
from authentication.runtime import SessionAuth
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
JWT_SECRET = jwt_secret()
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

# V2 development never initializes a live communications provider.
twilio_client = None

# Create the main app
app = FastAPI(title="DealerCRM Pro API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Client documents are served only by authenticated document handlers.

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== DOCUMENT OPTIMIZATION ====================

def optimize_document(file_path: Path, max_size_kb: int = 500, max_dimension: int = 1800) -> Path:
    """
    Optimize a document for storage while maintaining readability.
    - For images: Resize if too large, convert to optimized JPEG
    - For PDFs: Compress images within the PDF
    Returns the path to the optimized file.
    """
    from PIL import Image
    
    file_ext = file_path.suffix.lower()
    
    # Image optimization
    if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.heic']:
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large while maintaining aspect ratio
                width, height = img.size
                if width > max_dimension or height > max_dimension:
                    if width > height:
                        new_width = max_dimension
                        new_height = int(height * (max_dimension / width))
                    else:
                        new_height = max_dimension
                        new_width = int(width * (max_dimension / height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save as optimized JPEG
                optimized_path = file_path.with_suffix('.jpg')
                
                # Start with quality 85, reduce if file is too large
                quality = 85
                while quality >= 50:
                    img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
                    if optimized_path.stat().st_size <= max_size_kb * 1024:
                        break
                    quality -= 10
                
                # Remove original if different path
                if optimized_path != file_path:
                    file_path.unlink()
                
                logger.info(f"Optimized image: {file_path.name} -> {optimized_path.stat().st_size / 1024:.1f}KB")
                return optimized_path
                
        except Exception as e:
            logger.error(f"Failed to optimize image {file_path}: {e}")
            return file_path
    
    # PDF optimization - just return as-is for now (complex to recompress)
    elif file_ext == '.pdf':
        # For PDFs, we'll keep them as-is to preserve document integrity
        logger.info(f"PDF document kept as-is: {file_path.name}")
        return file_path
    
    # Other file types - return as-is
    return file_path


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
            base_url = os.environ.get('FRONTEND_URL', '')
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
    Runs every 5 minutes to check for comments with reminder_at:
    - If reminder is 1 day away or less: send notification now
    - Notifications are sent 1 day before the reminder date
    Checks both client_comments and record_comments collections.
    """
    logger.info("Running comment reminders check job...")
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    one_day_from_now = (now + timedelta(days=1)).isoformat()
    
    # Find client comments with reminders that are due within the next 24 hours
    due_client_reminders = await db.client_comments.find({
        "reminder_at": {"$ne": None, "$lte": one_day_from_now},
        "reminder_sent": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    # Find record comments with reminders that are due within the next 24 hours
    due_record_reminders = await db.record_comments.find({
        "reminder_at": {"$ne": None, "$lte": one_day_from_now},
        "reminder_sent": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    logger.info(f"Found {len(due_client_reminders)} client reminders, {len(due_record_reminders)} record reminders (within 24 hours)")
    
    # Process client comments
    for comment in due_client_reminders:
        try:
            client = await db.clients.find_one({"id": comment["client_id"]}, {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1})
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
            client_phone = client.get("phone", "") if client else ""
            
            # Build link with owner_filter=all to ensure client is found
            link = f"/clients?search={client_phone}&owner_filter=all" if client_phone else "/clients?owner_filter=all"
            
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": comment["user_id"],
                "title": f"📝 Recordatorio: {client_name}",
                "message": comment['comment'][:100] + ('...' if len(comment['comment']) > 100 else ''),
                "type": "reminder",
                "link": link,
                "client_id": comment["client_id"],
                "is_read": False,
                "created_at": now_iso
            }
            await db.notifications.insert_one(notif_doc)
            
            await db.client_comments.update_one(
                {"id": comment["id"]},
                {"$set": {"reminder_sent": True}}
            )
            
            logger.info(f"Client reminder notification sent for comment {comment['id']} - {client_name}")
        except Exception as e:
            logger.error(f"Error processing client reminder {comment['id']}: {e}")
    
    # Process record comments
    for comment in due_record_reminders:
        try:
            client_id = comment.get("client_id")
            record_id = comment.get("record_id")
            
            # Try to get client info, fallback to record data
            client = await db.clients.find_one({"id": client_id}, {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}) if client_id else None
            
            if client:
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}"
                client_phone = client.get("phone", "")
            else:
                # Fallback: get phone from the record
                record = await db.user_records.find_one({"id": record_id}, {"_id": 0, "phone": 1, "client_name": 1}) if record_id else None
                client_name = record.get("client_name", "Cliente") if record else "Cliente"
                client_phone = record.get("phone", "") if record else ""
            
            # Build link with owner_filter=all to ensure client is found
            link = f"/clients?search={client_phone}&owner_filter=all" if client_phone else "/clients?owner_filter=all"
            
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": comment["user_id"],
                "title": f"📝 Recordatorio: {client_name}",
                "message": comment['comment'][:100] + ('...' if len(comment['comment']) > 100 else ''),
                "type": "reminder",
                "link": link,
                "client_id": client_id,
                "is_read": False,
                "created_at": now_iso
            }
            await db.notifications.insert_one(notif_doc)
            
            await db.record_comments.update_one(
                {"id": comment["id"]},
                {"$set": {"reminder_sent": True}}
            )
            
            logger.info(f"Record reminder notification sent for comment {comment['id']} - {client_name}")
        except Exception as e:
            logger.error(f"Error processing record reminder {comment['id']}: {e}")
    
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
            client = await db.clients.find_one({"id": appt["client_id"]}, {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1})
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
            client_phone = client.get("phone", "") if client else ""
            
            # Get dealer info
            dealer_name = appt.get("dealer", "")
            
            # Create notification for the salesperson who created the appointment
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": appt["salesperson_id"],
                "title": f"📅 Cita mañana: {client_name}",
                "message": f"A las {appt.get('time', '')} en {dealer_name}",
                "type": "appointment_reminder",
                "link": "/agenda",
                "client_id": appt["client_id"],
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
    # Sold status
    is_sold: Optional[bool] = None
    sold_at: Optional[str] = None
    # Employment fields from prequalification
    employments: Optional[List[Dict[str, Any]]] = None
    employer_name: Optional[str] = None
    employer_phone: Optional[str] = None
    employment_type: Optional[str] = None
    income_type: Optional[str] = None
    net_income: Optional[str] = None
    income_frequency: Optional[str] = None
    time_with_employer_years: Optional[Any] = None
    time_with_employer_months: Optional[Any] = None

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
    try:
        return safe_hash_password(password)
    except ValueError:
        raise HTTPException(422, 'Password must contain 1 to 72 valid UTF-8 bytes') from None


session_auth = SessionAuth(db, JWT_SECRET, hours=JWT_EXPIRATION_HOURS)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await session_auth.current_user(credentials.credentials)

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
    return await session_auth.login(credentials.email, credentials.password)

class Reauthentication(BaseModel):
    password: str

@api_router.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await session_auth.logout(credentials.credentials)

@api_router.post("/auth/reauthenticate")
async def reauthenticate(body: Reauthentication, credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await session_auth.reauthenticate(credentials.credentials, body.password)

@api_router.get("/auth/passkeys/options")
async def get_passkey_options():
    return passkey_options()

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
        {"$set": {"is_active": data.is_active, "approved": data.is_active}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {'activated' if data.is_active else 'deactivated'} successfully"}

@api_router.put("/users/role")
async def update_user_role(data: UserRoleUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Valid roles: admin, bdc_manager, telemarketer (previously salesperson), demo
    valid_roles = ["admin", "bdc_manager", "telemarketer", "salesperson", "demo"]  # Keep salesperson for backwards compatibility
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

# Model for admin user creation
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    role: str = "telemarketer"
    is_active: bool = True

@api_router.post("/users/create", response_model=dict)
async def admin_create_user(user_data: AdminUserCreate, current_user: dict = Depends(get_current_user)):
    """Create a new user directly - Admin only"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    valid_roles = ["admin", "bdc_manager", "telemarketer", "salesperson"]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "phone": user_data.phone,
        "is_active": user_data.is_active,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    await db.users.insert_one(user_doc)
    
    logger.info(f"Admin {current_user['email']} created user: {user_data.email} with role {user_data.role}")
    
    return {
        "message": f"Usuario '{user_data.name}' creado exitosamente",
        "user": {k: v for k, v in user_doc.items() if k != "password" and k != "_id"}
    }

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
    access = CRMAccess(db, current_user)
    normalized_phone = normalize_phone_number(client.phone)
    
    # Check for existing client by phone (check both original and normalized)
    existing = await db.clients.find_one(await access.query("clients", {
        "$or": [
            {"phone": normalized_phone},
            {"phone": client.phone}
        ],
        "is_deleted": {"$ne": True}
    }, "read"))
    
    if existing:
        # If client exists and belongs to someone else, return info to create a request
        if existing.get("created_by") != current_user["id"]:
            owner = await db.users.find_one({"id": existing.get("created_by")}, {"_id": 0, "name": 1})
            owner_name = owner.get("name", "otro usuario") if owner else "otro usuario"
            return {
                "error": "client_exists_other_user",
                "message": f"Este cliente ya existe y pertenece a {owner_name}",
                "client_id": existing.get("id"),
                "owner_id": existing.get("created_by"),
                "owner_name": owner_name,
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
async def get_clients(include_deleted: bool = False, search: Optional[str] = None, salesperson_id: Optional[str] = None, exclude_sold: bool = False, owner_filter: Optional[str] = None, sort_by: Optional[str] = None, from_notification: bool = False, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    query = {} if include_deleted and current_user["role"] == "admin" else {"is_deleted": {"$ne": True}}
    
    if salesperson_id:
        query["created_by"] = salesperson_id
    if owner_filter == "mine":
        query["created_by"] = current_user["id"]
    elif owner_filter == "others":
        query["created_by"] = {"$ne": current_user["id"]}

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
    
    clients = await db.clients.find(await access.query("clients", query, "read"), {"_id": 0}).sort(sort_field).to_list(1000)
    
    now = datetime.now(timezone.utc)
    
    # For each client, get the last record date, sold count, and status color
    for client in clients:
        last_record = await db.user_records.find_one(
            await access.query("user_records", {"client_id": client["id"], "is_deleted": {"$ne": True}}, "read"),
            {"_id": 0, "created_at": 1},
            sort=[("created_at", -1)]
        )
        client["last_record_date"] = last_record["created_at"] if last_record else None
        
        # Count sold records (record_status = 'completed' indicates a completed sale)
        sold_count = await db.user_records.count_documents(await access.query("user_records", {
            "client_id": client["id"],
            "is_deleted": {"$ne": True},
            "record_status": "completed"
        }, "read"))
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
    
    return [await redact_documents(db, current_user, client) for client in clients]

@api_router.get("/clients/sold/list", response_model=List[dict])
async def get_sold_clients(search: Optional[str] = None, salesperson_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Get clients that have been marked as sold"""
    access = CRMAccess(db, current_user)
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
    
    clients = await db.clients.find(await access.query("clients", query, "read"), {"_id": 0}).sort("sold_at", -1).to_list(1000)
    
    # For each client, get the sold record info
    for client in clients:
        sold_record = await db.user_records.find_one(
            await access.query("user_records", {"client_id": client["id"], "is_deleted": {"$ne": True}, "record_status": "completed"}, "read"),
            {"_id": 0, "finance_status": 1, "bank": 1, "auto": 1, "updated_at": 1}
        )
        if sold_record:
            client["sold_record"] = sold_record
    
    return [await redact_documents(db, current_user, client) for client in clients]

@api_router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Hide sensitive fields from non-admin users
    if current_user["role"] != "admin":
        client.pop("id_number", None)
        client.pop("ssn", None)
    
    return await redact_documents(db, current_user, client)

@api_router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(client_id: str, client: ClientCreate, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    update_data = client.model_dump(exclude_unset=True)
    update_data["last_contact"] = datetime.now(timezone.utc).isoformat()
    
    # Restrict sensitive fields to admin only
    if current_user["role"] != "admin":
        update_data.pop("id_number", None)
        update_data.pop("ssn", None)
    
    # Normalize phone number if provided
    if "phone" in update_data and update_data["phone"]:
        update_data["phone"] = normalize_phone_number(update_data["phone"])
    
    result = await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    
    # Hide sensitive fields from non-admin users
    if current_user["role"] != "admin":
        updated.pop("id_number", None)
        updated.pop("ssn", None)
    
    return await redact_documents(db, current_user, updated)



async def require_document_access(client, current_user, action="read"):
    if not await can_access_documents(db, current_user, client, action):
        raise HTTPException(status_code=403, detail="Document access denied")


@api_router.put("/clients/{client_id}/documents")
async def update_client_documents(client_id: str, id_uploaded: bool = None, income_proof_uploaded: bool = None, residence_proof_uploaded: bool = None, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    await require_document_access(client, current_user, "write")
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
        await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": update_data})
    
    updated = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
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
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple documents for a client (ID, income proof, or residence proof)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    
    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be 'id', 'income', or 'residence'")
    
    # Verify client exists
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await require_document_access(client, current_user, "write")
    
    # Validate the entire batch before creating directories or writing bytes.
    validated = await validate_documents(files)
    client_upload_dir = upload_directory(UPLOAD_DIR, client_id)
    client_upload_dir.mkdir(parents=True, exist_ok=True)
    doc_field = f"{doc_type}_documents"
    existing_docs = client.get(doc_field, [])
    uploaded_files = []
    written_paths = []
    try:
        for item in validated:
            file_id = uuid.uuid4().hex
            file_path = client_upload_dir / f"{doc_type}_{file_id}.{item['extension']}"
            with file_path.open('xb') as destination:
                written_paths.append(file_path)
                destination.write(item['content'])
            uploaded_files.append({
                "id": file_id, "filename": item['filename'], "path": str(file_path),
                "type": item['type'], "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "uploaded_by": current_user["id"]
            })
    except OSError:
        for path in written_paths:
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unable to store document batch")

    # Update client with new documents
    all_docs = existing_docs + uploaded_files
    
    # Build update data
    update_data = {doc_field: all_docs}
    if doc_type == 'id':
        update_data["id_uploaded"] = True
    else:
        update_data[f"{doc_type}_proof_uploaded"] = True
    
    await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": update_data})
    
    return {
        "message": f"{len(uploaded_files)} documento(s) subido(s) correctamente",
        "files": uploaded_files,
        "total_documents": len(all_docs)
    }

@api_router.get("/clients/{client_id}/documents/list/{doc_type}")
async def list_client_documents(
    client_id: str,
    doc_type: str,
    current_user: dict = Depends(get_current_user)
):
    """List all documents of a specific type for a client"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await require_document_access(client, current_user, "read")
    
    doc_field = f"{doc_type}_documents"
    documents = client.get(doc_field, [])
    
    # Also check legacy single file
    legacy_field = f"{doc_type}_file_url" if doc_type == 'id' else f"{doc_type}_proof_file_url"
    legacy_file = client.get(legacy_field)
    
    if legacy_file and not documents:
        # Convert legacy single file to new format
        documents = [{
            "id": "legacy",
            "filename": f"{doc_type}_document",
            "path": legacy_file,
            "type": "application/pdf",
            "uploaded_at": client.get("created_at", ""),
            "uploaded_by": client.get("created_by", "")
        }]
    
    return {"documents": documents, "count": len(documents)}

@api_router.delete("/clients/{client_id}/documents/{doc_type}/{doc_id}")
async def delete_single_document(
    client_id: str,
    doc_type: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a single document from a client"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await require_document_access(client, current_user, "delete")
    
    doc_field = f"{doc_type}_documents"
    documents = client.get(doc_field, [])
    
    # Find and remove the document
    new_docs = [d for d in documents if d.get("id") != doc_id]
    
    if len(new_docs) == len(documents):
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete the file from disk
    for doc in documents:
        if doc.get("id") == doc_id:
            try:
                file_path = resolve_document_path(doc.get("path"), UPLOAD_DIR)
                if file_path is not None:
                    file_path.unlink()
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
    
    # Update client
    update_data = {doc_field: new_docs}
    if len(new_docs) == 0:
        uploaded_field = f"{doc_type}_uploaded" if doc_type == 'id' else f"{doc_type}_proof_uploaded"
        update_data[uploaded_field] = False
    
    await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": update_data})
    
    return {"message": "Documento eliminado", "remaining": len(new_docs)}

@api_router.get("/clients/{client_id}/documents/download/{doc_type}")
async def download_client_document(
    client_id: str,
    doc_type: str,
    doc_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Download a client document - single file or combined PDF of all documents"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    def find_file(path_str):
        return resolve_document_path(path_str, UPLOAD_DIR)

    if doc_type not in ['id', 'income', 'residence']:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await require_document_access(client, current_user, "read")
    
    from PIL import Image as PILImage
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as pdf_canvas
    import io

    # Check new multi-document structure first
    doc_field = f"{doc_type}_documents"
    documents = client.get(doc_field, [])
    
    # If requesting specific document
    if doc_id and documents:
        doc = next((d for d in documents if d.get("id") == doc_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = find_file(doc.get("path", ""))
        if not file_path:
            raise HTTPException(status_code=404, detail="Document file not found")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        file_ext = file_path.suffix.lower()
        content_type = 'application/pdf' if file_ext == '.pdf' else f'image/{file_ext[1:]}'
        
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={doc.get('filename', 'document')}"}
        )
    
    # If multiple documents exist, combine them into one PDF
    if documents and len(documents) > 0:
        pdf_writer = PdfWriter()
        
        for doc in documents:
            file_path = find_file(doc.get("path", ""))
            if not file_path:
                logger.warning(f"Skipping document {doc.get('id')} - file not found at {doc.get('path')}")
                continue
            
            file_ext = file_path.suffix.lower()
            
            try:
                if file_ext == '.pdf':
                    # Add PDF pages directly
                    pdf_reader = PdfReader(str(file_path))
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                else:
                    # Convert image to PDF page
                    img = PILImage.open(file_path)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Create PDF page with image
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PDF')
                    img_buffer.seek(0)
                    
                    img_pdf = PdfReader(img_buffer)
                    pdf_writer.add_page(img_pdf.pages[0])
            except Exception as e:
                logger.error(f"Error processing document {doc.get('id')}: {e}")
                continue
        
        if len(pdf_writer.pages) == 0:
            raise HTTPException(status_code=404, detail="No valid documents found")
        
        # Write combined PDF
        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        
        safe_filename = f"{client.get('first_name', 'client')}_{client.get('last_name', 'doc')}_{doc_type}_combined.pdf".replace(' ', '_')
        
        return Response(
            content=output.read(),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )
    
    # Fallback to legacy single file
    if doc_type == 'id':
        file_url_field = "id_file_url"
    elif doc_type == 'income':
        file_url_field = "income_proof_file_url"
    else:
        file_url_field = "residence_proof_file_url"
    
    file_url = client.get(file_url_field)
    if not file_url:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = find_file(file_url)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Document file not found")

    with open(file_path, 'rb') as f:
        content = f.read()
    
    file_ext = file_path.suffix.lower()
    content_type = 'application/pdf'
    if file_ext in ['.jpg', '.jpeg']:
        content_type = 'image/jpeg'
    elif file_ext == '.png':
        content_type = 'image/png'
    elif file_ext == '.webp':
        content_type = 'image/webp'
    
    safe_filename = f"{client.get('first_name', 'client')}_{client.get('last_name', 'doc')}_{doc_type}{file_ext}".replace(' ', '_')
    
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )

# ==================== USER RECORDS (CARTILLAS) ROUTES ====================

@api_router.post("/user-records", response_model=dict)
async def create_user_record(record: UserRecordCreate, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    await access.require("clients", record.client_id, "write")
    if record.previous_record_id:
        await access.same_client("user_records", record.previous_record_id, record.client_id)
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if this is the first record for this client
    existing_records_count = await db.user_records.count_documents(await access.query("user_records", {"client_id": record.client_id, "is_deleted": {"$ne": True}}, "read"))
    is_first_record = existing_records_count == 0
    
    # Calculate opportunity number
    opportunity_number = 1
    if record.previous_record_id:
        # This is a "New Opportunity" - count previous opportunities
        prev_record = await db.user_records.find_one(await access.query("user_records", {"id": record.previous_record_id}, "read"))
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
    await db.clients.update_one(await access.query("clients", {"id": record.client_id}, "write"), {"$set": {"last_record_date": now}})
    
    # Send automatic SMS if this is the first record for the client
    sms_sent = False
    if is_first_record and twilio_client:
        client = await db.clients.find_one(await access.query("clients", {"id": record.client_id}, "read"), {"_id": 0})
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
                await db.user_records.update_one(await access.query("user_records", {"id": record_doc["id"]}, "write"), {"$set": {"first_sms_sent": True}})
                logger.info(f"Automatic welcome SMS sent to {client['phone']} for first record")
    
    del record_doc["_id"]
    record_doc["auto_sms_sent"] = sms_sent
    return record_doc

@api_router.get("/user-records", response_model=List[dict])
async def get_user_records(client_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    query = {"is_deleted": {"$ne": True}}
    if client_id:
        query["client_id"] = client_id
    records = await db.user_records.find(await access.query("user_records", query, "read"), {"_id": 0}).sort("created_at", -1).to_list(1000)
    return records

@api_router.get("/user-records/{record_id}", response_model=UserRecordResponse)
async def get_user_record(record_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "read")
    record = await db.user_records.find_one(await access.query("user_records", {"id": record_id}, "read"), {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="User record not found")
    return record

@api_router.put("/user-records/{record_id}", response_model=UserRecordResponse)
async def update_user_record(record_id: str, record_data: dict, current_user: dict = Depends(get_current_user)):
    # Clean the data - convert empty strings to None for numeric fields
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
    original = await access.require("user_records", record_id, "write")
    allowed_fields = set(UserRecordCreate.model_fields) - {"previous_record_id", "collaborator_id", "collaborator_name"}
    if set(record_data) - allowed_fields:
        raise HTTPException(status_code=400, detail="Unsupported record fields")
    if record_data.get("client_id") != original.get("client_id"):
        raise HTTPException(status_code=400, detail="Record client cannot be changed")
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
    
    result = await db.user_records.update_one(await access.query("user_records", {"id": record_id}, "write"), {"$set": cleaned_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User record not found")
    
    # Update client last_contact
    client_update = {"last_contact": datetime.now(timezone.utc).isoformat()}
    
    # If record is marked as completed (sold), mark the client as sold too
    if cleaned_data.get("record_status") == "completed":
        client_update["is_sold"] = True
        client_update["sold_at"] = datetime.now(timezone.utc).isoformat()
    elif "record_status" in cleaned_data and cleaned_data.get("record_status") != "completed":
        # Check if client has any OTHER completed records before removing is_sold
        other_completed = await db.user_records.count_documents(await access.query("user_records", {
            "client_id": client_id,
            "id": {"$ne": record_id},  # Exclude current record being updated
            "record_status": "completed",
            "is_deleted": {"$ne": True}
        }, "read"))
        if other_completed == 0:
            # No other completed records, remove sold status
            client_update["is_sold"] = False
            client_update["sold_at"] = None
    
    await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": client_update})
    
    updated = await db.user_records.find_one(await access.query("user_records", {"id": record_id}, "read"), {"_id": 0})
    
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
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
    if permanent:
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        await db.user_records.delete_one(await access.query("user_records", {"id": record_id}, "write"))
    else:
        await db.user_records.update_one(await access.query("user_records", {"id": record_id}, "write"), {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "User record deleted"}

# ==================== RECORD COMMENTS/NOTES ====================

@api_router.get("/user-records/{record_id}/comments")
async def get_record_comments(record_id: str, current_user: dict = Depends(get_current_user)):
    """Get all comments for a user record"""
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "read")
    # Build query - if not admin, exclude admin_only comments
    query = {"record_id": record_id}
    if current_user["role"] != "admin":
        query["admin_only"] = {"$ne": True}
    
    comments = await db.record_comments.find(
        await access.query("record_comments", query, "read"),
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return comments

@api_router.post("/user-records/{record_id}/comments")
async def add_record_comment(record_id: str, comment: str = Form(...), reminder_at: Optional[str] = Form(None), current_user: dict = Depends(get_current_user)):
    """Add a comment to a user record, optionally with a reminder.
    If reminder is less than 24 hours away, create notification immediately.
    """
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Get the record to find the client and phone
    record = await db.user_records.find_one(await access.query("user_records", {"id": record_id}, "read"), {"_id": 0, "client_id": 1, "phone": 1, "client_name": 1})
    client_id = record.get("client_id") if record else None
    record_phone = record.get("phone", "") if record else ""
    record_client_name = record.get("client_name", "") if record else ""
    
    # Check if reminder should trigger immediate notification
    send_notification_now = False
    if reminder_at:
        try:
            reminder_datetime = datetime.fromisoformat(reminder_at.replace("Z", "+00:00"))
            if reminder_datetime.tzinfo is None:
                reminder_datetime = reminder_datetime.replace(tzinfo=timezone.utc)
            
            time_until_reminder = reminder_datetime - now
            # If reminder is within 24 hours (or in the past), send notification immediately
            if time_until_reminder.total_seconds() <= 86400:
                send_notification_now = True
        except Exception as e:
            logger.error(f"Error parsing reminder_at: {e}")
    
    comment_doc = {
        "id": str(uuid.uuid4()),
        "record_id": record_id,
        "client_id": client_id,
        "comment": comment,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", current_user.get("email", "Unknown")),
        "created_at": now_iso,
        "reminder_at": reminder_at,
        "reminder_sent": send_notification_now
    }
    await db.record_comments.insert_one(comment_doc)
    
    # If reminder is within 24 hours, create notification immediately
    notification_created = False
    if send_notification_now:
        try:
            # Get client info for the notification - try from clients collection first, then from record
            client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}) if client_id else None
            
            if client:
                client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}"
                client_phone = client.get("phone", "")
            else:
                # Fallback to record data
                client_name = record_client_name or "Cliente"
                client_phone = record_phone
            
            # Build link - use phone for search, add owner_filter=all to ensure client is found
            link = f"/clients?search={client_phone}&owner_filter=all" if client_phone else "/clients?owner_filter=all"
            
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": current_user["id"],
                "title": f"📝 Recordatorio: {client_name}",
                "message": comment[:100] + ('...' if len(comment) > 100 else ''),
                "type": "reminder",
                "link": link,
                "client_id": client_id,
                "is_read": False,
                "created_at": now_iso
            }
            await db.notifications.insert_one(notif_doc)
            notification_created = True
            logger.info(f"Immediate reminder notification created for record {record_id}")
        except Exception as e:
            logger.error(f"Error creating immediate notification: {e}")
    
    result = {k: v for k, v in comment_doc.items() if k != "_id"}
    result["notification_created"] = notification_created
    return result

@api_router.delete("/user-records/{record_id}/comments/{comment_id}")
async def delete_record_comment(record_id: str, comment_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a comment (only admin can delete)"""
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete comments")
    
    comment = await db.record_comments.find_one(await access.query("record_comments", {"id": comment_id, "record_id": record_id}, "read"))
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    await db.record_comments.delete_one(await access.query("record_comments", {"id": comment_id}, "write"))
    return {"message": "Comment deleted"}

# ==================== CLIENT COMMENTS/NOTES ROUTES ====================

@api_router.get("/clients/{client_id}/comments")
async def get_client_comments(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get all comments/notes for a client"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    comments = await db.client_comments.find(
        await access.query("client_comments", {"client_id": client_id}, "read"),
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return comments

@api_router.post("/clients/{client_id}/comments")
async def add_client_comment(client_id: str, comment: str = Form(...), reminder_at: Optional[str] = Form(None), current_user: dict = Depends(get_current_user)):
    """Add a comment/note to a client, optionally with a reminder.
    If reminder is less than 24 hours away, create notification immediately.
    """
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Check if reminder should trigger immediate notification
    send_notification_now = False
    if reminder_at:
        try:
            reminder_datetime = datetime.fromisoformat(reminder_at.replace("Z", "+00:00"))
            # If reminder is timezone-naive, assume UTC
            if reminder_datetime.tzinfo is None:
                reminder_datetime = reminder_datetime.replace(tzinfo=timezone.utc)
            
            time_until_reminder = reminder_datetime - now
            # If reminder is within 24 hours (or in the past), send notification immediately
            if time_until_reminder.total_seconds() <= 86400:  # 24 hours in seconds
                send_notification_now = True
        except Exception as e:
            logger.error(f"Error parsing reminder_at: {e}")
    
    comment_doc = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "comment": comment,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", current_user.get("email", "Unknown")),
        "created_at": now_iso,
        "reminder_at": reminder_at,  # ISO datetime string for when to remind
        "reminder_sent": send_notification_now  # Mark as sent if we're sending now
    }
    await db.client_comments.insert_one(comment_doc)
    
    # If reminder is within 24 hours, create notification immediately
    notification_created = False
    if send_notification_now:
        try:
            # Get client info for the notification
            client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1})
            client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}" if client else "Cliente"
            client_phone = client.get("phone", "") if client else ""
            
            # Build link with owner_filter=all to ensure client is found regardless of filter
            link = f"/clients?search={client_phone}&owner_filter=all" if client_phone else "/clients?owner_filter=all"
            
            notif_doc = {
                "id": str(uuid.uuid4()),
                "user_id": current_user["id"],
                "title": f"📝 Recordatorio: {client_name}",
                "message": comment[:100] + ('...' if len(comment) > 100 else ''),
                "type": "reminder",
                "link": link,
                "client_id": client_id,
                "is_read": False,
                "created_at": now_iso
            }
            await db.notifications.insert_one(notif_doc)
            notification_created = True
            logger.info(f"Immediate reminder notification created for client {client_id}")
        except Exception as e:
            logger.error(f"Error creating immediate notification: {e}")
    
    result = {k: v for k, v in comment_doc.items() if k != "_id"}
    result["notification_created"] = notification_created
    return result

@api_router.delete("/clients/{client_id}/comments/{comment_id}")
async def delete_client_comment(client_id: str, comment_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client comment (only admin can delete)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete comments")
    
    comment = await db.client_comments.find_one(await access.query("client_comments", {"id": comment_id, "client_id": client_id}, "read"))
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    await db.client_comments.delete_one(await access.query("client_comments", {"id": comment_id}, "write"))
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
    access = CRMAccess(db, current_user)
    await access.require("clients", request.client_id)
    await access.same_client("user_records", request.record_id, request.client_id, "read")
    if request.include_documents or request.attach_documents:
        await require_document_access(await access.require("clients", request.client_id), current_user)
    return mock_delivery("email")
    
    # Get record data
    record = await db.user_records.find_one(await access.query("user_records", {"id": request.record_id}, "read"), {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Get client data
    client = await db.clients.find_one(await access.query("clients", {"id": request.client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if request.include_documents or request.attach_documents:
        await require_document_access(client, current_user)
    
    # Get co-signers for this client
    cosigner_relations = await db.cosigner_relations.find(
        await access.query("cosigner_relations", {"buyer_client_id": request.client_id, "is_deleted": {"$ne": True}}, "read"),
        {"_id": 0}
    ).to_list(10)
    
    cosigners_data = []
    for relation in cosigner_relations:
        cosigner = await db.clients.find_one(await access.query("clients", {"id": relation.get("cosigner_client_id")}, "read"), {"_id": 0})
        if cosigner:
            if request.include_documents or request.attach_documents:
                await require_document_access(cosigner, current_user)
            # Get co-signer's records
            cosigner_records = await db.user_records.find(
                await access.query("user_records", {"client_id": cosigner.get("id"), "is_deleted": {"$ne": True}}, "read"),
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
.badge-info {{ background: #dbeafe; color: #1e40af; }}
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
"""
    
    # Add date of birth if available
    if client.get('date_of_birth'):
        email_body += f'<div class="info-row"><span class="label">Fecha de Nacimiento:</span> <span class="value">{client.get("date_of_birth")}</span></div>'
    
    # Add address
    address_parts = [client.get('address', '')]
    if client.get('apartment'):
        address_parts.append(f"Apt {client.get('apartment')}")
    email_body += f'<div class="info-row"><span class="label">Dirección:</span> <span class="value">{" ".join(address_parts) if any(address_parts) else "N/A"}</span></div>'
    
    # Add housing info if available
    if client.get('housing_type'):
        housing_info = client.get('housing_type')
        if client.get('rent_amount'):
            housing_info += f" (${client.get('rent_amount')}/mes)"
        email_body += f'<div class="info-row"><span class="label">Vivienda:</span> <span class="value">{housing_info}</span></div>'
    
    # Add time at address if available
    if client.get('time_at_address_years') is not None or client.get('time_at_address_months') is not None:
        years = client.get('time_at_address_years', 0) or 0
        months = client.get('time_at_address_months', 0) or 0
        email_body += f'<div class="info-row"><span class="label">Tiempo en Dirección:</span> <span class="value">{years} años, {months} meses</span></div>'
    
    email_body += '</div>'
    
    # Client ID Information Section
    email_body += """
<div class="section">
<div class="section-title">🪪 Identificación del Cliente</div>
"""
    if client.get('id_type'):
        email_body += f'<div class="info-row"><span class="label">Tipo de ID:</span> <span class="value">{client.get("id_type")}</span></div>'
    if client.get('id_number'):
        email_body += f'<div class="info-row"><span class="label">Número de ID:</span> <span class="value">{client.get("id_number")}</span></div>'
    if client.get('ssn_type'):
        email_body += f'<div class="info-row"><span class="label">Tipo SSN/ITIN:</span> <span class="value">{client.get("ssn_type")}</span></div>'
    if client.get('ssn'):
        # Only show last 4 digits for security
        ssn_value = client.get('ssn')
        if len(ssn_value) > 4:
            ssn_value = "***-**-" + ssn_value[-4:]
        email_body += f'<div class="info-row"><span class="label">SSN/ITIN:</span> <span class="value">{ssn_value}</span></div>'
    
    email_body += '</div>'
    
    # Record Documentation Section
    email_body += """
<div class="section">
<div class="section-title">📄 Documentación del Record</div>
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
            attachments = collect_document_attachments(client, cosigners_data, UPLOAD_DIR)

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
                    logger.warning("Unable to read a selected document attachment")
            
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
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
    return mock_delivery("email")
    
    record = await db.user_records.find_one(await access.query("user_records", {"id": record_id}, "read"), {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Get client info
    client = await db.clients.find_one(await access.query("clients", {"id": record.get("client_id")}, "read"), {"_id": 0})
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
    access = CRMAccess(db, current_user)
    await access.require("clients", appt.client_id, "write")
    await access.same_client("user_records", appt.user_record_id, appt.client_id)
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
    client = await db.clients.find_one(await access.query("clients", {"id": appt.client_id}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    query = {}
    if salesperson_id:
        query["salesperson_id"] = salesperson_id
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    appointments = await db.appointments.find(await access.query("appointments", query, "read"), {"_id": 0}).sort("date", 1).to_list(1000)
    return appointments

@api_router.get("/appointments/agenda", response_model=List[dict])
async def get_agenda(current_user: dict = Depends(get_current_user)):
    """Get appointments for the agenda view with client info.
    Admins see ALL appointments, others see only their own."""
    access = CRMAccess(db, current_user)
    
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
    appointments = await db.appointments.aggregate([{"$match": await access.scope("appointments")}] + pipeline).to_list(1000)
    
    # Also get reminders (from client_comments and record_comments)
    reminder_match = {"reminder_at": {"$ne": None}}
    if current_user["role"] == "admin":
        pass  # Admin sees all reminders
    elif current_user["role"] == "bdc_manager":
        admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
        admin_ids = [u["id"] for u in admin_users]
        reminder_match["user_id"] = {"$nin": admin_ids}
    else:
        reminder_match["user_id"] = current_user["id"]
    
    # Get client comment reminders
    client_reminders = await db.client_comments.find(await access.query("client_comments", reminder_match, "read"), {"_id": 0}).to_list(500)
    
    # Get record comment reminders
    record_reminders = await db.record_comments.find(await access.query("record_comments", reminder_match, "read"), {"_id": 0}).to_list(500)
    
    # Transform reminders to agenda format
    for reminder in client_reminders + record_reminders:
        client_id = reminder.get("client_id")
        client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}) if client_id else None
        
        # Parse reminder date
        reminder_at = reminder.get("reminder_at", "")
        reminder_date = reminder_at[:10] if reminder_at else ""  # YYYY-MM-DD
        reminder_time = reminder_at[11:16] if len(reminder_at) > 11 else ""  # HH:MM
        
        agenda_item = {
            "id": reminder.get("id"),
            "type": "reminder",  # Mark as reminder, not appointment
            "date": reminder_date,
            "time": reminder_time,
            "client_id": client_id,
            "client": {
                "first_name": client.get("first_name", "") if client else "",
                "last_name": client.get("last_name", "") if client else "",
                "phone": client.get("phone", "") if client else ""
            } if client else None,
            "comment": reminder.get("comment", ""),
            "reminder_sent": reminder.get("reminder_sent", False),
            "salesperson_id": reminder.get("user_id"),
            "salesperson_name": reminder.get("user_name", ""),
            "created_at": reminder.get("created_at")
        }
        appointments.append(agenda_item)
    
    # Sort all items by date and time
    appointments.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
    
    return appointments

@api_router.put("/appointments/{appt_id}", response_model=AppointmentResponse)
async def update_appointment(appt_id: str, appt: AppointmentUpdate, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if appt_id:
        await access.require("appointments", appt_id, "write")
    update_data = appt.model_dump(exclude_unset=True, exclude_none=True)
    
    # Determine status
    existing = await db.appointments.find_one(await access.query("appointments", {"id": appt_id}, "read"))
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appt.change_time and appt.change_time != existing.get("change_time"):
        update_data["status"] = "cambio_hora"
    elif appt.date and appt.time:
        update_data["status"] = "agendado"
    
    await db.appointments.update_one(await access.query("appointments", {"id": appt_id}, "write"), {"$set": update_data})
    updated = await db.appointments.find_one(await access.query("appointments", {"id": appt_id}, "read"), {"_id": 0})
    return updated

@api_router.put("/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, status: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if appt_id:
        await access.require("appointments", appt_id, "write")
    valid_statuses = ["agendado", "sin_configurar", "cambio_hora", "tres_semanas", "no_show", "cumplido"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    await db.appointments.update_one(await access.query("appointments", {"id": appt_id}, "write"), {"$set": {"status": status}})
    return {"message": "Status updated"}

@api_router.delete("/appointments/{appt_id}")
async def delete_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if appt_id:
        await access.require("appointments", appt_id, "write")
    await db.appointments.delete_one(await access.query("appointments", {"id": appt_id}, "write"))
    return {"message": "Appointment deleted"}

# ==================== CO-SIGNER ROUTES ====================

@api_router.post("/cosigners", response_model=CoSignerRelationResponse)
async def create_cosigner_relation(relation: CoSignerRelationCreate, current_user: dict = Depends(get_current_user)):
    # Check if both clients exist
    access = CRMAccess(db, current_user)
    await access.require("clients", relation.buyer_client_id, "write")
    await access.require("clients", relation.cosigner_client_id, "write")
    buyer = await db.clients.find_one(await access.query("clients", {"id": relation.buyer_client_id}, "read"))
    cosigner = await db.clients.find_one(await access.query("clients", {"id": relation.cosigner_client_id}, "read"))
    
    if not buyer or not cosigner:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if relation already exists
    existing = await db.cosigner_relations.find_one(await access.query("cosigner_relations", {
        "buyer_client_id": relation.buyer_client_id,
        "cosigner_client_id": relation.cosigner_client_id
    }, "read"))
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
    access = CRMAccess(db, current_user)
    if buyer_client_id:
        await access.require("clients", buyer_client_id, "read")
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
    relations = await db.cosigner_relations.aggregate([{"$match": await access.scope("cosigner_relations")}] + pipeline).to_list(100)
    for relation in relations:
        if isinstance(relation.get("cosigner"), dict):
            relation["cosigner"] = await redact_documents(db, current_user, relation["cosigner"])
    return relations

@api_router.delete("/cosigners/{relation_id}")
async def delete_cosigner_relation(relation_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if relation_id:
        await access.require("cosigner_relations", relation_id, "write")
    await db.cosigner_relations.delete_one(await access.query("cosigner_relations", {"id": relation_id}, "write"))
    return {"message": "Co-signer relation removed"}

@api_router.get("/clients/search/phone/{phone}")
async def search_client_by_phone(phone: str, current_user: dict = Depends(get_current_user)):
    """Search for a client by phone number (for adding existing co-signer)"""
    access = CRMAccess(db, current_user)
    client = await db.clients.find_one(await access.query("clients", {"phone": {"$regex": re.escape(phone)}, "is_deleted": {"$ne": True}}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await redact_documents(db, current_user, client)

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    period: str = "all",  # "all", "6months", "month", or specific "YYYY-MM"
    month: str = None  # Optional specific month in format "YYYY-MM"
):
    # Get list of admin user IDs (to exclude their data from non-admins)
    access = CRMAccess(db, current_user)
    admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
    admin_ids = [u["id"] for u in admin_users]
    
    # Base query for records/appointments - depends on role
    if current_user["role"] == "admin":
        # Admin sees all data
        base_query = {}
        clients_owner_filter = {}
    elif current_user["role"] == "bdc_manager":
        # BDC Manager sees all data EXCEPT admin data
        base_query = {"salesperson_id": {"$nin": admin_ids}}
        clients_owner_filter = {"created_by": {"$nin": admin_ids}}
    else:
        # Telemarketer only sees their own data
        base_query = {"salesperson_id": current_user["id"]}
        clients_owner_filter = {"created_by": current_user["id"]}
    
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
    
    # Build queries with date filter AND owner filter
    clients_query = {"is_deleted": {"$ne": True}}
    if clients_owner_filter:
        clients_query.update(clients_owner_filter)
    if date_filter:
        clients_query["created_at"] = date_filter
    
    # Total clients (filtered by period and owner)
    total_clients = await db.clients.count_documents(await access.query("clients", clients_query, "read"))
    
    # Total clients overall (for reference) - also filtered by owner
    clients_all_query = {"is_deleted": {"$ne": True}}
    if clients_owner_filter:
        clients_all_query.update(clients_owner_filter)
    total_clients_all = await db.clients.count_documents(await access.query("clients", clients_all_query, "read"))
    
    # New clients this month (always current month for comparison) - also filtered by owner
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_clients_query = {
        "is_deleted": {"$ne": True},
        "created_at": {"$gte": first_of_month.isoformat()}
    }
    if clients_owner_filter:
        new_clients_query.update(clients_owner_filter)
    new_clients_month = await db.clients.count_documents(await access.query("clients", new_clients_query, "read"))
    
    # Appointments query with date filter
    appt_query = {**base_query}
    if date_filter:
        appt_query["created_at"] = date_filter
    
    # Appointments by status
    appt_stats = await db.appointments.aggregate([{"$match": await access.scope("appointments")}] + [
        {"$match": appt_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    appointment_counts = {stat["_id"]: stat["count"] for stat in appt_stats}
    
    # Documents status (not filtered by date - shows current state) - filtered by owner
    docs_query_complete = {"id_uploaded": True, "income_proof_uploaded": True, "is_deleted": {"$ne": True}}
    docs_query_pending = {"$or": [{"id_uploaded": False}, {"income_proof_uploaded": False}], "is_deleted": {"$ne": True}}
    if clients_owner_filter:
        docs_query_complete.update(clients_owner_filter)
        docs_query_pending.update(clients_owner_filter)
    docs_complete = await db.clients.count_documents(await access.query("clients", docs_query_complete, "read"))
    docs_pending = await db.clients.count_documents(await access.query("clients", docs_query_pending, "read"))
    
    # Sales count - now based on is_sold in clients collection (consistent with Sold page)
    # Filtered by owner
    sales_client_query = {"is_sold": True, "is_deleted": {"$ne": True}}
    if clients_owner_filter:
        sales_client_query.update(clients_owner_filter)
    sales_count = await db.clients.count_documents(await access.query("clients", sales_client_query, "read"))
    
    # Sales this month - check sold_at field if exists, otherwise count all sold
    # First try to count clients with sold_at in this month - filtered by owner
    sales_month_query = {
        "is_sold": True, 
        "is_deleted": {"$ne": True},
        "sold_at": {"$gte": first_of_month.isoformat()}
    }
    if clients_owner_filter:
        sales_month_query.update(clients_owner_filter)
    sales_month = await db.clients.count_documents(await access.query("clients", sales_month_query, "read"))
    
    # If no sold_at dates exist, use sales_count as fallback (for backwards compatibility)
    if sales_month == 0 and sales_count > 0:
        # Check if any client has sold_at field
        has_sold_at = await db.clients.count_documents(await access.query("clients", {"is_sold": True, "sold_at": {"$exists": True}}, "read"))
        if has_sold_at == 0:
            # No sold_at dates tracked yet, show all sales as this month's
            sales_month = sales_count
    
    # Today's appointments
    today = now.strftime("%Y-%m-%d")
    today_appointments = await db.appointments.count_documents(await access.query("appointments", {"date": today, **base_query}, "read"))
    
    # This week's appointments
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_end = (now + timedelta(days=6-now.weekday())).strftime("%Y-%m-%d")
    week_appointments = await db.appointments.count_documents(await access.query("appointments", {
        "date": {"$gte": week_start, "$lte": week_end},
        **base_query
    }, "read"))
    
    # Total records with date filter
    records_query = {"is_deleted": {"$ne": True}}
    if base_query:
        records_query.update(base_query)
    if date_filter:
        records_query["created_at"] = date_filter
    total_records = await db.user_records.count_documents(await access.query("user_records", records_query, "read"))
    
    # Co-signers count
    total_cosigners = await db.cosigner_relations.count_documents(await access.query("cosigner_relations", {}, "read"))
    
    # Sold clients count (clients with is_sold = true) - filtered by owner
    sold_clients_query = {"is_sold": True, "is_deleted": {"$ne": True}}
    if clients_owner_filter:
        sold_clients_query.update(clients_owner_filter)
    sold_clients = await db.clients.count_documents(await access.query("clients", sold_clients_query, "read"))
    
    # Recent activity - clients contacted in last 7 days - filtered by owner
    week_ago = (now - timedelta(days=7)).isoformat()
    active_clients_query = {
        "is_deleted": {"$ne": True},
        "last_contact": {"$gte": week_ago}
    }
    if clients_owner_filter:
        active_clients_query.update(clients_owner_filter)
    active_clients = await db.clients.count_documents(await access.query("clients", active_clients_query, "read"))
    
    # Finance type breakdown with date filter
    finance_match = {"finance_status": {"$in": ["financiado", "lease"]}, "is_deleted": {"$ne": True}}
    if date_filter:
        finance_match["created_at"] = date_filter
    finance_stats = await db.user_records.aggregate([{"$match": await access.scope("user_records")}] + [
        {"$match": finance_match},
        {"$group": {"_id": "$finance_status", "count": {"$sum": 1}}}
    ]).to_list(10)
    finance_breakdown = {stat["_id"]: stat["count"] for stat in finance_stats}
    
    # Monthly sales trend (last 6 months or based on period)
    trend_start = now - timedelta(days=180)
    monthly_sales = await db.user_records.aggregate([{"$match": await access.scope("user_records")}] + [
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
    available_months = await db.user_records.aggregate([{"$match": await access.scope("user_records")}] + [
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
        await access.query("user_records", dp_match, "read"),
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


@api_router.get("/dashboard/stats/{stat_type}/details")
async def get_dashboard_stat_details(
    stat_type: str,
    current_user: dict = Depends(get_current_user),
    period: str = "all",
    month: str = None
):
    """Get detailed list of items for a dashboard statistic (clickable stats)"""
    access = CRMAccess(db, current_user)
    # Get admin IDs for role filtering
    admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
    admin_ids = [u["id"] for u in admin_users]
    
    # Build owner filter based on role
    if current_user["role"] == "admin":
        clients_owner_filter = {}
        records_filter = {}
    elif current_user["role"] == "bdc_manager":
        clients_owner_filter = {"created_by": {"$nin": admin_ids}}
        records_filter = {"salesperson_id": {"$nin": admin_ids}}
    else:
        clients_owner_filter = {"created_by": current_user["id"]}
        records_filter = {"salesperson_id": current_user["id"]}
    
    # Calculate date filter
    now = datetime.now(timezone.utc)
    date_filter = {}
    if month:
        year, mon = month.split("-")
        start_date = datetime(int(year), int(mon), 1, tzinfo=timezone.utc)
        if int(mon) == 12:
            end_date = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(int(year), int(mon) + 1, 1, tzinfo=timezone.utc)
        date_filter = {"$gte": start_date.isoformat(), "$lt": end_date.isoformat()}
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"$gte": start_date.isoformat()}
    elif period == "6months":
        start_date = now - timedelta(days=180)
        date_filter = {"$gte": start_date.isoformat()}
    
    result = {"stat_type": stat_type, "items": [], "count": 0}
    
    if stat_type == "total_clients":
        query = {"is_deleted": {"$ne": True}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        if date_filter:
            query["created_at"] = date_filter
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "new_clients_month":
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = {"is_deleted": {"$ne": True}, "created_at": {"$gte": first_of_month.isoformat()}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "sales" or stat_type == "sold_clients":
        query = {"is_sold": True, "is_deleted": {"$ne": True}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "sold_at": 1}
        ).sort("sold_at", -1).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "sales_month":
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = {"is_sold": True, "is_deleted": {"$ne": True}, "sold_at": {"$gte": first_of_month.isoformat()}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "sold_at": 1}
        ).sort("sold_at", -1).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "today_appointments":
        today = now.strftime("%Y-%m-%d")
        query = {"date": today}
        if records_filter:
            query.update(records_filter)
        
        appointments = await db.appointments.find(
            await access.query("appointments", query, "read"),
            {"_id": 0, "id": 1, "client_id": 1, "date": 1, "time": 1, "status": 1, "dealer": 1}
        ).to_list(500)
        
        # Enrich with client names
        for appt in appointments:
            client = await db.clients.find_one(await access.query("clients", {"id": appt.get("client_id")}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
            if client:
                appt["client_name"] = f"{client.get('first_name', '')} {client.get('last_name', '')}"
        
        result["items"] = appointments
        result["count"] = len(appointments)
    
    elif stat_type == "week_appointments":
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        week_end = (now + timedelta(days=6-now.weekday())).strftime("%Y-%m-%d")
        query = {"date": {"$gte": week_start, "$lte": week_end}}
        if records_filter:
            query.update(records_filter)
        
        appointments = await db.appointments.find(
            await access.query("appointments", query, "read"),
            {"_id": 0, "id": 1, "client_id": 1, "date": 1, "time": 1, "status": 1, "dealer": 1}
        ).sort("date", 1).to_list(500)
        
        for appt in appointments:
            client = await db.clients.find_one(await access.query("clients", {"id": appt.get("client_id")}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
            if client:
                appt["client_name"] = f"{client.get('first_name', '')} {client.get('last_name', '')}"
        
        result["items"] = appointments
        result["count"] = len(appointments)
    
    elif stat_type == "total_records":
        query = {"is_deleted": {"$ne": True}}
        if records_filter:
            query.update(records_filter)
        if date_filter:
            query["created_at"] = date_filter
        
        records = await db.user_records.find(
            await access.query("user_records", query, "read"),
            {"_id": 0, "id": 1, "client_id": 1, "record_status": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(500)
        
        for rec in records:
            client = await db.clients.find_one(await access.query("clients", {"id": rec.get("client_id")}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
            if client:
                rec["client_name"] = f"{client.get('first_name', '')} {client.get('last_name', '')}"
        
        result["items"] = records
        result["count"] = len(records)
    
    elif stat_type == "total_cosigners":
        cosigner_relations = await db.cosigner_relations.find(
            await access.query("cosigner_relations", {}, "read"),
            {"_id": 0, "buyer_client_id": 1, "cosigner_client_id": 1}
        ).to_list(500)
        
        items = []
        for rel in cosigner_relations:
            buyer = await db.clients.find_one(await access.query("clients", {"id": rel.get("buyer_client_id")}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
            cosigner = await db.clients.find_one(await access.query("clients", {"id": rel.get("cosigner_client_id")}, "read"), {"_id": 0, "first_name": 1, "last_name": 1})
            items.append({
                "buyer_name": f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}" if buyer else "N/A",
                "cosigner_name": f"{cosigner.get('first_name', '')} {cosigner.get('last_name', '')}" if cosigner else "N/A",
                "buyer_client_id": rel.get("buyer_client_id"),
                "cosigner_client_id": rel.get("cosigner_client_id")
            })
        
        result["items"] = items
        result["count"] = len(items)
    
    elif stat_type == "active_clients":
        week_ago = (now - timedelta(days=7)).isoformat()
        query = {"is_deleted": {"$ne": True}, "last_contact": {"$gte": week_ago}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "last_contact": 1}
        ).sort("last_contact", -1).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "docs_complete":
        query = {"id_uploaded": True, "income_proof_uploaded": True, "is_deleted": {"$ne": True}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1}
        ).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    elif stat_type == "docs_pending":
        query = {"$or": [{"id_uploaded": False}, {"income_proof_uploaded": False}], "is_deleted": {"$ne": True}}
        if clients_owner_filter:
            query.update(clients_owner_filter)
        
        clients = await db.clients.find(
            await access.query("clients", query, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1, "id_uploaded": 1, "income_proof_uploaded": 1}
        ).to_list(500)
        result["items"] = clients
        result["count"] = len(clients)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown stat type: {stat_type}")
    
    return result

@api_router.get("/dashboard/salesperson-performance")
async def get_salesperson_performance(
    current_user: dict = Depends(get_current_user),
    period: str = "all",  # "all", "6months", "month"
    month: str = None  # Optional specific month in format "YYYY-MM"
):
    # Admin and BDC Manager can see salesperson performance
    access = CRMAccess(db, current_user)
    if current_user["role"] not in ["admin", "bdc", "bdc_manager"]:
        raise HTTPException(status_code=403, detail="Admin or BDC Manager access required")
    
    # Get admin IDs to filter them out for BDC Managers
    admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
    admin_ids = [u["id"] for u in admin_users]
    
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
    
    # Build match filter based on role and date
    match_filter = {"is_deleted": {"$ne": True}}
    if current_user["role"] == "bdc_manager":
        # BDC Manager should NOT see admin performance
        match_filter["salesperson_id"] = {"$nin": admin_ids}
    if date_filter:
        match_filter["created_at"] = date_filter
    
    # Build appointment match filter for the lookup
    appt_match_filter = {}
    if date_filter:
        appt_match_filter["created_at"] = date_filter
    
    pipeline = [
        {"$match": match_filter},
        {"$group": {
            "_id": "$salesperson_id",
            "salesperson_name": {"$first": "$salesperson_name"},
            "total_records": {"$sum": 1},
            "sales": {"$sum": {"$cond": [{"$eq": ["$record_status", "completed"]}, 1, 0]}}
        }},
        {"$lookup": {
            "from": "appointments",
            "let": {"sp_id": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$salesperson_id", "$$sp_id"]},
                    **({"created_at": date_filter} if date_filter else {})
                }}
            ],
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
        }},
        {"$sort": {"total_records": -1}}  # Sort by total records descending
    ]
    
    performance = await db.user_records.aggregate([{"$match": await access.scope("user_records")}] + pipeline).to_list(100)
    return performance

# ==================== TRASH ROUTES (ADMIN) ====================

@api_router.get("/trash/clients", response_model=List[ClientResponse])
async def get_trash_clients(current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    clients = await db.clients.find(await access.query("clients", {"is_deleted": True}, "read"), {"_id": 0}).to_list(1000)
    return [await redact_documents(db, current_user, client) for client in clients]

@api_router.get("/trash/user-records", response_model=List[UserRecordResponse])
async def get_trash_user_records(current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    records = await db.user_records.find(await access.query("user_records", {"is_deleted": True}, "read"), {"_id": 0}).to_list(1000)
    return records

# ==================== SMS ROUTES (TWILIO) ====================

async def send_sms_twilio(to_phone: str, message: str) -> dict:
    """V2 development communication boundary: no external delivery."""
    return mock_delivery("sms")

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
    raise HTTPException(status_code=403, detail="Public document access is disabled")

@api_router.post("/email/send-documents-link")
async def send_documents_email(client_id: str, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=403, detail="Public document access is disabled")

@api_router.post("/sms/send-appointment-link")
async def send_appointment_sms(client_id: str, appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Send SMS with appointment scheduling/management link"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if appointment_id:
        await access.require("appointments", appointment_id, "write")
    await access.same_client("appointments", appointment_id, client_id)
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    appointment = await db.appointments.find_one(await access.query("appointments", {"id": appointment_id}, "read"), {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Generate public link token
    token = await create_public_link(client_id, appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one(await access.query("appointments", {"id": appointment_id}, "write"), {"$set": {"public_token": token}})
    
    # Get base URL from environment or use default
    base_url = os.environ.get('FRONTEND_URL', '')
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
        await access.query("appointments", {"id": appointment_id}, "write"),
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if appointment_id:
        await access.require("appointments", appointment_id, "write")
    await access.same_client("appointments", appointment_id, client_id)
    return mock_delivery("email")
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.get("email"):
        raise HTTPException(status_code=400, detail="El cliente no tiene email registrado")
    
    appointment = await db.appointments.find_one(await access.query("appointments", {"id": appointment_id}, "read"), {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Generate public link token
    token = await create_public_link(client_id, appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one(await access.query("appointments", {"id": appointment_id}, "write"), {"$set": {"public_token": token}})
    
    # Get base URL
    base_url = os.environ.get('FRONTEND_URL', '')
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
            await access.query("appointments", {"id": appointment_id}, "write"),
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if record_id:
        await access.require("user_records", record_id, "write")
    await access.same_client("user_records", record_id, client_id)
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    record = await db.user_records.find_one(await access.query("user_records", {"id": record_id}, "read"), {"_id": 0})
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
        await access.query("user_records", {"id": record_id}, "write"),
        {"$set": {"last_reminder_sent": datetime.now(timezone.utc).isoformat()}}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")
    
    return {"message": "Reminder SMS sent successfully", "phone": client["phone"], "twilio_sid": result.get("sid")}

@api_router.post("/sms/process-weekly-reminders")
async def process_weekly_reminders(current_user: dict = Depends(get_current_user)):
    """Process and send weekly reminders for all pending records (admin only or scheduled task)"""
    access = CRMAccess(db, current_user)
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
    
    records = await db.user_records.find(await access.query("user_records", query, "read"), {"_id": 0}).to_list(500)
    
    sent_count = 0
    skipped_count = 0
    errors = []
    
    for record in records:
        try:
            client = await db.clients.find_one(await access.query("clients", {"id": record["client_id"], "is_deleted": {"$ne": True}}, "read"), {"_id": 0})
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
                    await access.query("user_records", {"id": record["id"]}, "write"),
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    logs = await db.sms_logs.find(await access.query("sms_logs", query, "read"), {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
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
    """V2 development communication boundary: no external delivery."""
    return mock_delivery("email")

# IMPORTANT: This route must be BEFORE /inbox/{client_id} to avoid shadowing
@api_router.get("/inbox/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread messages count for notification badge"""
    access = CRMAccess(db, current_user)
    count = await db.sms_conversations.count_documents(await access.query("sms_conversations", {
        "direction": "inbound",
        "is_read": False
    }, "read"))
    return {"unread_count": count}

@api_router.get("/inbox/{client_id}")
async def get_client_inbox(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get all SMS messages for a client (conversation inbox)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    # Get client info
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all messages for this client (both sent and received)
    messages = await db.sms_conversations.find(
        await access.query("sms_conversations", {"client_id": client_id}, "read"),
        {"_id": 0}
    ).sort("timestamp", 1).to_list(500)
    
    # Also get SMS logs for historical messages
    sms_logs = await db.sms_logs.find(
        await access.query("sms_logs", {"client_id": client_id}, "read"),
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
    unread_count = await db.sms_conversations.count_documents(await access.query("sms_conversations", {
        "client_id": client_id,
        "direction": "inbound",
        "is_read": False
    }, "read"))
    
    return {
        "client": client,
        "messages": messages,
        "unread_count": unread_count
    }

@api_router.post("/inbox/{client_id}/send")
async def send_inbox_message(client_id: str, message: str = Form(...), current_user: dict = Depends(get_current_user)):
    """Send a message from the inbox to a client"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    # Get client info
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
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
        await access.query("clients", {"id": client_id}, "write"),
        {"$set": {"last_sms_activity": now, "last_active_user_id": current_user["id"]}}
    )
    
    if result["success"]:
        return {"message": "SMS sent successfully", "conversation": {**conversation_msg, "_id": None}}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {result.get('error')}")

@api_router.post("/inbox/{client_id}/mark-read")
async def mark_messages_read(client_id: str, current_user: dict = Depends(get_current_user)):
    """Mark all inbound messages for a client as read"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    result = await db.sms_conversations.update_many(
        await access.query("sms_conversations", {"client_id": client_id, "direction": "inbound", "is_read": False}, "write"),
        {"$set": {"read": True, "read_by": current_user["id"], "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Marked {result.modified_count} messages as read"}

@api_router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user), limit: int = 20):
    """Get in-app notifications for the current user"""
    notifications = await db.notifications.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "is_read": False
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
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

# ==================== TWILIO WEBHOOK (Receive SMS) ====================

@app.post("/webhook/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """
    Webhook endpoint to receive incoming SMS messages from Twilio.
    Configure this URL in your Twilio console: https://your-domain.com/webhook/twilio/sms
    """
    form_data = await validate_twilio_webhook(request)
    try:
        
        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        
        logger.info("Validated inbound SMS webhook")
        
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
                "is_read": False
            }
            result = await db.sms_conversations.update_one(
                {"_id": "twilio:" + message_sid},
                {"$setOnInsert": {**conversation_msg, "id": "twilio:" + message_sid}}, upsert=True)
            if not result.upserted_id:
                return Response(content='<Response/>', media_type='application/xml')
            
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
                    "is_read": False,
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
            
            logger.info("Processed inbound SMS webhook")
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
                "is_read": False
            }
            await db.sms_conversations.update_one(
                {"_id": "twilio:" + message_sid},
                {"$setOnInsert": {**unknown_msg, "id": "twilio:" + message_sid}}, upsert=True)
            logger.info("Processed unmatched inbound SMS webhook")
        
        # Return TwiML response (empty response = don't auto-reply)
        return Response(content='<Response/>', media_type='application/xml')
        
    except Exception as e:
        logger.error("Inbound SMS webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# ==================== CLIENT COLLABORATION ====================

@api_router.post("/clients/{client_id}/request-collaboration")
async def request_collaboration(client_id: str, current_user: dict = Depends(get_current_user)):
    """Request to collaborate on a client with the original salesperson"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
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
        "is_read": False,
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
    access = CRMAccess(db, current_user)
    collab_request = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not collab_request:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    
    if collab_request["original_user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You are not authorized to respond to this request")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if accept:
        # Add requester to client's collaboration list
        await db.clients.update_one(
            await access.query("clients", {"id": collab_request["client_id"]}, "write"),
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
            "is_read": False,
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
            "is_read": False,
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
    access = CRMAccess(db, current_user)
    validated_content = await validate_import(file)
    try:
        content = validated_content
        
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
            existing_client = await db.clients.find_one(await access.query("clients", {
                "$or": [
                    {"phone": {"$regex": phone_clean[-10:] + "$"}},
                    {"phone": phone_raw}
                ]
            }, "read"), {"_id": 0})
            
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0})
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
        await access.query("clients", {"id": client_id}, "write"),
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
    return secrets.token_urlsafe(32)

async def create_public_link(client_id: str, record_id: str, link_type: str) -> str:
    """Create and store a public link token"""
    if link_type != "appointment":
        raise HTTPException(status_code=403, detail="Public document access is disabled")
    appointment = await db.appointments.find_one({"id": record_id, "client_id": client_id, "is_deleted": {"$ne": True}})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    token = generate_public_token(client_id, record_id, link_type)
    
    link_doc = {
        "id": str(uuid.uuid4()),
        "token": token,
        "client_id": client_id,
        "record_id": record_id,
        "link_type": link_type,  # 'documents' or 'appointment'
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "used": False
    }
    await db.public_links.insert_one(link_doc)
    return token

@api_router.post("/generate-document-link/{client_id}")
async def generate_document_link(client_id: str, record_id: str, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=403, detail="Public document access is disabled")

@api_router.post("/generate-appointment-link/{appointment_id}")
async def generate_appointment_link(appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a public link for client to manage appointment"""
    access = CRMAccess(db, current_user)
    if appointment_id:
        await access.require("appointments", appointment_id, "write")
    appointment = await db.appointments.find_one(await access.query("appointments", {"id": appointment_id}, "read"), {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    token = await create_public_link(appointment.get("client_id", ""), appointment_id, "appointment")
    
    # Update appointment with the token
    await db.appointments.update_one(await access.query("appointments", {"id": appointment_id}, "write"), {"$set": {"public_token": token}})
    
    return {"token": token, "link": f"/c/appointment/{token}"}

# Public endpoints (no auth required)
@api_router.get("/public/documents/{token}")
async def get_public_document_info(token: str):
    raise HTTPException(status_code=403, detail="Public document access is disabled")

class DocumentLanguageRequest(BaseModel):
    language: str  # 'en' or 'es'

@api_router.put("/public/documents/{token}/language")
async def update_document_language_preference(token: str, data: DocumentLanguageRequest):
    raise HTTPException(status_code=403, detail="Public document access is disabled")

@api_router.post("/public/documents/{token}/upload")
async def upload_public_documents(
    token: str,
    id_documents: List[UploadFile] = File(default=[]),
    income_documents: List[UploadFile] = File(default=[]),
    residence_documents: List[UploadFile] = File(default=[]),
    language: str = Form(default="en")
):
    raise HTTPException(status_code=403, detail="Public document access is disabled")

@api_router.get("/public/appointment/{token}")
async def get_public_appointment_info(token: str):
    """Get appointment info for client management (public, no auth)"""
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

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
    appointment_with_address = {key: appointment.get(key) for key in ("date", "time", "dealer", "status", "language", "preferred_language")}
    appointment_with_address["dealer_address"] = dealer_address
    
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
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

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
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "cancelado", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Cita cancelada"}

@api_router.put("/public/appointment/{token}/confirm")
async def confirm_public_appointment(token: str):
    """Confirm appointment (public, no auth)"""
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

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
    
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"preferred_language": data.language, "language_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"Language preference updated to {data.language}"}

@api_router.put("/public/appointment/{token}/late")
async def notify_late_arrival(token: str, data: LateArrivalRequest):
    """Notify that client will arrive late and send SMS to salesperson (public, no auth)"""
    appointment = await resolve_appointment_token(db, token)
    appointment_id = appointment["id"]
    client_id = appointment["client_id"]

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
    access = CRMAccess(db, current_user)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload CSV or Excel file (.csv, .xlsx, .xls)")
    
    validated_content = await validate_import(file)
    try:
        contents = validated_content
        
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
            existing = await db.imported_contacts.find_one(await access.query("imported_contacts", {"phone": phone}, "read"))
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
    access = CRMAccess(db, current_user)
    query = {}
    
    # Non-admin users only see their own imports
    if current_user["role"] != "admin":
        query["imported_by"] = current_user["id"]
    
    if status:
        query["status"] = status
    
    contacts = await db.imported_contacts.find(await access.query("imported_contacts", query, "read"), {"_id": 0}).sort("imported_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.imported_contacts.count_documents(await access.query("imported_contacts", query, "read"))
    
    return {"contacts": contacts, "total": total}

@api_router.post("/imported-contacts/{contact_id}/send-sms-now")
async def send_marketing_sms_now(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Send marketing SMS immediately to an imported contact"""
    access = CRMAccess(db, current_user)
    if contact_id:
        await access.require("imported_contacts", contact_id, "write")
    contact = await db.imported_contacts.find_one(await access.query("imported_contacts", {"id": contact_id}, "read"), {"_id": 0})
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
    base_url = os.environ.get('FRONTEND_URL', '')
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
        await access.query("imported_contacts", {"id": contact_id}, "write"),
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
    access = CRMAccess(db, current_user)
    if contact_id:
        await access.require("imported_contacts", contact_id, "write")
    result = await db.imported_contacts.update_one(
        await access.query("imported_contacts", {"id": contact_id}, "write"),
        {"$set": {"opt_out": opt_out, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"message": f"Contact {'opted out' if opt_out else 'opted in'} successfully"}

@api_router.delete("/imported-contacts/{contact_id}")
async def delete_imported_contact(contact_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an imported contact"""
    access = CRMAccess(db, current_user)
    if contact_id:
        await access.require("imported_contacts", contact_id, "write")
    contact = await db.imported_contacts.find_one(await access.query("imported_contacts", {"id": contact_id}, "read"), {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Only owner or admin can delete
    if current_user["role"] != "admin" and contact.get("imported_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contact")
    
    await db.imported_contacts.delete_one(await access.query("imported_contacts", {"id": contact_id}, "write"))
    return {"message": "Contact deleted"}

# Also add opt_out field to clients
@api_router.put("/clients/{client_id}/opt-out")
async def toggle_client_opt_out(client_id: str, opt_out: bool, current_user: dict = Depends(get_current_user)):
    """Toggle opt-out status for a client (disable/enable automatic appointment SMS)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    result = await db.clients.update_one(
        await access.query("clients", {"id": client_id}, "write"),
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
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to delete clients")
    
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if permanent:
        # Permanent delete
        await db.clients.delete_one(await access.query("clients", {"id": client_id}, "write"))
        # Also delete related records and appointments
        await db.user_records.delete_many(await access.query("user_records", {"client_id": client_id}, "write"))
        await db.appointments.delete_many(await access.query("appointments", {"client_id": client_id}, "write"))
        await db.cosigner_relations.delete_many(await access.query("cosigner_relations", {"$or": [{"buyer_client_id": client_id}, {"cosigner_client_id": client_id}]}, "write"))
        return {"message": "Client permanently deleted"}
    else:
        # Soft delete
        await db.clients.update_one(
            await access.query("clients", {"id": client_id}, "write"),
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "Client moved to trash"}

@api_router.post("/clients/{client_id}/restore")
async def restore_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Restore a deleted client (admin only)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.clients.update_one(
        await access.query("clients", {"id": client_id, "is_deleted": True}, "write"),
        {"$set": {"is_deleted": False}, "$unset": {"deleted_at": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deleted client not found")
    return {"message": "Client restored"}

# ==================== CLIENT ACCESS REQUESTS ====================

@api_router.post("/client-requests")
async def create_client_request(client_id: str, current_user: dict = Depends(get_current_user)):
    """Create a request to access another user's client"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "write")
    # Get the client
    client = await db.clients.find_one(await access.query("clients", {"id": client_id, "is_deleted": {"$ne": True}}, "read"), {"_id": 0})
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
    access = CRMAccess(db, current_user)
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
            await access.query("clients", {"id": request.get("client_id")}, "write"),
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
    access = CRMAccess(db, current_user)
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
        clients_today = await db.clients.count_documents(await access.query("clients", {
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": today.isoformat()}
        }, "read"))
        clients_week = await db.clients.count_documents(await access.query("clients", {
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": week_ago.isoformat()}
        }, "read"))
        clients_month = await db.clients.count_documents(await access.query("clients", {
            "created_by": sp_id,
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": month_ago.isoformat()}
        }, "read"))
        clients_total = await db.clients.count_documents(await access.query("clients", {
            "created_by": sp_id,
            "is_deleted": {"$ne": True}
        }, "read"))
        
        # Appointments created
        appts_today = await db.appointments.count_documents(await access.query("appointments", {
            "salesperson_id": sp_id,
            "created_at": {"$gte": today.isoformat()}
        }, "read"))
        appts_week = await db.appointments.count_documents(await access.query("appointments", {
            "salesperson_id": sp_id,
            "created_at": {"$gte": week_ago.isoformat()}
        }, "read"))
        appts_month = await db.appointments.count_documents(await access.query("appointments", {
            "salesperson_id": sp_id,
            "created_at": {"$gte": month_ago.isoformat()}
        }, "read"))
        
        # Sales (completed records)
        sales_today = await db.user_records.count_documents(await access.query("user_records", {
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": today.isoformat()}
        }, "read"))
        sales_week = await db.user_records.count_documents(await access.query("user_records", {
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": week_ago.isoformat()}
        }, "read"))
        sales_month = await db.user_records.count_documents(await access.query("user_records", {
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True},
            "updated_at": {"$gte": month_ago.isoformat()}
        }, "read"))
        sales_total = await db.user_records.count_documents(await access.query("user_records", {
            "salesperson_id": sp_id,
            "record_status": "completed",
            "is_deleted": {"$ne": True}
        }, "read"))
        
        # Records total
        records_total = await db.user_records.count_documents(await access.query("user_records", {
            "salesperson_id": sp_id,
            "is_deleted": {"$ne": True}
        }, "read"))
        
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
    
    validated_content = await bounded_read(file)
    try:
        # Read and parse JSON
        content = validated_content
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
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden sincronizar clientes vendidos")
    
    try:
        # Find all clients with completed records that aren't marked as sold
        completed_records = await db.user_records.find(
            await access.query("user_records", {"record_status": "completed", "is_deleted": {"$ne": True}}, "read"),
            {"_id": 0, "client_id": 1, "created_at": 1}
        ).to_list(1000)
        
        synced_count = 0
        for record in completed_records:
            client_id = record["client_id"]
            
            # Check if client is already marked as sold
            client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"), {"_id": 0, "is_sold": 1})
            if client and not client.get("is_sold", False):
                # Mark client as sold
                await db.clients.update_one(
                    await access.query("clients", {"id": client_id}, "write"),
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

@api_router.post("/admin/fix-sold-clients")
async def fix_sold_clients(current_user: dict = Depends(get_current_user)):
    """Fix clients incorrectly marked as sold - remove is_sold flag from clients with no completed records (Admin only)"""
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    try:
        # Find all clients marked as sold
        sold_clients = await db.clients.find(
            await access.query("clients", {"is_sold": True, "is_deleted": {"$ne": True}}, "read"),
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
        ).to_list(1000)
        
        fixed_count = 0
        fixed_clients = []
        
        for client in sold_clients:
            client_id = client["id"]
            # Check if this client has any completed records
            completed_count = await db.user_records.count_documents(await access.query("user_records", {
                "client_id": client_id,
                "record_status": "completed",
                "is_deleted": {"$ne": True}
            }, "read"))
            
            if completed_count == 0:
                # No completed records, remove sold status
                await db.clients.update_one(
                    await access.query("clients", {"id": client_id}, "write"),
                    {"$set": {"is_sold": False, "sold_at": None}}
                )
                fixed_count += 1
                fixed_clients.append({
                    "id": client_id,
                    "name": f"{client.get('first_name', '')} {client.get('last_name', '')}"
                })
        
        logger.info(f"Fixed sold clients by {current_user['email']}: {fixed_count} clients corrected")
        
        return {
            "message": f"Corrección completada: {fixed_count} clientes ya no marcados como vendidos",
            "fixed_count": fixed_count,
            "total_checked": len(sold_clients),
            "fixed_clients": fixed_clients
        }
        
    except Exception as e:
        logger.error(f"Fix sold clients error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al corregir: {str(e)}")

@api_router.get("/admin/debug-clients")
async def debug_clients(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to check client ownership (Admin only)"""
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    # Get current user info
    user_info = {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"]
    }
    
    # Count clients by created_by
    all_clients = await db.clients.find(await access.query("clients", {"is_deleted": {"$ne": True}}, "read"), {"_id": 0, "created_by": 1, "first_name": 1, "last_name": 1}).to_list(1000)
    
    my_clients = [c for c in all_clients if c.get("created_by") == current_user["id"]]
    other_clients = [c for c in all_clients if c.get("created_by") != current_user["id"]]
    
    # Get unique created_by values
    created_by_ids = list(set([c.get("created_by") for c in all_clients if c.get("created_by")]))
    
    # Get user info for each creator
    creators = []
    for creator_id in created_by_ids:
        user = await db.users.find_one({"id": creator_id}, {"_id": 0, "id": 1, "email": 1, "name": 1, "role": 1})
        count = len([c for c in all_clients if c.get("created_by") == creator_id])
        if user:
            creators.append({
                "id": creator_id,
                "email": user.get("email"),
                "name": user.get("name"),
                "role": user.get("role"),
                "client_count": count
            })
        else:
            creators.append({
                "id": creator_id,
                "email": "USUARIO ELIMINADO",
                "name": "USUARIO ELIMINADO", 
                "role": "unknown",
                "client_count": count
            })
    
    return {
        "current_user": user_info,
        "total_clients": len(all_clients),
        "my_clients_count": len(my_clients),
        "other_clients_count": len(other_clients),
        "creators": creators
    }

# ==================== SCHEDULER ENDPOINTS ====================

@api_router.get("/scheduler/status")
async def get_scheduler_status(current_user: dict = Depends(get_current_user)):
    """Get the status of the SMS scheduler (admin only)"""
    access = CRMAccess(db, current_user)
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
    pending_initial = await db.imported_contacts.count_documents(await access.query("imported_contacts", {
        "opt_out": False,
        "appointment_created": False,
        "sms_sent": False
    }, "read"))
    
    pending_reminder = await db.imported_contacts.count_documents(await access.query("imported_contacts", {
        "opt_out": False,
        "appointment_created": False,
        "sms_sent": True,
        "sms_count": {"$lt": 5}
    }, "read"))
    
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

# Employment model for multiple jobs support
class Employment(BaseModel):
    employmentType: Optional[str] = None  # Tipo de empleo
    employerName: Optional[str] = None  # Company / Business Name
    employerPhoneNumber: Optional[str] = None  # Employer Phone Number
    timeWithEmployerYears: Optional[int] = None  # Time at Employment (years)
    timeWithEmployerMonths: Optional[int] = None  # Time at Employment (months)
    incomeType: Optional[str] = None  # Income type (Empleado, Self-Employed, etc.)
    netIncome: Optional[str] = None  # Net Income Amount
    incomeFrequency: Optional[str] = None  # Income Frequency

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
    # Legacy single employment fields (for backward compatibility)
    employerName: Optional[str] = None
    employerPhoneNumber: Optional[str] = None
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    # Multiple employments support (up to 4)
    employments: Optional[List[Employment]] = None
    estimatedDownPayment: Optional[str] = None
    consentAccepted: bool = False

class PreQualifyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")  # Changed to allow for employments array
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
    # Legacy single employment fields (for backward compatibility)
    employerName: Optional[str] = None
    employerPhoneNumber: Optional[str] = None
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    # Multiple employments support
    employments: Optional[List[Employment]] = None
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
                "is_read": False,
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
    # Primary employment (backward compatible)
    employerName: Optional[str] = Form(None),
    employerPhoneNumber: Optional[str] = Form(None),
    employmentType: Optional[str] = Form(None),
    # Time with employer - separated fields (support both naming conventions)
    timeWithEmployerYears: Optional[str] = Form(None),
    timeWithEmployerMonths: Optional[str] = Form(None),
    # Alternative names from website form
    employmentTimeYears: Optional[str] = Form(None),
    employmentTimeMonths: Optional[str] = Form(None),
    incomeType: Optional[str] = Form(None),
    netIncome: Optional[str] = Form(None),
    incomeFrequency: Optional[str] = Form(None),
    # Multiple employments support (up to 4 jobs)
    # Employment 2
    employmentType2: Optional[str] = Form(None),
    employerName2: Optional[str] = Form(None),
    employerPhoneNumber2: Optional[str] = Form(None),
    timeWithEmployerYears2: Optional[str] = Form(None),
    timeWithEmployerMonths2: Optional[str] = Form(None),
    incomeType2: Optional[str] = Form(None),
    netIncome2: Optional[str] = Form(None),
    incomeFrequency2: Optional[str] = Form(None),
    # Employment 3
    employmentType3: Optional[str] = Form(None),
    employerName3: Optional[str] = Form(None),
    employerPhoneNumber3: Optional[str] = Form(None),
    timeWithEmployerYears3: Optional[str] = Form(None),
    timeWithEmployerMonths3: Optional[str] = Form(None),
    incomeType3: Optional[str] = Form(None),
    netIncome3: Optional[str] = Form(None),
    incomeFrequency3: Optional[str] = Form(None),
    # Employment 4
    employmentType4: Optional[str] = Form(None),
    employerName4: Optional[str] = Form(None),
    employerPhoneNumber4: Optional[str] = Form(None),
    timeWithEmployerYears4: Optional[str] = Form(None),
    timeWithEmployerMonths4: Optional[str] = Form(None),
    incomeType4: Optional[str] = Form(None),
    netIncome4: Optional[str] = Form(None),
    incomeFrequency4: Optional[str] = Form(None),
    # JSON array of all employments (alternative format from website)
    employments_json: Optional[str] = Form(None, alias="employments"),
    totalEmployments: Optional[str] = Form(None),
    # Support both down payment field naming conventions
    estimatedDownPayment: Optional[str] = Form(None),
    downPayment: Optional[str] = Form(None),  # Alternative from website
    consentAccepted: bool = Form(False),
    smsConsent: bool = Form(False),  # SMS notification consent for Twilio A2P compliance
    language: Optional[str] = Form(None),
    # Support multiple file field names
    id_file: Optional[UploadFile] = File(None),
    id_files: List[UploadFile] = File(default=[]),
    idFile: Optional[UploadFile] = File(None)  # Alternative from website
):
    """Submit pre-qualify data; anonymous document uploads are forbidden."""
    if id_file or id_files or idFile:
        raise HTTPException(status_code=403, detail="Public document uploads are disabled")
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
                if file_extension not in ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic']:
                    continue  # Skip invalid files
                
                content = await file.read()
                temp_filename = f"temp_{submission_id}_{idx}{file_extension}"
                temp_path = temp_dir / temp_filename
                
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                # Optimize image files before further processing
                if file_extension in ['.jpg', '.jpeg', '.png', '.webp', '.heic']:
                    temp_path = optimize_document(temp_path, max_size_kb=400, max_dimension=1600)
                    file_extension = temp_path.suffix.lower()  # May have changed to .jpg
                
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
    
    # Build employments array
    employments = []
    
    # Log received employment data for debugging
    logger.info(f"=== EMPLOYMENT DATA RECEIVED ===")
    logger.info(f"employments_json: {employments_json[:200] if employments_json else 'None'}...")
    logger.info(f"totalEmployments: {totalEmployments}")
    logger.info(f"Employment 1: employerName={employerName}, incomeType={incomeType}, netIncome={netIncome}")
    logger.info(f"Employment 2: employerName2={employerName2}, incomeType2={incomeType2}, netIncome2={netIncome2}")
    logger.info(f"Employment 3: employerName3={employerName3}, incomeType3={incomeType3}, netIncome3={netIncome3}")
    logger.info(f"Employment 4: employerName4={employerName4}, incomeType4={incomeType4}, netIncome4={netIncome4}")
    
    # OPTION 1: Try to parse JSON array first (preferred from website)
    if employments_json and employments_json.strip() and employments_json.strip() != '[]':
        try:
            import json
            parsed_employments = json.loads(employments_json)
            if isinstance(parsed_employments, list) and len(parsed_employments) > 0:
                for emp in parsed_employments:
                    if isinstance(emp, dict) and (emp.get('employerName') or emp.get('incomeType') or emp.get('netIncome')):
                        employments.append({
                            "employmentType": emp.get('employmentType'),
                            "employerName": emp.get('employerName'),
                            "employerPhoneNumber": emp.get('employerPhoneNumber'),
                            "timeWithEmployerYears": int(emp.get('timeWithEmployerYears')) if emp.get('timeWithEmployerYears') else None,
                            "timeWithEmployerMonths": int(emp.get('timeWithEmployerMonths')) if emp.get('timeWithEmployerMonths') else None,
                            "incomeType": emp.get('incomeType'),
                            "netIncome": emp.get('netIncome'),
                            "incomeFrequency": emp.get('incomeFrequency')
                        })
                logger.info(f"Parsed {len(employments)} employments from JSON array")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse employments JSON: {e}")
            employments = []  # Reset and fall back to individual fields
    
    # OPTION 2: If JSON parsing failed or was empty, use individual fields
    if len(employments) == 0:
        logger.info("Using individual employment fields (fallback)")
        
        # Employment 1 (primary)
        if employerName or incomeType or netIncome:
            employments.append({
                "employmentType": employmentType or incomeType,
                "employerName": employerName,
                "employerPhoneNumber": employerPhoneNumber,
                "timeWithEmployerYears": final_employmentYears,
                "timeWithEmployerMonths": final_employmentMonths,
                "incomeType": incomeType,
                "netIncome": netIncome,
                "incomeFrequency": incomeFrequency
            })
        
        # Employment 2
        if employerName2 or incomeType2 or netIncome2:
            employments.append({
                "employmentType": employmentType2,
                "employerName": employerName2,
                "employerPhoneNumber": employerPhoneNumber2,
                "timeWithEmployerYears": int(timeWithEmployerYears2) if timeWithEmployerYears2 and timeWithEmployerYears2.strip().isdigit() else None,
                "timeWithEmployerMonths": int(timeWithEmployerMonths2) if timeWithEmployerMonths2 and timeWithEmployerMonths2.strip().isdigit() else None,
                "incomeType": incomeType2,
                "netIncome": netIncome2,
                "incomeFrequency": incomeFrequency2
            })
        
        # Employment 3
        if employerName3 or incomeType3 or netIncome3:
            employments.append({
                "employmentType": employmentType3,
                "employerName": employerName3,
                "employerPhoneNumber": employerPhoneNumber3,
                "timeWithEmployerYears": int(timeWithEmployerYears3) if timeWithEmployerYears3 and timeWithEmployerYears3.strip().isdigit() else None,
                "timeWithEmployerMonths": int(timeWithEmployerMonths3) if timeWithEmployerMonths3 and timeWithEmployerMonths3.strip().isdigit() else None,
                "incomeType": incomeType3,
                "netIncome": netIncome3,
                "incomeFrequency": incomeFrequency3
            })
        
        # Employment 4
        if employerName4 or incomeType4 or netIncome4:
            employments.append({
                "employmentType": employmentType4,
                "employerName": employerName4,
                "employerPhoneNumber": employerPhoneNumber4,
                "timeWithEmployerYears": int(timeWithEmployerYears4) if timeWithEmployerYears4 and timeWithEmployerYears4.strip().isdigit() else None,
                "timeWithEmployerMonths": int(timeWithEmployerMonths4) if timeWithEmployerMonths4 and timeWithEmployerMonths4.strip().isdigit() else None,
                "incomeType": incomeType4,
                "netIncome": netIncome4,
                "incomeFrequency": incomeFrequency4
            })
    
    # Log the built employments array
    logger.info(f"=== EMPLOYMENTS ARRAY BUILT ===")
    logger.info(f"Total employments: {len(employments)}")
    for i, emp in enumerate(employments):
        logger.info(f"Employment {i+1}: {emp}")
    
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
        # Legacy single employment fields (for backward compatibility)
        "employerName": employerName,
        "employerPhoneNumber": employerPhoneNumber,
        "employmentType": employmentType,
        "timeWithEmployerYears": final_employmentYears,
        "timeWithEmployerMonths": final_employmentMonths,
        "incomeType": incomeType,
        "netIncome": netIncome,
        "incomeFrequency": incomeFrequency,
        # Multiple employments array
        "employments": employments if employments else None,
        "estimatedDownPayment": final_downPayment,  # Use normalized value
        "consentAccepted": consentAccepted,
        "smsConsent": smsConsent,  # SMS notification consent for Twilio A2P compliance
        "smsConsentDate": datetime.now(timezone.utc).isoformat() if smsConsent else None,
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
                "is_read": False,
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
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submissions = await db.prequalify_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for sub in submissions:
        if not sub.get("matched_client_id"):
            phone = sub.get("phone", "")
            if phone:
                existing_client = await db.clients.find_one(
                    await access.query("clients", {"phone": {"$regex": phone[-10:], "$options": "i"}, "is_deleted": {"$ne": True}}, "read"),
                    {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
                )
                if existing_client:
                    sub["matched_client_id"] = existing_client["id"]
                    sub["matched_client_name"] = f"{existing_client['first_name']} {existing_client['last_name']}"
    return submissions

@api_router.get("/prequalify/submissions/{submission_id}")
async def get_prequalify_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    comparison = None
    if submission.get("matched_client_id"):
        client = await db.clients.find_one(await access.query("clients", {"id": submission["matched_client_id"]}, "read"), {"_id": 0})
        if client:
            # Get the most recent record for this client
            latest_record = await db.user_records.find_one(
                await access.query("user_records", {"client_id": client["id"], "is_deleted": {"$ne": True}}, "read"),
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
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    client_id = str(uuid.uuid4())
    await require_document_access({"id": client_id, "created_by": current_user["id"]}, current_user, "write")
    full_address = f"{submission.get('address', '')} {submission.get('city', '')} {submission.get('state', '')} {submission.get('zipCode', '')}".strip()
    
    # Transfer ID document if exists
    id_file_url = None
    id_uploaded = False
    prequalify_id_file = submission.get("id_file_url")
    
    if prequalify_id_file:
        try:
            old_path = resolve_document_path(prequalify_id_file, UPLOAD_DIR)
            if old_path is not None:
                new_path = UPLOAD_DIR / f"{client_id}_id{old_path.suffix}"
                shutil.copy2(old_path, new_path)
                id_file_url = str(new_path)
                id_uploaded = True
            else:
                logger.warning("Pre-qualify ID document unavailable in local storage")
        except OSError:
            logger.warning("Unable to transfer pre-qualify ID document")

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
    
    # Transfer employments array from submission to client
    submission_employments = submission.get("employments", [])
    if not submission_employments:
        # If no employments array, create one from legacy fields for backward compatibility
        if submission.get("employerName") or submission.get("incomeType") or submission.get("netIncome"):
            submission_employments = [{
                "employmentType": submission.get("employmentType") or submission.get("incomeType"),
                "employerName": submission.get("employerName"),
                "employerPhoneNumber": submission.get("employerPhoneNumber"),
                "timeWithEmployerYears": submission.get("timeWithEmployerYears"),
                "timeWithEmployerMonths": submission.get("timeWithEmployerMonths"),
                "incomeType": submission.get("incomeType"),
                "netIncome": submission.get("netIncome"),
                "incomeFrequency": submission.get("incomeFrequency")
            }]
    
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
        # Also add to the new documents array system
        "id_documents": [{
            "id": str(uuid.uuid4()),
            "filename": "ID_PreQualify",
            "path": id_file_url,
            "type": "application/pdf",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "uploaded_by": current_user["id"]
        }] if id_file_url else [],
        "income_proof_uploaded": False,
        "income_documents": [],
        "residence_proof_uploaded": False,
        "residence_documents": [],
        # Employment data from prequalification
        "employments": submission_employments,
        # Legacy employment fields from first employment (for backward compatibility)
        "employer_name": submission_employments[0].get("employerName") if submission_employments else submission.get("employerName"),
        "employer_phone": submission_employments[0].get("employerPhoneNumber") if submission_employments else submission.get("employerPhoneNumber"),
        "employment_type": submission_employments[0].get("employmentType") if submission_employments else submission.get("employmentType"),
        "income_type": submission_employments[0].get("incomeType") if submission_employments else submission.get("incomeType"),
        "net_income": submission_employments[0].get("netIncome") if submission_employments else submission.get("netIncome"),
        "income_frequency": submission_employments[0].get("incomeFrequency") if submission_employments else submission.get("incomeFrequency"),
        "time_with_employer_years": submission_employments[0].get("timeWithEmployerYears") if submission_employments else submission.get("timeWithEmployerYears"),
        "time_with_employer_months": submission_employments[0].get("timeWithEmployerMonths") if submission_employments else submission.get("timeWithEmployerMonths"),
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
    access = CRMAccess(db, current_user)
    if record_id:
        await access.require("user_records", record_id, "write")
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

@api_router.get("/clients/{client_id}/prequalify")
async def get_client_prequalify(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get prequalify submission linked to a client (Admin only)"""
    access = CRMAccess(db, current_user)
    if client_id:
        await access.require("clients", client_id, "read")
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # First get the client to find phone number
    client = await db.clients.find_one(await access.query("clients", {"id": client_id, "is_deleted": {"$ne": True}}, "read"), {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Search for prequalify submissions that match this client
    # Check by matched_client_id or by phone number
    prequalify = await db.prequalify_submissions.find_one(
        {
            "$or": [
                {"matched_client_id": client_id},
                {"phone": {"$regex": client.get("phone", "")[-10:] if client.get("phone") else "NOMATCH", "$options": "i"}}
            ]
        },
        {"_id": 0},
        sort=[("created_at", -1)]  # Get most recent
    )
    
    if not prequalify:
        return {"found": False, "prequalify": None}
    
    return {"found": True, "prequalify": prequalify}


@api_router.get("/clients/export/excel")
async def export_clients_excel(current_user: dict = Depends(get_current_user)):
    """Export all clients to Excel (Name, LastName, Email, Phone only)"""
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all non-deleted clients
    clients = await db.clients.find(
        await access.query("clients", {"is_deleted": {"$ne": True}}, "read"),
        {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "phone": 1}
    ).sort("created_at", -1).to_list(None)
    
    # Create Excel file
    df = pd.DataFrame(clients)
    df.columns = ["Nombre", "Apellido", "Email", "Teléfono"]
    
    # Create Excel in memory
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name="Clientes")
    output.seek(0)
    
    # Generate filename with date
    filename = f"clientes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.delete("/prequalify/submissions/{submission_id}")
async def delete_prequalify_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a prequalify submission and its associated documents (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    await require_document_access(submission, current_user, "delete")
    id_file_url = submission.get("id_file_url")
    file_path = resolve_document_path(id_file_url, UPLOAD_DIR)
    if file_path is not None:
        file_path.unlink()

    # Delete from database
    result = await db.prequalify_submissions.delete_one({"id": submission_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete submission")
    
    logger.info(f"Deleted prequalify submission {submission_id} by {current_user['email']}")
    
    return {"message": "Precalificación eliminada correctamente", "deleted_file": id_file_url is not None}


@api_router.post("/prequalify/submissions/{submission_id}/sync-to-client")
async def sync_prequalify_to_client(submission_id: str, current_user: dict = Depends(get_current_user)):
    """Overwrite existing client data with pre-qualification submission data (Admin only)"""
    access = CRMAccess(db, current_user)
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    submission = await db.prequalify_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if not submission.get("matched_client_id"):
        raise HTTPException(status_code=400, detail="No matched client found for this submission")
    
    client_id = submission["matched_client_id"]
    client = await db.clients.find_one(await access.query("clients", {"id": client_id}, "read"))
    if not client:
        raise HTTPException(status_code=404, detail="Matched client not found")
    await require_document_access(client, current_user, "write")
    
    # Build update data from submission
    update_data = {}
    
    # Personal info
    if submission.get("firstName"):
        update_data["first_name"] = submission["firstName"]
    if submission.get("lastName"):
        update_data["last_name"] = submission["lastName"]
    if submission.get("email"):
        update_data["email"] = submission["email"]
    if submission.get("phone"):
        update_data["phone"] = submission["phone"]
    if submission.get("dateOfBirth"):
        update_data["date_of_birth"] = submission["dateOfBirth"]
    
    # Address info
    if submission.get("address"):
        update_data["address"] = submission["address"]
    if submission.get("apartment"):
        update_data["apartment"] = submission["apartment"]
    if submission.get("city"):
        update_data["city"] = submission["city"]
    if submission.get("state"):
        update_data["state"] = submission["state"]
    if submission.get("zipCode"):
        update_data["zip_code"] = submission["zipCode"]
    
    # Housing info
    if submission.get("housingType"):
        update_data["housing_type"] = submission["housingType"]
    if submission.get("rentAmount"):
        update_data["rent_amount"] = submission["rentAmount"]
    if submission.get("timeAtAddressYears") is not None:
        update_data["time_at_address_years"] = submission["timeAtAddressYears"]
    if submission.get("timeAtAddressMonths") is not None:
        update_data["time_at_address_months"] = submission["timeAtAddressMonths"]
    
    # ID info
    if submission.get("idType"):
        update_data["id_type"] = submission["idType"]
    if submission.get("idNumber"):
        update_data["id_number"] = submission["idNumber"]
    
    # SSN/ITIN info
    if submission.get("ssnType"):
        update_data["ssn_type"] = submission["ssnType"]
    if submission.get("ssn"):
        update_data["ssn"] = submission["ssn"]
    
    # Transfer employments array from submission to client
    submission_employments = submission.get("employments", [])
    if not submission_employments:
        # If no employments array, create one from legacy fields for backward compatibility
        if submission.get("employerName") or submission.get("incomeType") or submission.get("netIncome"):
            submission_employments = [{
                "employmentType": submission.get("employmentType") or submission.get("incomeType"),
                "employerName": submission.get("employerName"),
                "employerPhoneNumber": submission.get("employerPhoneNumber"),
                "timeWithEmployerYears": submission.get("timeWithEmployerYears"),
                "timeWithEmployerMonths": submission.get("timeWithEmployerMonths"),
                "incomeType": submission.get("incomeType"),
                "netIncome": submission.get("netIncome"),
                "incomeFrequency": submission.get("incomeFrequency")
            }]
    
    # Always update employments if available
    if submission_employments:
        update_data["employments"] = submission_employments
        # Also update legacy employment fields from first employment
        first_emp = submission_employments[0] if submission_employments else {}
        update_data["employer_name"] = first_emp.get("employerName") or submission.get("employerName")
        update_data["employer_phone"] = first_emp.get("employerPhoneNumber") or submission.get("employerPhoneNumber")
        update_data["employment_type"] = first_emp.get("employmentType") or submission.get("employmentType")
        update_data["income_type"] = first_emp.get("incomeType") or submission.get("incomeType")
        update_data["net_income"] = first_emp.get("netIncome") or submission.get("netIncome")
        update_data["income_frequency"] = first_emp.get("incomeFrequency") or submission.get("incomeFrequency")
        update_data["time_with_employer_years"] = first_emp.get("timeWithEmployerYears") or submission.get("timeWithEmployerYears")
        update_data["time_with_employer_months"] = first_emp.get("timeWithEmployerMonths") or submission.get("timeWithEmployerMonths")
    
    # Copy document file if exists
    if submission.get("id_file_url"):
        id_file_url = submission["id_file_url"]
        update_data["id_file_url"] = id_file_url
        update_data["id_uploaded"] = True
        
        # Also add to the new documents array system
        update_data["id_documents"] = [{
            "id": str(uuid.uuid4()),
            "filename": "ID_PreQualify",
            "path": id_file_url,
            "type": "application/pdf",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "uploaded_by": current_user["id"]
        }]
        
        logger.info(f"Copying document from submission: {id_file_url}")
    else:
        logger.info(f"No id_file_url found in submission. Available keys: {list(submission.keys())}")
    
    # Update timestamp
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user["id"]
    
    logger.info(f"Update data for client {client_id}: {update_data}")
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    # Update the client
    result = await db.clients.update_one(await access.query("clients", {"id": client_id}, "write"), {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update client")
    
    # Mark submission as synced
    await db.prequalify_submissions.update_one(
        {"id": submission_id}, 
        {"$set": {"status": "synced", "synced_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    logger.info(f"Synced prequalify submission {submission_id} to client {client_id} by {current_user['email']}")
    
    return {
        "message": "Datos del cliente actualizados correctamente",
        "client_id": client_id,
        "fields_updated": list(update_data.keys())
    }

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
    """Initialize non-sensitive defaults; account provisioning is explicit."""
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

# ==================== DEMO ENDPOINTS ====================

class DemoResetRequest(BaseModel):
    confirm: bool = True

async def _seed_demo_data(demo_user_id: str, db):
    """Seed fictional demo data for a demo user"""
    from datetime import datetime, timedelta, timezone
    import uuid
    
    now = datetime.now(timezone.utc)
    
    # Delete existing demo data for this user
    await db.inventory.delete_many({"created_by": demo_user_id})
    await db.clients.delete_many({"created_by": demo_user_id})
    await db.appointments.delete_many({"created_by": demo_user_id})
    await db.conversations.delete_many({"salesperson_id": demo_user_id})
    await db.messages.delete_many({"conversation_id": {"$in": 
        [c["id"] async for c in db.conversations.find({"salesperson_id": demo_user_id}, {"id": 1})]
    }})
    await db.prequalifications.delete_many({"client_id": {"$in": 
        [c["id"] async for c in db.clients.find({"created_by": demo_user_id}, {"id": 1})]
    }})
    await db.activities.delete_many({"user_id": demo_user_id})
    
    # Create fictional vehicles
    vehicles = [
        {
            "id": str(uuid.uuid4()), "vin": "1HGCM82633A123456", "make": "Honda", "model": "Accord",
            "year": 2023, "trim": "EX-L", "color": "White", "mileage": 15000, "price": 28500, "cost": 25000,
            "status": "available", "dealer": "Main", "stock_number": "H23-001", "days_on_lot": 45,
            "description": "Clean CarFax, one owner", "features": "Bluetooth, Backup Camera, Leather Seats, Sunroof",
            "images": [], "created_at": (now - timedelta(days=45)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "5TDZZRFH0MS123456", "make": "Toyota", "model": "RAV4",
            "year": 2024, "trim": "XLE", "color": "Blue", "mileage": 500, "price": 34500, "cost": 31000,
            "status": "available", "dealer": "Main", "stock_number": "T24-002", "days_on_lot": 12,
            "description": "New arrival, hybrid AWD", "features": "Bluetooth, Backup Camera, Blind Spot Monitor, Lane Keep Assist",
            "images": [], "created_at": (now - timedelta(days=12)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "1FTFW1E50MFA12345", "make": "Ford", "model": "F-150",
            "year": 2023, "trim": "Lariat", "color": "Black", "mileage": 22000, "price": 42000, "cost": 38000,
            "status": "reserved", "dealer": "North", "stock_number": "F23-003", "days_on_lot": 78,
            "description": "EcoBoost, 4WD, crew cab", "features": "Leather, Navigation, 360 Camera, Pro Trailer Backup",
            "images": [], "created_at": (now - timedelta(days=78)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "1G1BE5SM0N7123456", "make": "Chevrolet", "model": "Malibu",
            "year": 2024, "trim": "LT", "color": "Silver", "mileage": 100, "price": 26500, "cost": 23500,
            "status": "available", "dealer": "Main", "stock_number": "C24-004", "days_on_lot": 8,
            "description": "Fuel efficient sedan", "features": "Bluetooth, Backup Camera, Apple CarPlay, Android Auto",
            "images": [], "created_at": (now - timedelta(days=8)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
        {
            "id": str(uuid.uuid4()), "vin": "KM8K33AG0NU123456", "make": "Hyundai", "model": "Santa Fe",
            "year": 2023, "trim": "Limited", "color": "Red", "mileage": 18000, "price": 36500, "cost": 32500,
            "status": "sold", "dealer": "South", "stock_number": "H23-005", "days_on_lot": 120,
            "description": "Well maintained, all service records", "features": "Leather, Panoramic Sunroof, Heated Seats, Harman Kardon Audio",
            "images": [], "created_at": (now - timedelta(days=120)).isoformat(),
            "created_by": demo_user_id, "is_deleted": False
        },
    ]
    
    await db.inventory.insert_many(vehicles)
    
    # Create fictional leads/customers
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
    
    await db.clients.insert_many(leads)
    
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
    
    await db.appointments.insert_many(appointments)
    
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
    
    await db.conversations.insert_many(conversations)
    
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
    
    await db.messages.insert_many(messages)
    
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
    
    await db.prequalifications.insert_many(prequals)
    
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
    
    await db.activities.insert_many(activities)
    
    return {
        "vehicles": len(vehicles),
        "leads": len(leads),
        "appointments": len(appointments),
        "conversations": len(conversations),
        "prequals": len(prequals),
        "activities": len(activities)
    }

@api_router.post("/demo/reset")
async def reset_demo_data(current_user: dict = Depends(get_current_user)):
    """Reset demo data for the current demo user"""
    if current_user.get("role") != "demo":
        raise HTTPException(status_code=403, detail="Demo access required")
    
    counts = await _seed_demo_data(current_user["id"], db)
    
    return {
        "message": "Demo data reset successfully",
        "demo_user": current_user["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seeded": counts
    }

@api_router.get("/demo/data")
async def get_demo_data(current_user: dict = Depends(get_current_user)):
    """Get demo data overview"""
    if current_user.get("role") != "demo":
        raise HTTPException(status_code=403, detail="Demo access required")
    
    # Return actual demo data stats
    vehicles_count = await db.inventory.count_documents({"created_by": current_user["id"]})
    leads_count = await db.clients.count_documents({"created_by": current_user["id"]})
    appointments_count = await db.appointments.count_documents({"created_by": current_user["id"]})
    conversations_count = await db.conversations.count_documents({"salesperson_id": current_user["id"]})
    prequals_count = await db.prequalifications.count_documents({
        "client_id": {"$in": await db.clients.find({"created_by": current_user["id"]}).distinct("id")}
    })
    
    return {
        "vehicles": vehicles_count,
        "leads": leads_count,
        "appointments": appointments_count,
        "conversations": conversations_count,
        "prequalifications": prequals_count,
        "is_demo": True,
        "data_source": "fictional"
    }

# ==================== INVENTORY ENDPOINTS ====================

class VehicleCreate(BaseModel):
    vin: str
    make: str
    model: str
    year: int
    trim: Optional[str] = None
    color: Optional[str] = None
    mileage: int = 0
    price: float
    cost: Optional[float] = None
    status: str = "available"  # available, reserved, sold, in_transit, service
    dealer: Optional[str] = None
    stock_number: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None
    images: Optional[List[str]] = None

class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    trim: Optional[str] = None
    color: Optional[str] = None
    mileage: Optional[int] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    status: Optional[str] = None
    dealer: Optional[str] = None
    stock_number: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None
    images: Optional[List[str]] = None

@api_router.post("/inventory", response_model=dict)
async def create_vehicle(vehicle: VehicleCreate, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    vehicle_doc = vehicle.dict()
    vehicle_doc["id"] = str(uuid.uuid4())
    vehicle_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    vehicle_doc["created_by"] = current_user["id"]
    vehicle_doc["days_on_lot"] = 0
    vehicle_doc["is_deleted"] = False
    
    await db.inventory.insert_one(vehicle_doc)
    return {k: v for k, v in vehicle_doc.items() if k != "_id"}

@api_router.get("/inventory", response_model=dict)
async def get_inventory(
    current_user: dict = Depends(get_current_user),
    search: Optional[str] = None,
    status: Optional[str] = None,
    make: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0
):
    access = CRMAccess(db, current_user)
    
    query = {"is_deleted": {"$ne": True}}
    
    if search:
        query["$or"] = [
            {"vin": {"$regex": search, "$options": "i"}},
            {"make": {"$regex": search, "$options": "i"}},
            {"model": {"$regex": search, "$options": "i"}},
            {"stock_number": {"$regex": search, "$options": "i"}}
        ]
    
    if status:
        query["status"] = status
    
    if make:
        query["make"] = make
    
    # Role-based filtering
    if current_user["role"] == "admin":
        pass
    elif current_user["role"] == "bdc_manager":
        admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
        admin_ids = [u["id"] for u in admin_users]
        query["dealer"] = {"$nin": [u for u in admin_ids]}  # Simplified
    else:
        query["dealer"] = current_user.get("dealer_id", "")
    
    sort_dir = -1 if sort_order == "desc" else 1
    
    vehicles = await db.inventory.find(query).sort(sort_by, sort_dir).skip(offset).limit(limit).to_list(limit)
    total = await db.inventory.count_documents(query)
    
    return {"vehicles": vehicles, "total": total}

@api_router.get("/inventory/{vehicle_id}", response_model=dict)
async def get_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    vehicle = await db.inventory.find_one({"id": vehicle_id, "is_deleted": {"$ne": True}})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@api_router.put("/inventory/{vehicle_id}", response_model=dict)
async def update_vehicle(vehicle_id: str, vehicle: VehicleUpdate, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    update_data = {k: v for k, v in vehicle.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.inventory.update_one(
        {"id": vehicle_id, "is_deleted": {"$ne": True}},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = await db.inventory.find_one({"id": vehicle_id})
    return vehicle

@api_router.delete("/inventory/{vehicle_id}")
async def delete_vehicle(vehicle_id: str, current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    result = await db.inventory.update_one(
        {"id": vehicle_id, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return {"message": "Vehicle moved to trash"}

# ==================== JARVIS ENDPOINTS ====================

class JarvisChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class JarvisExecuteRequest(BaseModel):
    action: dict
    confirmed: bool

@api_router.post("/jarvis/chat")
async def jarvis_chat(request: JarvisChatRequest, current_user: dict = Depends(get_current_user)):
    """Process Jarvis chat message and return response with optional tool calls"""
    message = request.message.lower()
    
    # Simple intent detection - in production this would use an LLM
    tool_calls = []
    response = ""
    requires_confirmation = False
    action = None
    
    if any(kw in message for kw in ["appointment", "cita", "schedule"]):
        tool_calls.append({
            "tool": "get_appointments",
            "params": {"date_range": "today"},
            "result": {"count": 3}
        })
        response = "I found 3 appointments for today. Would you like me to show them or help you schedule a new one?"
    
    elif any(kw in message for kw in ["lead", "follow", "prospect", "contact"]):
        tool_calls.append({
            "tool": "search_leads",
            "params": {"stage": "NEW LEAD", "days_since_contact": 48},
            "result": {"count": 7}
        })
        response = "There are 7 leads that haven't been contacted in 48+ hours. The oldest is from March 15th. Want me to list them?"
    
    elif any(kw in message for kw in ["inventory", "vehicle", "car", "stock"]):
        tool_calls.append({
            "tool": "get_inventory_report",
            "params": {},
            "result": {"total": 42, "aging_over_60": 12}
        })
        response = "We have 42 vehicles in inventory. 12 are over 60 days on lot. Top aging: 2023 Ford F-150 (78 days). Need details?"
    
    elif any(kw in message for kw in ["conversion", "rate", "metric", "performance"]):
        tool_calls.append({
            "tool": "get_conversion_report",
            "params": {"period": "month"},
            "result": {"rate": 18.5, "sales": 32, "leads": 173}
        })
        response = "Current conversion rate: 18.5% (32 sales / 173 leads this month). Industry avg is 15-20%. Want the breakdown by source?"
    
    elif any(kw in message for kw in ["deal", "negoti", "pending", "close"]):
        tool_calls.append({
            "tool": "search_leads",
            "params": {"stage": ["NEGOTIATING", "PENDING DEAL"]},
            "result": {"count": 8, "value": 485000}
        })
        response = "5 deals in negotiation stage, 3 pending deal. Total pipeline value: $485,000. Closest to closing: Robin Test - Electric Sedan ($42k)."
    
    elif any(kw in message for kw in ["document", "paperwork", "doc", "missing"]):
        tool_calls.append({
            "tool": "search_leads",
            "params": {"docs_incomplete": True},
            "result": {"count": 23, "missing_id": 15, "missing_income": 8}
        })
        response = "23 clients have incomplete documents. 15 missing ID, 8 missing income proof. Want me to send reminder SMS to any of them?"
    
    elif any(kw in message for kw in ["report", "analytics", "dashboard"]):
        response = "I can generate sales, leads, appointments, inventory, or financial reports. Which type and what period?"
    
    else:
        response = "I can help you with leads, appointments, inventory, deals, documents, and reports. Try asking: \"Show today's appointments\" or \"Which leads need follow-up?\""
    
    return {
        "response": response,
        "tool_calls": tool_calls,
        "requires_confirmation": requires_confirmation,
        "action": action
    }

@api_router.post("/jarvis/execute")
async def jarvis_execute(request: JarvisExecuteRequest, current_user: dict = Depends(get_current_user)):
    """Execute a confirmed Jarvis action"""
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Action not confirmed")
    
    action = request.action
    tool = action.get("tool")
    params = action.get("params", {})
    
    # In production, this would execute the actual tool
    # For demo, just return success
    return {
        "success": True,
        "tool": tool,
        "params": params,
        "result": {"status": "executed", "message": f"Tool {tool} executed with params: {params}"}
    }

# ==================== REPORTS ENDPOINTS ====================

@api_router.get("/reports/sales")
async def get_sales_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    # Mock data
    return [
        {"month": "Jan", "sales": 12, "revenue": 340000},
        {"month": "Feb", "sales": 15, "revenue": 420000},
        {"month": "Mar", "sales": 18, "revenue": 510000},
        {"month": "Apr", "sales": 14, "revenue": 390000},
        {"month": "May", "sales": 20, "revenue": 560000},
        {"month": "Jun", "sales": 22, "revenue": 620000},
    ]

@api_router.get("/reports/leads")
async def get_leads_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    return [
        {"source": "Website", "count": 45, "converted": 12},
        {"source": "Walk-in", "count": 30, "converted": 8},
        {"source": "Referral", "count": 20, "converted": 10},
        {"source": "Social Media", "count": 25, "converted": 5},
        {"source": "Phone", "count": 15, "converted": 4},
    ]

@api_router.get("/reports/appointments")
async def get_appointments_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    return [
        {"status": "agendado", "count": 35},
        {"status": "cumplido", "count": 28},
        {"status": "no_show", "count": 5},
        {"status": "sin_configurar", "count": 12},
        {"status": "cambio_hora", "count": 3},
    ]

@api_router.get("/reports/financial")
async def get_financial_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    return {
        "total_revenue": 2840000,
        "avg_deal": 32000,
        "total_gross": 420000,
        "total_down_payment": 580000,
    }

@api_router.get("/reports/inventory")
async def get_inventory_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    return [
        {"make": "Toyota", "count": 15, "avg_days": 32},
        {"make": "Honda", "count": 12, "avg_days": 28},
        {"make": "Ford", "count": 10, "avg_days": 45},
        {"make": "Chevrolet", "count": 8, "avg_days": 38},
        {"make": "Nissan", "count": 6, "avg_days": 41},
    ]

@api_router.get("/reports/attribution")
async def get_attribution_report(period: str = "month", current_user: dict = Depends(get_current_user)):
    access = CRMAccess(db, current_user)
    return [
        {"campaign": "Google Ads", "leads": 35, "sales": 8, "cost": 5000, "roi": 4.2},
        {"campaign": "Facebook", "leads": 28, "sales": 5, "cost": 3500, "roi": 3.8},
        {"campaign": "Email", "leads": 20, "sales": 4, "cost": 800, "roi": 12.5},
        {"campaign": "Referral", "leads": 15, "sales": 6, "cost": 0, "roi": 0},
        {"campaign": "Organic", "leads": 22, "sales": 5, "cost": 0, "roi": 0},
    ]

# ==================== INBOX CONVERSATIONS ENDPOINT ====================

@api_router.get("/inbox/conversations")
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    search: Optional[str] = None,
    channel: Optional[str] = None,
    unread: Optional[bool] = None
):
    access = CRMAccess(db, current_user)
    # Mock data for demo
    return [
        {"id": "1", "client_id": "c1", "client_name": "John Smith", "client_phone": "+15551234567", "channel": "sms", "last_message": "Thanks for the info!", "last_message_at": datetime.now(timezone.utc).isoformat(), "unread_count": 2, "status": "active"},
        {"id": "2", "client_id": "c2", "client_name": "Maria Garcia", "client_phone": "+15559876543", "channel": "email", "last_message": "When can I test drive?", "last_message_at": (datetime.now(timezone.utc).replace(hour=datetime.now().hour-1)).isoformat(), "unread_count": 0, "status": "active"},
        {"id": "3", "client_id": "c3", "client_name": "Robert Johnson", "client_phone": "+15554567890", "channel": "facebook", "last_message": "Interested in the Honda", "last_message_at": (datetime.now(timezone.utc).replace(hour=datetime.now().hour-2)).isoformat(), "unread_count": 1, "status": "active"},
    ]


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

