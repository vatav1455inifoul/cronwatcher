"""SLA (Service Level Agreement) tracking for cron jobs.

Tracks whether jobs are meeting their expected uptime/reliability targets
based on historical run data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SLAConfig:
    """Configuration for a job's SLA requirements."""
    target_success_rate: float  # 0.0 - 1.0, e.g. 0.99 for 99%
    window_hours: int = 24

    def __post_init__(self) -> None:
        if not (0.0 < self.target_success_rate <= 1.0):
            raise ValueError("target_success_rate must be between 0 (exclusive) and 1 (inclusive)")
        if self.window_hours < 1:
            raise ValueError("window_hours must be at least 1")


@dataclass
class SLAResult:
    """Result of an SLA check for a single job."""
    job_name: str
    target: float
    actual: float
    total_runs: int
    on_time_runs: int
    window_hours: int
    breached: bool

    def __str__(self) -> str:
        status = "BREACHED" if self.breached else "OK"
        return (
            f"[{status}] {self.job_name}: "
            f"{self.actual:.1%} actual vs {self.target:.1%} target "
            f"({self.on_time_runs}/{self.total_runs} on-time, "
            f"{self.window_hours}h window)"
        )


@dataclass
class _RunEntry:
    ran_at: datetime
    on_time: bool


class SLATracker:
    """Tracks run history and evaluates SLA compliance per job."""

    def __init__(self) -> None:
        self._configs: Dict[str, SLAConfig] = {}
        self._runs: Dict[str, List[_RunEntry]] = {}

    def configure(self, job_name: str, config: SLAConfig) -> None:
        """Register an SLA config for a job."""
        self._configs[job_name] = config
        if job_name not in self._runs:
            self._runs[job_name] = []

    def record(self, job_name: str, on_time: bool, ran_at: Optional[datetime] = None) -> None:
        """Record a run outcome for a job."""
        if job_name not in self._configs:
            raise KeyError(f"No SLA config for job: {job_name!r}")
        ts = ran_at or _utcnow()
        self._runs[job_name].append(_RunEntry(ran_at=ts, on_time=on_time))

    def evaluate(self, job_name: str, now: Optional[datetime] = None) -> SLAResult:
        """Evaluate SLA compliance for a job over its configured window."""
        if job_name not in self._configs:
            raise KeyError(f"No SLA config for job: {job_name!r}")
        cfg = self._configs[job_name]
        now = now or _utcnow()
        cutoff = now - timedelta(hours=cfg.window_hours)
        recent = [r for r in self._runs[job_name] if r.ran_at >= cutoff]
        total = len(recent)
        on_time = sum(1 for r in recent if r.on_time)
        actual = (on_time / total) if total > 0 else 1.0
        return SLAResult(
            job_name=job_name,
            target=cfg.target_success_rate,
            actual=actual,
            total_runs=total,
            on_time_runs=on_time,
            window_hours=cfg.window_hours,
            breached=actual < cfg.target_success_rate,
        )

    def evaluate_all(self, now: Optional[datetime] = None) -> List[SLAResult]:
        """Evaluate SLA compliance for all configured jobs."""
        return [self.evaluate(name, now=now) for name in self._configs]
