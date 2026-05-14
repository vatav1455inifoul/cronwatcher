"""Delay trend analysis: detects whether a job's delay is worsening over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class TrendSample:
    recorded_at: datetime
    delay_seconds: float

    def __str__(self) -> str:
        return f"TrendSample(delay={self.delay_seconds:.1f}s at {self.recorded_at.isoformat()})"


@dataclass
class TrendResult:
    job_name: str
    slope: float          # seconds of delay gained per sample
    samples: int
    is_worsening: bool
    is_improving: bool

    def __str__(self) -> str:
        direction = "worsening" if self.is_worsening else ("improving" if self.is_improving else "stable")
        return f"Trend[{self.job_name}]: {direction} (slope={self.slope:+.2f}s/sample, n={self.samples})"


class TrendAnalyzer:
    """Tracks delay samples per job and computes a linear trend slope."""

    def __init__(self, min_samples: int = 3, worsen_threshold: float = 1.0,
                 improve_threshold: float = -1.0) -> None:
        if min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        self._min_samples = min_samples
        self._worsen_threshold = worsen_threshold
        self._improve_threshold = improve_threshold
        self._samples: dict[str, List[TrendSample]] = {}

    def record(self, job_name: str, delay_seconds: float,
               now: Optional[datetime] = None) -> None:
        now = now or _utcnow()
        self._samples.setdefault(job_name, []).append(
            TrendSample(recorded_at=now, delay_seconds=delay_seconds)
        )

    def analyze(self, job_name: str) -> Optional[TrendResult]:
        samples = self._samples.get(job_name, [])
        if len(samples) < self._min_samples:
            return None
        delays = [s.delay_seconds for s in samples]
        n = len(delays)
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(delays) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, delays))
        den = sum((x - mean_x) ** 2 for x in xs)
        slope = num / den if den != 0.0 else 0.0
        return TrendResult(
            job_name=job_name,
            slope=slope,
            samples=n,
            is_worsening=slope >= self._worsen_threshold,
            is_improving=slope <= self._improve_threshold,
        )

    def jobs(self) -> List[str]:
        return list(self._samples.keys())

    def clear(self, job_name: str) -> None:
        self._samples.pop(job_name, None)
