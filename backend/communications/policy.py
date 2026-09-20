"""Conservative configurable contact controls, not a legal compliance determination."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .models import aware


@dataclass(frozen=True)
class ContactPolicy:
    consent: bool = False
    opted_out: bool = False
    timezone_name: str = 'UTC'
    quiet_start: int = 21
    quiet_end: int = 8
    frequency_cap: int = 3

    def __post_init__(self):
        ZoneInfo(self.timezone_name)
        if type(self.consent) is not bool or type(self.opted_out) is not bool:
            raise ValueError('Consent and opt-out must be booleans')
        if type(self.frequency_cap) is not int or self.frequency_cap < 1:
            raise ValueError('Positive integer frequency cap required')
        if any(type(hour) is not int or not 0 <= hour <= 23
               for hour in (self.quiet_start, self.quiet_end)):
            raise ValueError('Quiet hours must be integers in 0..23')

    def reason(self, now: datetime, sent_at: list[datetime]) -> str | None:
        aware(now)
        if self.opted_out:
            return 'OPTED_OUT'
        if not self.consent:
            return 'CONSENT_REQUIRED'
        hour = now.astimezone(ZoneInfo(self.timezone_name)).hour
        if self.quiet_start < self.quiet_end:
            quiet = self.quiet_start <= hour < self.quiet_end
        else:
            quiet = hour >= self.quiet_start or hour < self.quiet_end
        if quiet:
            return 'QUIET_HOURS'
        if sum(now - timedelta(days=1) < timestamp <= now for timestamp in sent_at) >= self.frequency_cap:
            return 'FREQUENCY_CAP'
        return None
