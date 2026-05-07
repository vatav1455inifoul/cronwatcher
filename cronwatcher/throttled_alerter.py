"""Alerter wrapper that applies throttle rules before dispatching alerts."""

from __future__ import annotations

from typing import List, Optional

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.throttle import AlertThrottle, ThrottleRule


_DEFAULT_RULES: List[ThrottleRule] = [
    ThrottleRule(AlertLevel.WARNING, 600),   # 10 min cooldown for warnings
    ThrottleRule(AlertLevel.CRITICAL, 300),  # 5 min cooldown for critical
]


class ThrottledAlerter:
    """Wraps an Alerter with per-level throttle rules.

    Alerts that fire too frequently for the same job+level are silently
    dropped until the cooldown window has elapsed.
    """

    def __init__(
        self,
        alerter: Alerter,
        rules: Optional[List[ThrottleRule]] = None,
    ) -> None:
        self._alerter = alerter
        self._throttle = AlertThrottle(rules if rules is not None else _DEFAULT_RULES)

    # ------------------------------------------------------------------
    # Public API mirrors Alerter so it can be used as a drop-in.
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> bool:
        """Forward alert to the inner alerter if not throttled.

        Returns True if the alert was dispatched, False if suppressed.
        """
        return self._throttle.send(alert, self._alerter)

    def alert_missed(self, job_name: str) -> bool:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=f"Job '{job_name}' has missed its scheduled run.",
        )
        return self.send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> bool:
        mins = delay_seconds / 60
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=f"Job '{job_name}' ran {mins:.1f} min late.",
        )
        return self.send(alert)

    def reset(self, job_name: str, level: Optional[AlertLevel] = None) -> None:
        """Clear throttle state — useful after a job recovers."""
        self._throttle.reset(job_name, level)

    @property
    def history(self):
        """Expose inner alerter history for inspection."""
        return self._alerter.history
