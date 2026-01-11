"""Pre-Qualify submission models"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

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
    timeAtAddressYears: Optional[int] = None
    timeAtAddressMonths: Optional[int] = None
    employerName: Optional[str] = None
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    estimatedDownPayment: Optional[str] = None
    consentAccepted: bool = False

class PreQualifyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
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
    timeAtAddressYears: Optional[int] = None
    timeAtAddressMonths: Optional[int] = None
    employerName: Optional[str] = None
    timeWithEmployerYears: Optional[int] = None
    timeWithEmployerMonths: Optional[int] = None
    incomeType: Optional[str] = None
    netIncome: Optional[str] = None
    incomeFrequency: Optional[str] = None
    estimatedDownPayment: Optional[str] = None
    consentAccepted: bool = False
    created_at: str
    status: str = "pending"
    matched_client_id: Optional[str] = None
    matched_client_name: Optional[str] = None
    id_file_url: Optional[str] = None
