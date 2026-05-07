"""Alert throttling to prevent repeated notifications for the same issue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ThrottleRule:
    """Defines how often an alert of a given level may fire for a job."""

    def __init__(self, level: AlertLevel, min_interval_seconds: int) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0")
        self.level = level
        self.min_interval = timedelta(seconds=min_interval_seconds)


class AlertThrottle:
    """Wraps an Alerter and suppresses duplicate alerts within a cooldown window."""

    def __init__(self, rules: Optional[list[ThrottleRule]] = None) -> None:
        # (job_name, level) -> last sent time
        self._last_sent: Dict[Tuple[str, AlertLevel], datetime] = {}
        self._rules: Dict[AlertLevel, timedelta] = {}
        if rules:
            for rule in rules:
                self._rules[rule.level] = rule.min_interval

    def _min_interval(self, level: AlertLevel) -> timedelta:
        return self._rules.get(level, timedelta(0))

    def should_send(self, alert: Alert) -> bool:
        """Return True if the alert should be forwarded, False if throttled."""
        key = (alert.job_name, alert.level)
        interval = self._min_interval(alert.level)
        if interval.total_seconds() == 0:
            return True
        last = self._last_sent.get(key)
        if last is None:
            return True
        return (_utcnow() - last) >= interval

    def record(self, alert: Alert) -> None:
        """Mark an alert as sent now."""
        key = (alert.job_name, alert.level)
        self._last_sent[key] = _utcnow()

    def send(self, alert: Alert, alerter) -> bool:
        """Send alert through alerter only if not throttled. Returns True if sent."""
        if self.should_send(alert):
            alerter.send(alert)
            self.record(alert)
            return True
        return False

    def reset(self, job_name: str, level: Optional[AlertLevel] = None) -> None:
        """Clear throttle state for a job (optionally for a specific level)."""
        keys = [k for k in self._last_sent if k[0] == job_name]
        if level is not None:
            keys = [k for k in keys if k[1] == level]
        for k in keys:
            del self._last_sent[k]
