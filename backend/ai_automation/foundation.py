"""Typed proposals and fail-closed dispatch. Authority comes only from the host."""
from datetime import datetime, timedelta
from typing import Annotated, Literal, Protocol

from pydantic import Field, TypeAdapter
from ..commercial.common import DomainModel, Identifier
from ..commercial.inventory import Vehicle, VehiclePreference


class MatchRequest(DomainModel):
    tool: Literal['match_vehicle'] = 'match_vehicle'
    preference: VehiclePreference = Field(default_factory=VehiclePreference)


class UpdateAppointment(DomainModel):
    tool: Literal['update_appointment'] = 'update_appointment'
    appointment_id: Identifier
    status: Literal['CONFIRMED', 'RUNNING_LATE', 'CANCELLED', 'NO_SHOW']


Request = Annotated[MatchRequest | UpdateAppointment, Field(discriminator='tool')]
_REQUEST = TypeAdapter(Request)


class Permissions(Protocol):
    def require(self, actor: object, request: Request) -> None:
        """Raise unless authenticated actor may access this tenant/object/action."""

    def consume_confirmation(self, actor: object, request: UpdateAppointment) -> bool:
        """Consume trusted, unexpired, single-use human approval bound to exact intent."""


class CRMTools(Protocol):
    def match_vehicle(self, actor: object, request: MatchRequest) -> tuple['Match', ...]: ...
    def update_appointment(self, actor: object, request: UpdateAppointment) -> object: ...


class Jarvis:
    """Host injects permission engine, typed CRM API and durable audit sink.

    This object never receives a database handle. CRM methods must recheck scope
    at persistence time. Audit errors block dispatch; failed writes are never retried.
    """
    def __init__(self, permissions: Permissions, api: CRMTools, audit):
        self._permissions, self._api, self._audit = permissions, api, audit

    @staticmethod
    def parse(payload: dict) -> Request:
        return _REQUEST.validate_python(payload)

    def execute(self, actor: object, payload: dict):
        request = self.parse(payload)
        try:
            self._permissions.require(actor, request)
            if isinstance(request, UpdateAppointment):
                if self._permissions.consume_confirmation(actor, request) is not True:
                    raise PermissionError('Trusted confirmation required')
        except PermissionError:
            self._audit(actor, request.tool, 'DENIED')
            raise
        self._audit(actor, request.tool, 'AUTHORIZED_ATTEMPT')
        try:
            if isinstance(request, MatchRequest):
                result = self._api.match_vehicle(actor, request)
            else:
                result = self._api.update_appointment(actor, request)
        except Exception:
            self._audit(actor, request.tool, 'FAILED_REQUIRES_REVIEW')
            raise
        self._audit(actor, request.tool, 'SUCCEEDED')
        return result


class Match(DomainModel):
    vehicle_id: Identifier
    reasons: tuple[str, ...]
    provider_status: Literal['MOCK'] = 'MOCK'


def match_vehicles(inventory: list[Vehicle], preference: VehiclePreference) -> tuple[Match, ...]:
    """Hard constraints, then lowest asking price and stable ID; no credit inference."""
    result = []
    for vehicle in sorted(inventory, key=lambda v: (v.asking_price, v.vehicle_id)):
        if vehicle.availability != 'AVAILABLE':
            continue
        if preference.budget is not None and vehicle.asking_price > preference.budget:
            continue
        if preference.min_year is not None and vehicle.year < preference.min_year:
            continue
        if preference.max_year is not None and vehicle.year > preference.max_year:
            continue
        if preference.body_type and vehicle.body_type.casefold() != preference.body_type.casefold():
            continue
        reasons = ['AVAILABLE', 'MATCHES_FILTERS']
        if (preference.down_payment is not None or preference.payment_preference is not None
                or preference.credit_constraints):
            reasons.append('FINANCING_REVIEW_REQUIRED')
        result.append(Match(vehicle_id=vehicle.vehicle_id, reasons=tuple(reasons)))
    return tuple(result)


def _aware(*values):
    if any(not isinstance(v, datetime) or v.utcoffset() is None for v in values):
        raise ValueError('Timezone-aware timestamps required')


