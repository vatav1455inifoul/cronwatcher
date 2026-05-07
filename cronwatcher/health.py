"""Health check endpoint data for cronwatcher daemon."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobHealth:
    job_name: str
    last_run: Optional[datetime]
    is_missed: bool
    is_delayed: bool
    delay_seconds: float

    @property
    def status(self) -> str:
        if self.is_missed:
            return "missed"
        if self.is_delayed:
            return "delayed"
        return "ok"

    def to_dict(self) -> dict:
        return {
            "job": self.job_name,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "delay_seconds": round(self.delay_seconds, 2),
        }


@dataclass
class HealthReport:
    generated_at: datetime = field(default_factory=_utcnow)
    jobs: List[JobHealth] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        if any(j.is_missed for j in self.jobs):
            return "critical"
        if any(j.is_delayed for j in self.jobs):
            return "warning"
        return "ok"

    def to_dict(self) -> dict:
        return {
            "status": self.overall_status,
            "generated_at": self.generated_at.isoformat(),
            "jobs": [j.to_dict() for j in self.jobs],
        }


class HealthChecker:
    """Builds a HealthReport from a registry."""

    def __init__(self, registry) -> None:
        self._registry = registry

    def check(self) -> HealthReport:
        report = HealthReport()
        for name, tracker in self._registry:
            status = tracker.check()
            report.jobs.append(
                JobHealth(
                    job_name=name,
                    last_run=tracker.last_run,
                    is_missed=status.is_missed,
                    is_delayed=status.is_delayed,
                    delay_seconds=status.delay_seconds if status.delay_seconds else 0.0,
                )
            )
        return report
