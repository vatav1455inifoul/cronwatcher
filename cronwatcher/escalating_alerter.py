"""Alerter wrapper that applies escalation policy before forwarding alerts."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.escalation import EscalationPolicy, EscalationTracker


class EscalatingAlerter:
    """Wraps an Alerter and escalates alert levels on repeated misses."""

    def __init__(
        self,
        inner: Alerter,
        policy: Optional[EscalationPolicy] = None,
    ) -> None:
        self._inner = inner
        self._tracker = EscalationTracker(policy)
        self._escalated: List[Alert] = []

    # ------------------------------------------------------------------
    # Public API mirrors Alerter
    # ------------------------------------------------------------------

    def alert_missed(self, job_name: str, message: str = "") -> None:
        raw = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=message or f"{job_name} missed",
        )
        escalated = self._tracker.escalate_alert(raw)
        self._escalated.append(escalated)
        self._inner.send(escalated)

    def alert_delayed(self, job_name: str, message: str = "") -> None:
        """Delayed runs don't escalate — forward as WARNING and reset counter."""
        self._tracker.record_ok(job_name)
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=message or f"{job_name} delayed",
        )
        self._inner.send(alert)

    def record_ok(self, job_name: str) -> None:
        """Notify tracker that the job ran successfully."""
        self._tracker.record_ok(job_name)

    def consecutive_misses(self, job_name: str) -> int:
        return self._tracker.consecutive_misses(job_name)

    @property
    def escalated(self) -> List[Alert]:
        """All alerts that were sent through escalation."""
        return list(self._escalated)
