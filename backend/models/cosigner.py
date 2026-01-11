"""Co-signer relation models"""
from pydantic import BaseModel, ConfigDict

class CoSignerRelationCreate(BaseModel):
    buyer_client_id: str
    cosigner_client_id: str

class CoSignerRelationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    buyer_client_id: str
    cosigner_client_id: str
    created_at: str
