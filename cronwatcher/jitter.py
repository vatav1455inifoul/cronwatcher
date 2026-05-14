"""Jitter detection: flags runs that arrive suspiciously early or late
relative to their scheduled time, beyond a configurable tolerance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JitterSample:
    job_name: str
    scheduled_at: datetime
    actual_at: datetime

    @property
    def jitter_seconds(self) -> float:
        """Positive = late, negative = early."""
        return (self.actual_at - self.scheduled_at).total_seconds()

    def __str__(self) -> str:
        sign = "+" if self.jitter_seconds >= 0 else ""
        return (
            f"{self.job_name}: scheduled={self.scheduled_at.isoformat()} "
            f"actual={self.actual_at.isoformat()} "
            f"jitter={sign}{self.jitter_seconds:.1f}s"
        )


@dataclass
class JitterStats:
    job_name: str
    samples: List[float] = field(default_factory=list)

    def record(self, jitter_seconds: float) -> None:
        self.samples.append(jitter_seconds)

    @property
    def mean(self) -> Optional[float]:
        if not self.samples:
            return None
        return sum(self.samples) / len(self.samples)

    @property
    def max_abs(self) -> Optional[float]:
        if not self.samples:
            return None
        return max(abs(s) for s in self.samples)

    @property
    def count(self) -> int:
        return len(self.samples)


class JitterTracker:
    """Collects jitter samples per job and detects outliers."""

    def __init__(self, threshold_seconds: float = 30.0) -> None:
        if threshold_seconds <= 0:
            raise ValueError("threshold_seconds must be positive")
        self.threshold_seconds = threshold_seconds
        self._stats: Dict[str, JitterStats] = {}

    def record(self, job_name: str, scheduled_at: datetime, actual_at: datetime) -> JitterSample:
        sample = JitterSample(job_name=job_name, scheduled_at=scheduled_at, actual_at=actual_at)
        if job_name not in self._stats:
            self._stats[job_name] = JitterStats(job_name=job_name)
        self._stats[job_name].record(sample.jitter_seconds)
        return sample

    def is_outlier(self, sample: JitterSample) -> bool:
        return abs(sample.jitter_seconds) > self.threshold_seconds

    def stats_for(self, job_name: str) -> Optional[JitterStats]:
        return self._stats.get(job_name)

    def all_stats(self) -> Dict[str, JitterStats]:
        return dict(self._stats)
