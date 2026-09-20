from runtime_security import mock_delivery
"""Email service for sending notifications"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME, RESEND_API_KEY, SENDER_EMAIL, logger

async def send_email_notification(to_email: str, subject: str, html_content: str):
    return mock_delivery("email")
