"""WhatsApp human-first eligibility only; never schedules or sends AI messages."""
from datetime import datetime, timedelta

from .models import aware


class WhatsAppHandoff:
    def __init__(self, human_window_seconds: int = 60):
        if human_window_seconds < 1:
            raise ValueError('Positive human response window required')
        self.window = timedelta(seconds=human_window_seconds)
        self.last_inbound = None
        self.human_active = False

    def inbound(self, now: datetime):
        aware(now)
        if self.last_inbound is not None and now < self.last_inbound:
            raise ValueError('Out-of-order inbound event')
        self.last_inbound = now

    def human_takeover(self):
        self.human_active = True

    def release_to_ai(self, now: datetime):
        self.inbound(now)
        self.human_active = False

    def ai_allowed(self, now: datetime) -> bool:
        aware(now)
        return (not self.human_active and self.last_inbound is not None
                and now >= self.last_inbound + self.window)
