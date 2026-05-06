"""Collects and exposes runtime metrics for monitored cron jobs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class JobMetrics:
    job_name: str
    total_runs: int = 0
    missed_count: int = 0
    delayed_count: int = 0
    delay_seconds: List[float] = field(default_factory=list)
    last_run: Optional[datetime] = None

    @property
    def average_delay(self) -> Optional[float]:
        if not self.delay_seconds:
            return None
        return sum(self.delay_seconds) / len(self.delay_seconds)

    @property
    def max_delay(self) -> Optional[float]:
        if not self.delay_seconds:
            return None
        return max(self.delay_seconds)

    @property
    def on_time_rate(self) -> Optional[float]:
        """Fraction of runs that were not delayed (0.0 - 1.0)."""
        if self.total_runs == 0:
            return None
        return (self.total_runs - self.delayed_count) / self.total_runs


class MetricsCollector:
    """Accumulates per-job metrics over the lifetime of the watcher."""

    def __init__(self) -> None:
        self._metrics: Dict[str, JobMetrics] = {}

    def _ensure(self, job_name: str) -> JobMetrics:
        if job_name not in self._metrics:
            self._metrics[job_name] = JobMetrics(job_name=job_name)
        return self._metrics[job_name]

    def record_run(self, job_name: str, delay_seconds: float, run_time: datetime) -> None:
        m = self._ensure(job_name)
        m.total_runs += 1
        m.last_run = run_time
        if delay_seconds > 0:
            m.delayed_count += 1
            m.delay_seconds.append(delay_seconds)

    def record_missed(self, job_name: str) -> None:
        m = self._ensure(job_name)
        m.missed_count += 1

    def get(self, job_name: str) -> Optional[JobMetrics]:
        return self._metrics.get(job_name)

    def all(self) -> Dict[str, JobMetrics]:
        return dict(self._metrics)

    def reset(self, job_name: str) -> None:
        if job_name in self._metrics:
            del self._metrics[job_name]
