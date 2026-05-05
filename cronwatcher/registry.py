"""Registry for managing multiple tracked cron jobs."""

from datetime import datetime
from typing import Dict, Iterator, List, Optional

from cronwatcher.tracker import JobStatus, JobTracker


class JobRegistry:
    """Central registry for all monitored cron jobs."""

    def __init__(self, default_tolerance: float = 60.0):
        self._jobs: Dict[str, JobTracker] = {}
        self.default_tolerance = default_tolerance

    def register(self, name: str, expression: str, tolerance_seconds: Optional[float] = None) -> JobTracker:
        """Register a new job or overwrite an existing one."""
        tolerance = tolerance_seconds if tolerance_seconds is not None else self.default_tolerance
        tracker = JobTracker(name, expression, tolerance)
        self._jobs[name] = tracker
        return tracker

    def record_run(self, name: str, at: Optional[datetime] = None) -> JobStatus:
        """Record a run for a named job. Raises KeyError if not registered."""
        return self._jobs[name].record_run(at)

    def check(self, name: str, at: Optional[datetime] = None) -> JobStatus:
        """Check status of a single job."""
        return self._jobs[name].check(at)

    def check_all(self, at: Optional[datetime] = None) -> List[JobStatus]:
        """Return status for all registered jobs."""
        return [tracker.check(at) for tracker in self._jobs.values()]

    def alerts(self, at: Optional[datetime] = None) -> List[JobStatus]:
        """Return only jobs that are missed or delayed beyond tolerance."""
        return [s for s in self.check_all(at) if s.is_missed or s.is_delayed]

    def __contains__(self, name: str) -> bool:
        return name in self._jobs

    def __iter__(self) -> Iterator[str]:
        return iter(self._jobs)

    def __len__(self) -> int:
        return len(self._jobs)
