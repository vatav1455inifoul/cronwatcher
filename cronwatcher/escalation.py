"""Alert escalation policy: re-alert at increasing severity after repeated misses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EscalationPolicy:
    """Defines how many consecutive misses before escalating to CRITICAL."""
    warn_after: int = 1    # send WARNING after this many consecutive misses
    critical_after: int = 3  # escalate to CRITICAL after this many

    def __post_init__(self) -> None:
        if self.warn_after < 1:
            raise ValueError("warn_after must be >= 1")
        if self.critical_after < self.warn_after:
            raise ValueError("critical_after must be >= warn_after")

    def level_for(self, consecutive_misses: int) -> AlertLevel:
        if consecutive_misses >= self.critical_after:
            return AlertLevel.CRITICAL
        if consecutive_misses >= self.warn_after:
            return AlertLevel.WARNING
        return AlertLevel.INFO


@dataclass
class EscalationState:
    consecutive_misses: int = 0
    last_escalation: Optional[datetime] = None


class EscalationTracker:
    """Tracks consecutive misses per job and computes escalated alert level."""

    def __init__(self, policy: Optional[EscalationPolicy] = None) -> None:
        self._policy = policy or EscalationPolicy()
        self._states: Dict[str, EscalationState] = {}

    def _state(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState()
        return self._states[job_name]

    def record_miss(self, job_name: str) -> AlertLevel:
        """Increment miss counter and return the escalated AlertLevel."""
        st = self._state(job_name)
        st.consecutive_misses += 1
        st.last_escalation = _utcnow()
        return self._policy.level_for(st.consecutive_misses)

    def record_ok(self, job_name: str) -> None:
        """Reset miss counter when a job runs successfully."""
        if job_name in self._states:
            self._states[job_name].consecutive_misses = 0

    def consecutive_misses(self, job_name: str) -> int:
        return self._state(job_name).consecutive_misses

    def escalate_alert(self, alert: Alert) -> Alert:
        """Return a new Alert with the escalated level based on miss history."""
        level = self.record_miss(alert.job_name)
        return Alert(job_name=alert.job_name, level=level, message=alert.message)
