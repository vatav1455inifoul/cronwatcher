"""Alerter wrapper that drops notifications exceeding the rate limit."""

from __future__ import annotations

from typing import List

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.rate_limiter import BucketConfig, RateLimiter


class RateLimitedAlerter:
    """Wraps an :class:`Alerter` and suppresses bursts via a token bucket.

    Each job gets its own bucket.  When the bucket is empty the alert is
    recorded in ``suppressed`` but not forwarded to the inner alerter.
    """

    def __init__(self, alerter: Alerter, config: BucketConfig) -> None:
        self._alerter = alerter
        self._limiter = RateLimiter(config)
        self.suppressed: List[Alert] = []

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _send(self, alert: Alert) -> None:
        if self._limiter.allow(alert.job_name):
            self._alerter.send(alert)
        else:
            self.suppressed.append(alert)

    # ------------------------------------------------------------------
    # public API (mirrors Alerter)
    # ------------------------------------------------------------------

    def send(self, alert: Alert) -> None:
        self._send(alert)

    def alert_missed(self, job_name: str) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=f"{job_name} missed its scheduled run",
        )
        self._send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=(
                f"{job_name} ran {delay_seconds:.1f}s late"
            ),
        )
        self._send(alert)

    def reset(self, job_name: str) -> None:
        """Restore full token allowance for *job_name* (e.g. after recovery)."""
        self._limiter.reset(job_name)

    @property
    def suppressed_count(self) -> int:
        return len(self.suppressed)
