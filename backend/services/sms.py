from runtime_security import mock_delivery
"""SMS service using Twilio"""
import re
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, logger

# Provider initialization is disabled in V2 development.
twilio_client = None

def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format (+1XXXXXXXXXX)"""
    if not phone:
        return phone
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 10:
        return f"+{digits}"
    
    return phone

async def send_sms_twilio(to_phone: str, message: str):
    return mock_delivery("sms")
