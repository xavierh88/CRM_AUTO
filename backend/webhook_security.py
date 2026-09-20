"""Validate inbound Twilio forms before any logging or database access.

TWILIO_WEBHOOK_URL is the exact externally registered URL, including its query.
Forwarded/Host headers are not trusted to reconstruct the signature input.
"""
import os
import re
from urllib.parse import parse_qsl
from fastapi import HTTPException
from twilio.request_validator import RequestValidator

MAX_WEBHOOK_BYTES = 16 * 1024


async def validate_twilio_webhook(request, environ=None):
    env = os.environ if environ is None else environ
    secret, url = env.get('TWILIO_AUTH_TOKEN'), env.get('TWILIO_WEBHOOK_URL')
    if not secret or not url or not url.startswith('https://'):
        raise HTTPException(503, 'Webhook validation is not configured')
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
        raise HTTPException(415, 'Unsupported webhook content type')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, 'Webhook payload too large')
    try:
        pairs = parse_qsl(body.decode('utf-8'), keep_blank_values=True, strict_parsing=True,
                          max_num_fields=100, errors='strict')
    except (UnicodeError, ValueError):
        raise HTTPException(400, 'Invalid webhook form')
    form = dict(pairs)
    if len(form) != len(pairs):
        raise HTTPException(400, 'Duplicate webhook fields')
    signature = request.headers.get('x-twilio-signature', '')
    if not signature or not RequestValidator(secret).validate(url, form, signature):
        raise HTTPException(403, 'Invalid webhook signature')
    if (not re.fullmatch(r'\+[1-9][0-9]{7,14}', form.get('From', ''))
            or not re.fullmatch(r'\+[1-9][0-9]{7,14}', form.get('To', ''))
            or not re.fullmatch(r'SM[0-9a-fA-F]{32}', form.get('MessageSid', ''))
            or not form.get('Body', '').strip() or len(form['Body']) > 1600):
        raise HTTPException(400, 'Invalid SMS payload')
    return form
