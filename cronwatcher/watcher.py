"""High-level watcher that ties registry + alerter together."""

from datetime import datetime
from typing import Optional

from cronwatcher.alerter import Alerter
from cronwatcher.registry import JobRegistry


class Watcher:
    """Coordinates job tracking and alert dispatch."""

    def __init__(
        self,
        alerter: Optional[Alerter] = None,
        delay_threshold: float = 60.0,
        miss_tolerance: float = 120.0,
    ) -> None:
        self.registry = JobRegistry(
            delay_threshold=delay_threshold,
            miss_tolerance=miss_tolerance,
        )
        self.alerter = alerter or Alerter()

    def register(self, name: str, expression: str) -> None:
        """Register a cron job by name and cron expression."""
        self.registry.register(name, expression)

    def record_run(self, name: str, at: Optional[datetime] = None) -> None:
        """Record a job execution and fire alerts if needed."""
        status = self.registry.record_run(name, at=at)
        if status.is_delayed:
            self.alerter.alert_delayed(name, status.delay_seconds)

    def check_all(self, now: Optional[datetime] = None) -> None:
        """Check all registered jobs for missed runs and fire alerts."""
        results = self.registry.check(now=now)
        for name, status in results.items():
            if status.is_missed:
                overdue = status.overdue_seconds if status.overdue_seconds is not None else 0.0
                self.alerter.alert_missed(name, overdue)

    def __repr__(self) -> str:
        jobs = list(self.registry)
        return f"Watcher(jobs={jobs})"
