"""Alert deduplication: suppress repeated identical alerts within a time window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional, Tuple

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DedupConfig:
    window_seconds: int = 300  # suppress duplicates within this window

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


# Key: (job_name, alert_level)
_DedupKey = Tuple[str, AlertLevel]


class AlertDeduplicator:
    """Tracks recently sent alerts and suppresses duplicates within a window."""

    def __init__(
        self,
        config: Optional[DedupConfig] = None,
        now_fn: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._config = config or DedupConfig()
        self._now = now_fn
        # maps key -> timestamp of last forwarded alert
        self._last_sent: Dict[_DedupKey, datetime] = {}
        self._suppressed: int = 0
        self._forwarded: int = 0

    def _key(self, alert: Alert) -> _DedupKey:
        return (alert.job_name, alert.level)

    def should_send(self, alert: Alert) -> bool:
        """Return True if the alert should be forwarded (not a duplicate)."""
        key = self._key(alert)
        now = self._now()
        last = self._last_sent.get(key)
        if last is None:
            return True
        window = timedelta(seconds=self._config.window_seconds)
        return (now - last) >= window

    def record_sent(self, alert: Alert) -> None:
        """Mark an alert as having been forwarded right now."""
        self._last_sent[self._key(alert)] = self._now()
        self._forwarded += 1

    def record_suppressed(self) -> None:
        self._suppressed += 1

    def reset(self, job_name: str) -> None:
        """Clear dedup state for a specific job (e.g. after recovery)."""
        keys_to_remove = [k for k in self._last_sent if k[0] == job_name]
        for k in keys_to_remove:
            del self._last_sent[k]

    @property
    def suppressed(self) -> int:
        return self._suppressed

    @property
    def forwarded(self) -> int:
        return self._forwarded
