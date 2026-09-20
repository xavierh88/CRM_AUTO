"""Conservative, non-mutating compatibility projection; never a bulk migration."""
from copy import deepcopy
from enum import Enum
from typing import Any, Mapping
from .common import DomainModel


class Stage(str, Enum):
    NEW_LEAD = 'NEW LEAD'
    CONTACTED = 'CONTACTED'
    ENGAGED = 'ENGAGED'
    PREQUALIFY = 'PREQUALIFY'
    APPLIED = 'APPLIED'
    APPROVED = 'APPROVED'
    CONDITIONAL = 'CONDITIONAL'
    DECLINED = 'DECLINED'
    APPOINTMENT = 'APPOINTMENT'
    SHOW = 'SHOW'
    NEGOTIATING = 'NEGOTIATING'
    PENDING_DEAL = 'PENDING DEAL'
    STOP_HOLD = 'STOP/HOLD'
    SOLD = 'SOLD'
    LOST = 'LOST'


class PipelineProjection(DomainModel):
    stage: Stage | None
    source_field: str | None
    legacy_value: str | None
    needs_review: bool


def map_legacy(record: Mapping[str, Any]) -> PipelineProjection:
    # An explicit canonical value wins, including invalid values needing review.
    if record.get('commercial_stage') is not None:
        value = record['commercial_stage']
        try:
            stage = Stage(value)
        except (ValueError, TypeError):
            stage = None
        return PipelineProjection(stage=stage, source_field='commercial_stage', legacy_value=str(value), needs_review=stage is None)
    if record.get('record_status') == 'completed':
        return PipelineProjection(stage=Stage.SOLD, source_field='record_status', legacy_value='completed', needs_review=False)
    appointments = {'agendado': Stage.APPOINTMENT, 'confirmado': Stage.APPOINTMENT, 'reagendado': Stage.APPOINTMENT, 'scheduled': Stage.APPOINTMENT, 'cumplido': Stage.SHOW}
    value = record.get('appointment_status')
    if isinstance(value, str) and value in appointments:
        return PipelineProjection(stage=appointments[value], source_field='appointment_status', legacy_value=value, needs_review=False)
    value = record.get('record_status')
    return PipelineProjection(stage=None, source_field='record_status' if value is not None else None, legacy_value=str(value) if value is not None else None, needs_review=True)


def transition(record: Mapping[str, Any], target: Stage | str) -> dict[str, Any]:
    """Return a detached candidate; caller owns authorization, audit and persistence.

    No linear transition policy is assumed: hold/recovery/reopening are valid.
    """
    stage = Stage(target)
    result = deepcopy(dict(record))
    result['commercial_stage'] = stage.value
    return result
