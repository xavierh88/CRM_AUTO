"""User Record (Oportunidad/Cartilla) models"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

class UserRecordCreate(BaseModel):
    client_id: str
    has_id: bool = False
    id_type: Optional[str] = None
    has_poi: bool = False
    poi_type: Optional[str] = None
    ssn: bool = False
    itin: bool = False
    self_employed: bool = False
    self_employed_docs: List[str] = Field(default_factory=list)
    has_por: bool = False
    por_types: List[str] = Field(default_factory=list)
    bank: Optional[str] = None
    bank_deposit_type: Optional[str] = None
    down_payment_type: List[str] = Field(default_factory=list)
    down_payment_cash: Optional[str] = None
    down_payment_card: Optional[str] = None
    trade_make: Optional[str] = None
    trade_model: Optional[str] = None
    trade_year: Optional[str] = None
    trade_title: Optional[str] = None
    trade_miles: Optional[str] = None
    trade_plate: Optional[str] = None
    trade_estimated_value: Optional[str] = None
    auto: bool = False
    credit: bool = False
    auto_loan: Optional[List[str]] = None
    dealer: Optional[str] = None
    finance_status: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[str] = None
    sale_day: Optional[str] = None
    sale_year: Optional[str] = None
    record_status: Optional[str] = None
    approved_amount: Optional[str] = None
    contract_amount: Optional[str] = None
    down_payment_final: Optional[str] = None
    commission_amount: Optional[str] = None
    commission_paid: bool = False
    commission_due_date: Optional[str] = None
    employment_type: Optional[str] = None
    employment_company_name: Optional[str] = None
    employment_time_years: Optional[int] = None
    employment_time_months: Optional[int] = None
    income_frequency: Optional[str] = None
    net_income_amount: Optional[str] = None
    collaborator_id: Optional[str] = None
    collaborator_name: Optional[str] = None
    collaborator_commission: Optional[str] = None
    collaborator_paid: bool = False

class UserRecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    salesperson_id: Optional[str] = None
    salesperson_name: Optional[str] = None
    has_id: bool = False
    id_type: Optional[str] = None
    has_poi: bool = False
    poi_type: Optional[str] = None
    ssn: bool = False
    itin: bool = False
    self_employed: bool = False
    self_employed_docs: List[str] = Field(default_factory=list)
    has_por: bool = False
    por_types: List[str] = Field(default_factory=list)
    bank: Optional[str] = None
    bank_deposit_type: Optional[str] = None
    down_payment_type: List[str] = Field(default_factory=list)
    down_payment_cash: Optional[str] = None
    down_payment_card: Optional[str] = None
    trade_make: Optional[str] = None
    trade_model: Optional[str] = None
    trade_year: Optional[str] = None
    trade_title: Optional[str] = None
    trade_miles: Optional[str] = None
    trade_plate: Optional[str] = None
    trade_estimated_value: Optional[str] = None
    auto: bool = False
    credit: bool = False
    auto_loan: Optional[List[str]] = None
    dealer: Optional[str] = None
    finance_status: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_year: Optional[str] = None
    sale_month: Optional[str] = None
    sale_day: Optional[str] = None
    sale_year: Optional[str] = None
    created_at: str
    is_deleted: bool = False
    previous_record_id: Optional[str] = None
    opportunity_number: int = 1
    record_status: Optional[str] = None
    approved_amount: Optional[str] = None
    contract_amount: Optional[str] = None
    down_payment_final: Optional[str] = None
    commission_amount: Optional[str] = None
    commission_paid: bool = False
    commission_due_date: Optional[str] = None
    employment_type: Optional[str] = None
    employment_company_name: Optional[str] = None
    employment_time_years: Optional[int] = None
    employment_time_months: Optional[int] = None
    income_frequency: Optional[str] = None
    net_income_amount: Optional[str] = None
    collaborator_id: Optional[str] = None
    collaborator_name: Optional[str] = None
    collaborator_commission: Optional[str] = None
    collaborator_paid: bool = False
