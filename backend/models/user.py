"""User models for authentication and user management"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserCreate(BaseModel):
    email: str
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
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: Optional[str] = None
    role: str
    phone: Optional[str] = None
    created_at: str
