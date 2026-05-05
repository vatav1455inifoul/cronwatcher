"""Tracks cron job execution history and detects missed/delayed runs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from cronwatcher.schedule import CronSchedule


@dataclass
class JobStatus:
    name: str
    last_run: Optional[datetime] = None
    last_expected: Optional[datetime] = None
    missed_count: int = 0
    delay_seconds: float = 0.0

    @property
    def is_delayed(self) -> bool:
        return self.delay_seconds > 0

    @property
    def is_missed(self) -> bool:
        return self.missed_count > 0


class JobTracker:
    """Tracks execution state for a named cron job."""

    def __init__(self, name: str, expression: str, tolerance_seconds: float = 60.0):
        self.name = name
        self.schedule = CronSchedule(expression)
        self.tolerance = tolerance_seconds
        self._last_run: Optional[datetime] = None

    def record_run(self, at: Optional[datetime] = None) -> JobStatus:
        """Record that the job ran, optionally at a specific time."""
        now = at or datetime.utcnow()
        self._last_run = now
        expected = self.schedule.last_expected_run(now)
        delay = max(0.0, (now - expected).total_seconds()) if expected else 0.0
        return JobStatus(
            name=self.name,
            last_run=now,
            last_expected=expected,
            missed_count=0,
            delay_seconds=delay,
        )

    def check(self, at: Optional[datetime] = None) -> JobStatus:
        """Check current job status without recording a run."""
        now = at or datetime.utcnow()
        expected = self.schedule.last_expected_run(now)
        missed = 0
        delay = 0.0

        if expected is not None:
            if self._last_run is None or self._last_run < expected:
                overdue = (now - expected).total_seconds()
                if overdue > self.tolerance:
                    missed = 1
            elif self._last_run >= expected:
                delay = max(0.0, (self._last_run - expected).total_seconds())

        return JobStatus(
            name=self.name,
            last_run=self._last_run,
            last_expected=expected,
            missed_count=missed,
            delay_seconds=delay,
        )
