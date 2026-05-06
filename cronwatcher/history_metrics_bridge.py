"""Bridge that populates MetricsCollector from RunHistory data."""

from __future__ import annotations

from typing import Optional

from cronwatcher.history import RunHistory
from cronwatcher.metrics import MetricsCollector


class HistoryMetricsBridge:
    """Feeds historical run records into a MetricsCollector.

    Useful when restoring state from persistence so that metrics
    reflect all known runs, not just those observed in the current
    process lifetime.
    """

    def __init__(
        self,
        history: RunHistory,
        collector: MetricsCollector,
    ) -> None:
        self._history = history
        self._collector = collector

    def sync(self, job_name: str) -> int:
        """Replay all history records for *job_name* into the collector.

        Returns the number of records replayed.
        """
        records = self._history.get(job_name)
        replayed = 0
        for record in records:
            delay: Optional[float] = (
                record.delay_seconds if record.delay_seconds is not None else None
            )
            self._collector.record_run(job_name, delay_seconds=delay)
            replayed += 1
        return replayed

    def sync_all(self) -> dict[str, int]:
        """Replay history for every job known to the history store.

        Returns a mapping of job_name -> records replayed.
        """
        results: dict[str, int] = {}
        for job_name in self._history.all_jobs():
            results[job_name] = self.sync(job_name)
        return results
