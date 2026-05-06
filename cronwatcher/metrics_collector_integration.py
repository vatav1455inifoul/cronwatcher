"""Wires MetricsCollector into a Watcher so every record_run call
also updates metrics automatically."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from cronwatcher.metrics import MetricsCollector
from cronwatcher.watcher import Watcher


class MetricsWatcher:
    """A thin wrapper around Watcher that records metrics on every run."""

    def __init__(self, watcher: Watcher, collector: Optional[MetricsCollector] = None) -> None:
        self._watcher = watcher
        self.collector: MetricsCollector = collector or MetricsCollector()

    # ------------------------------------------------------------------ #
    # Delegation helpers
    # ------------------------------------------------------------------ #

    def register(self, name: str, expression: str, tolerance: int = 60) -> None:
        """Register a job with the underlying watcher."""
        self._watcher.register(name, expression, tolerance)

    def record_run(self, name: str, ran_at: Optional[datetime] = None) -> object:
        """Record a run, update metrics, and return the JobStatus."""
        ran_at = ran_at or datetime.utcnow()
        status = self._watcher.record_run(name, ran_at)
        delay_seconds = status.delay_seconds if status.delay_seconds else 0.0
        self.collector.record(name, ran_at, delay_seconds)
        return status

    def check_all(self) -> list:
        """Delegate check_all to the underlying watcher."""
        return self._watcher.check_all()

    def metrics(self, name: str):
        """Return JobMetrics for a given job name (may be None)."""
        return self.collector.get(name)

    def all_metrics(self) -> dict:
        """Return a mapping of job_name -> JobMetrics for every tracked job."""
        return self.collector.all()

    # Make len() and 'in' work the same as on the underlying registry
    def __len__(self) -> int:
        return len(self._watcher)

    def __contains__(self, name: str) -> bool:
        return name in self._watcher
