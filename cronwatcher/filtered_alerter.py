"""Alerter wrapper that applies an AlertFilter before dispatching."""
from __future__ import annotations

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.filter import AlertFilter


class FilteredAlerter:
    """Wraps an :class:`Alerter` and silently drops alerts that match the filter."""

    def __init__(self, alerter: Alerter, alert_filter: AlertFilter) -> None:
        self._alerter = alerter
        self._filter = alert_filter
        self._suppressed: list[Alert] = []

    # ------------------------------------------------------------------
    # Public API mirrors Alerter so callers can swap one for the other
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> bool:
        """Send *alert* through the inner alerter unless the filter suppresses it.

        Returns True if the alert was forwarded, False if suppressed.
        """
        if self._filter.should_suppress(alert):
            self._suppressed.append(alert)
            return False
        self._alerter.send(alert)
        return True

    def alert_missed(self, job_name: str, seconds_overdue: float) -> bool:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=f"{job_name} missed its scheduled run ({seconds_overdue:.0f}s overdue)",
        )
        return self.send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> bool:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=f"{job_name} ran late by {delay_seconds:.0f}s",
        )
        return self.send(alert)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def suppressed(self) -> list[Alert]:
        """All alerts that were suppressed (read-only copy)."""
        return list(self._suppressed)

    @property
    def suppressed_count(self) -> int:
        return len(self._suppressed)

    @property
    def history(self) -> list[Alert]:
        """Forwarded alert history from the inner alerter."""
        return self._alerter.history
