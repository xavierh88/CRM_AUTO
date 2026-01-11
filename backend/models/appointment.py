"""Appointment models"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class AppointmentCreate(BaseModel):
    user_record_id: str
    client_id: str
    date: str
    time: str
    dealer: Optional[str] = None
    language: str = "es"
    change_time: bool = False

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_record_id: str
    client_id: str
    salesperson_id: Optional[str] = None
    date: str
    time: str
    dealer: Optional[str] = None
    language: str = "es"
    change_time: bool = False
    status: str = "scheduled"
    link_sent_at: Optional[str] = None
    reminder_count: int = 0
    created_at: str
