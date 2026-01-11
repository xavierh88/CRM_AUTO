"""
Pydantic models for DealerCRM
"""
from .user import UserCreate, UserActivate, UserRoleUpdate, UserLogin, UserResponse
from .client import ClientCreate, ClientResponse
from .record import UserRecordCreate, UserRecordResponse
from .appointment import AppointmentCreate, AppointmentResponse
from .cosigner import CoSignerRelationCreate, CoSignerRelationResponse
from .config_list import ConfigListItem, ConfigListItemResponse
from .prequalify import PreQualifySubmission, PreQualifyResponse

__all__ = [
    # User models
    'UserCreate', 'UserActivate', 'UserRoleUpdate', 'UserLogin', 'UserResponse',
    # Client models
    'ClientCreate', 'ClientResponse',
    # Record models
    'UserRecordCreate', 'UserRecordResponse',
    # Appointment models
    'AppointmentCreate', 'AppointmentResponse',
    # Co-signer models
    'CoSignerRelationCreate', 'CoSignerRelationResponse',
    # Config list models
    'ConfigListItem', 'ConfigListItemResponse',
    # Pre-qualify models
    'PreQualifySubmission', 'PreQualifyResponse',
]
