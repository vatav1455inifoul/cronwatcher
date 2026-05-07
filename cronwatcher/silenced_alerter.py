"""Alerter wrapper that skips notifications for silenced jobs."""

from __future__ import annotations

from typing import List

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.silencer import Silencer


class SilencedAlerter:
    """Wraps an Alerter and suppresses alerts for jobs covered by a Silencer."""

    def __init__(self, alerter: Alerter, silencer: Silencer) -> None:
        self._alerter = alerter
        self._silencer = silencer
        self._suppressed: List[Alert] = []

    # ------------------------------------------------------------------
    # Public interface mirrors Alerter
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> None:
        if self._silencer.is_silenced(alert.job_name):
            self._suppressed.append(alert)
            return
        self._alerter.send(alert)

    def alert_missed(self, job_name: str, seconds_overdue: float) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=f"{job_name} missed its scheduled run ({seconds_overdue:.0f}s overdue)",
        )
        self.send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=f"{job_name} ran late by {delay_seconds:.0f}s",
        )
        self.send(alert)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def suppressed(self) -> List[Alert]:
        return list(self._suppressed)

    @property
    def suppressed_count(self) -> int:
        return len(self._suppressed)
