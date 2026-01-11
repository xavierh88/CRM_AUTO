"""Client models for customer management"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_at_address_years: Optional[int] = None
    time_at_address_months: Optional[int] = None
    housing_type: Optional[str] = None
    rent_amount: Optional[str] = None

class ClientResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_at_address_years: Optional[int] = None
    time_at_address_months: Optional[int] = None
    housing_type: Optional[str] = None
    rent_amount: Optional[str] = None
    id_uploaded: bool = False
    id_file_url: Optional[str] = None
    income_proof_uploaded: bool = False
    income_proof_file_url: Optional[str] = None
    residence_proof_uploaded: bool = False
    residence_proof_file_url: Optional[str] = None
    last_record_date: Optional[str] = None
    sold_count: int = 0
    created_at: str
    created_by: Optional[str] = None
    is_deleted: bool = False
    salesperson_id: Optional[str] = None
    salesperson_name: Optional[str] = None
    last_contacted_at: Optional[str] = None
    opt_out_sms: bool = False
