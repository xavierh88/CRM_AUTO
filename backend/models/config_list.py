"""Config list models for dynamic dropdowns (banks, dealers, cars, etc.)"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ConfigListItem(BaseModel):
    name: str
    category: str  # bank, dealer, car, id_type, poi_type, por_type

class ConfigListItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    created_at: str
    created_by: Optional[str] = None
