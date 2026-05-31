from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class CameraCredentials:
    serial_number: str
    safety_code: str


@dataclass(slots=True)
class SessionEvent:
    event_type: str
    reason: str
    attempt: int
    ts_utc: datetime

    @staticmethod
    def now(event_type: str, reason: str, attempt: int) -> "SessionEvent":
        return SessionEvent(
            event_type=event_type,
            reason=reason,
            attempt=attempt,
            ts_utc=datetime.now(tz=timezone.utc),
        )

