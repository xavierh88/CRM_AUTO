"""Source is independent from who acquired the lead; never infer AI credit."""
from enum import Enum
from pydantic import ConfigDict
from .common import DomainModel


class Source(str, Enum):
    FACEBOOK = 'Facebook'
    INSTAGRAM = 'Instagram'
    GOOGLE = 'Google'
    WEBSITE = 'Website'
    AI_CHAT = 'AI Chat'
    PHONE = 'Phone'
    WALK_IN = 'Walk-in'
    REFERRAL = 'Referral'
    EXISTING_CLIENT = 'Existing Client'
    MANUAL_CRM = 'Manual CRM'
    PREQUALIFY = 'Prequalify'


class AcquisitionType(str, Enum):
    AI_ACQUIRED = 'AI_ACQUIRED'
    AI_ASSISTED = 'AI_ASSISTED'
    HUMAN_ACQUIRED = 'HUMAN_ACQUIRED'
    EXISTING_CUSTOMER = 'EXISTING_CUSTOMER'


class Attribution(DomainModel):
    model_config = ConfigDict(str_strip_whitespace=False)
    source: Source | None = None
    acquisition_type: AcquisitionType | None = None
    legacy_source: str | None = None


def map_source(value: str | None) -> Attribution:
    source = next((source for source in Source if value is not None and source.value.casefold() == value.strip().casefold()), None)
    return Attribution(source=source, legacy_source=value)
