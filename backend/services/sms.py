"""SMS service using Twilio"""
import re
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, logger

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        from twilio.rest import Client as TwilioClient
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        logger.warning(f"Could not initialize Twilio client: {e}")

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
    """Send SMS via Twilio"""
    if not twilio_client:
        logger.warning("Twilio not configured - SMS not sent")
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        normalized_phone = normalize_phone(to_phone)
        
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=normalized_phone
        )
        
        logger.info(f"SMS sent to {normalized_phone}: {msg.sid}")
        return {"success": True, "sid": msg.sid}
    except Exception as e:
        logger.error(f"SMS failed to {to_phone}: {str(e)}")
        return {"success": False, "error": str(e)}
