"""Correlate related alerts across jobs to detect systemic failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class CorrelationGroup:
    """A group of alerts that fired within the same time window."""
    window_start: datetime
    window_end: datetime
    alerts: List[Alert] = field(default_factory=list)

    @property
    def job_names(self) -> List[str]:
        return [a.job_name for a in self.alerts]

    @property
    def is_systemic(self) -> bool:
        """True when multiple distinct jobs fired in this window."""
        return len(set(self.job_names)) >= 2

    @property
    def highest_level(self) -> AlertLevel:
        levels = [a.level for a in self.alerts]
        if AlertLevel.CRITICAL in levels:
            return AlertLevel.CRITICAL
        if AlertLevel.WARNING in levels:
            return AlertLevel.WARNING
        return AlertLevel.INFO

    def __str__(self) -> str:
        jobs = ", ".join(sorted(set(self.job_names)))
        return (
            f"CorrelationGroup({len(self.alerts)} alerts, "
            f"jobs=[{jobs}], systemic={self.is_systemic})"
        )


class AlertCorrelator:
    """Groups incoming alerts by time proximity."""

    def __init__(self, window_seconds: int = 60, _now=None) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = timedelta(seconds=window_seconds)
        self._now = _now or _utcnow
        self._pending: List[Alert] = []
        self._groups: List[CorrelationGroup] = []
        self._window_start: Optional[datetime] = None

    def observe(self, alert: Alert) -> Optional[CorrelationGroup]:
        """Record an alert; returns a group if the window just closed."""
        now = self._now()
        if self._window_start is None:
            self._window_start = now
        if now - self._window_start > self._window:
            group = self._flush()
            self._window_start = now
            self._pending.append(alert)
            return group
        self._pending.append(alert)
        return None

    def flush(self) -> Optional[CorrelationGroup]:
        """Force-close the current window and return the group."""
        return self._flush()

    def _flush(self) -> Optional[CorrelationGroup]:
        if not self._pending:
            return None
        now = self._now()
        group = CorrelationGroup(
            window_start=self._window_start or now,
            window_end=now,
            alerts=list(self._pending),
        )
        self._groups.append(group)
        self._pending.clear()
        self._window_start = None
        return group

    @property
    def groups(self) -> List[CorrelationGroup]:
        return list(self._groups)
