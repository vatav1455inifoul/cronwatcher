"""Job dependency tracking: alert when a job runs before its upstream jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class DependencyViolation:
    job: str
    missing_upstream: List[str]
    checked_at: datetime

    def __str__(self) -> str:
        ups = ", ".join(self.missing_upstream)
        return f"[{self.job}] ran before upstream(s) completed: {ups}"


class DependencyGraph:
    """Tracks upstream dependencies and last-run times for each job."""

    def __init__(self) -> None:
        self._deps: Dict[str, List[str]] = {}
        self._last_run: Dict[str, datetime] = {}

    def add_dependency(self, job: str, depends_on: str) -> None:
        """Declare that *job* must run after *depends_on*."""
        self._deps.setdefault(job, [])
        if depends_on not in self._deps[job]:
            self._deps[job].append(depends_on)

    def record_run(self, job: str, ran_at: Optional[datetime] = None) -> None:
        self._last_run[job] = ran_at or _utcnow()

    def check(self, job: str) -> Optional[DependencyViolation]:
        """Return a violation if any upstream of *job* has not run yet
        or ran *after* the current job's last run."""
        upstreams = self._deps.get(job, [])
        if not upstreams:
            return None
        job_ran_at = self._last_run.get(job)
        if job_ran_at is None:
            return None  # job hasn't run yet — nothing to validate
        missing: List[str] = []
        for up in upstreams:
            up_ran_at = self._last_run.get(up)
            if up_ran_at is None or up_ran_at > job_ran_at:
                missing.append(up)
        if missing:
            return DependencyViolation(job=job, missing_upstream=missing, checked_at=_utcnow())
        return None

    def check_all(self) -> List[DependencyViolation]:
        return [v for job in self._deps for v in [self.check(job)] if v]

    def jobs(self) -> Set[str]:
        return set(self._deps.keys())

    def upstream_of(self, job: str) -> List[str]:
        return list(self._deps.get(job, []))