def guardian(status: str, scheduled_at: datetime, now: datetime) -> str:
    """Recommendations only: elapsed time never automatically marks a no-show."""
    _aware(scheduled_at, now)
    if status not in {'SCHEDULED', 'CONFIRMED', 'RUNNING_LATE', 'CANCELLED', 'COMPLETED', 'NO_SHOW'}:
        raise ValueError('Unknown appointment status')
    if status == 'NO_SHOW':
        return 'RECOVERY_REVIEW'
    if status in {'CANCELLED', 'COMPLETED'}:
        return 'NONE'
    if scheduled_at < now:
        return 'REVIEW_NO_SHOW'
    return 'REMIND' if scheduled_at - now <= timedelta(hours=24) else 'NONE'


class Recovery(DomainModel):
    priority: Literal['HOT', 'WARM', 'COLD']
    reasons: tuple[str, ...]
    action: Literal['HUMAN_REVIEW', 'NONE']
    provider_status: Literal['PENDING_EXTERNAL'] = 'PENDING_EXTERNAL'


def recovery(now: datetime, *, last_activity: datetime | None = None,
             no_show: bool = False, no_reply: bool = False,
             abandoned_prequalify: bool = False, never_contacted: bool = False) -> Recovery:
    _aware(now, *([last_activity] if last_activity is not None else []))
    if any(type(flag) is not bool for flag in (no_show, no_reply, abandoned_prequalify, never_contacted)):
        raise ValueError('Recovery flags must be booleans')
    if last_activity is not None and last_activity > now:
        raise ValueError('Activity cannot be in the future')
    reasons = [name for name, flag in (
        ('NO_SHOW', no_show), ('NO_REPLY', no_reply),
        ('ABANDONED_PREQUALIFY', abandoned_prequalify), ('NEVER_CONTACTED', never_contacted)
    ) if flag]
    if last_activity is None:
        reasons.append('NO_ACTIVITY')
    elif now - last_activity >= timedelta(days=7):
        reasons.append('STALE')
    priority = 'HOT' if no_show or abandoned_prequalify else 'WARM' if reasons else 'COLD'
    return Recovery(priority=priority, reasons=tuple(reasons), action='HUMAN_REVIEW' if reasons else 'NONE')


from dataclasses import dataclass
from threading import Lock
import time


@dataclass(frozen=True)
class TrustedContext:
    """Created by authenticated host only, never deserialized from LLM JSON.

    Grants are tenant-scoped (tool, object_id) pairs from current CRM policy.
    The empty object ID grants inventory matching only.
    """
    user_id: str
    tenant_id: str
    session_id: str
    grants: frozenset[tuple[str, str]]


class PermissionEngine:
    """Process-local foundation. Confirmation entry point belongs to human UI only."""
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._approvals = {}
        self._lock = Lock()

    def require(self, actor, request):
        if (not isinstance(actor, TrustedContext)
                or not all(isinstance(v, str) and v.strip() for v in
                           (actor.user_id, actor.tenant_id, actor.session_id))):
            raise PermissionError('Authenticated context required')
        target = request.appointment_id if isinstance(request, UpdateAppointment) else ''
        if (request.tool, target) not in actor.grants:
            raise PermissionError('Tool or object access denied')

    def _key(self, actor, request):
        self.require(actor, request)
        return (actor.user_id, actor.tenant_id, actor.session_id, request.model_dump_json())

    def confirm(self, actor, request: UpdateAppointment):
        """Trusted human endpoint calls this after displaying exact validated intent."""
        key = self._key(actor, request)
        with self._lock:
            now = self._clock()
            self._approvals = {k: expiry for k, expiry in self._approvals.items() if expiry > now}
            if len(self._approvals) >= 1000:
                raise PermissionError('Confirmation capacity exceeded')
            self._approvals[key] = now + 120

    def consume_confirmation(self, actor, request):
        key = self._key(actor, request)
        with self._lock:
            expiry = self._approvals.pop(key, None)
            return expiry is not None and self._clock() < expiry
