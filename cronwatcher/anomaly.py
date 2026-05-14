"""Anomaly detection for cron job run times using rolling z-score."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class AnomalyResult:
    job_name: str
    observed_delay: float  # seconds
    mean: float
    stddev: float
    z_score: float
    is_anomaly: bool

    def __str__(self) -> str:
        flag = "[ANOMALY]" if self.is_anomaly else "[ok]"
        return (
            f"{flag} {self.job_name}: delay={self.observed_delay:.1f}s "
            f"z={self.z_score:.2f} (mean={self.mean:.1f}s stddev={self.stddev:.1f}s)"
        )


class AnomalyDetector:
    """Detects anomalous run delays using a rolling window z-score."""

    def __init__(self, window: int = 20, threshold: float = 3.0) -> None:
        if window < 2:
            raise ValueError("window must be at least 2")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self._window = window
        self._threshold = threshold
        self._samples: dict[str, List[float]] = {}

    def record(self, job_name: str, delay_seconds: float) -> Optional[AnomalyResult]:
        """Record a delay sample and return an AnomalyResult if enough data exists."""
        bucket = self._samples.setdefault(job_name, [])
        bucket.append(delay_seconds)
        if len(bucket) > self._window:
            bucket.pop(0)
        if len(bucket) < 2:
            return None
        mean = sum(bucket) / len(bucket)
        variance = sum((x - mean) ** 2 for x in bucket) / len(bucket)
        stddev = math.sqrt(variance)
        if stddev == 0.0:
            z = 0.0
        else:
            z = abs(delay_seconds - mean) / stddev
        return AnomalyResult(
            job_name=job_name,
            observed_delay=delay_seconds,
            mean=mean,
            stddev=stddev,
            z_score=z,
            is_anomaly=z >= self._threshold,
        )

    def reset(self, job_name: str) -> None:
        self._samples.pop(job_name, None)

    def sample_count(self, job_name: str) -> int:
        return len(self._samples.get(job_name, []))
