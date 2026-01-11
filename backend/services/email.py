"""Email service for sending notifications"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME, RESEND_API_KEY, SENDER_EMAIL, logger

async def send_email_notification(to_email: str, subject: str, html_content: str):
    """Send email notification using SMTP or Resend"""
    
    # Try SMTP first (free)
    if SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
            
            logger.info(f"Email sent via SMTP to {to_email}")
            return {"success": True, "method": "smtp"}
        except Exception as e:
            logger.error(f"SMTP email failed: {str(e)}")
    
    # Fallback to Resend if configured
    if RESEND_API_KEY:
        try:
            import resend
            resend.api_key = RESEND_API_KEY
            resend.Emails.send({
                "from": f"{SMTP_FROM_NAME} <{SENDER_EMAIL}>",
                "to": to_email,
                "subject": subject,
                "html": html_content
            })
            logger.info(f"Email sent via Resend to {to_email}")
            return {"success": True, "method": "resend"}
        except Exception as e:
            logger.error(f"Resend email failed: {str(e)}")
    
    return {"success": False, "error": "No email provider configured"}
