"""Authentication utilities and dependencies"""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import JWT_SECRET, JWT_EXPIRATION_HOURS, db

from authentication.foundation import hash_password, verify_password
from authentication.runtime import SessionAuth

security = HTTPBearer()

session_auth = SessionAuth(db, JWT_SECRET, hours=JWT_EXPIRATION_HOURS)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return await session_auth.current_user(credentials.credentials)

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency to ensure the user is an admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
