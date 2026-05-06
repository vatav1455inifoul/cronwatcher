"""Combined report: history table + per-job metrics summary."""

from __future__ import annotations

from cronwatcher.history import RunHistory
from cronwatcher.history_reporter import HistoryReport
from cronwatcher.metrics import MetricsCollector
from cronwatcher.metrics_reporter import MetricsReport


class HistoryMetricsReport:
    """Renders a combined history + metrics report for one or all jobs."""

    def __init__(
        self,
        history: RunHistory,
        collector: MetricsCollector,
        limit: int = 10,
    ) -> None:
        self._history = history
        self._collector = collector
        self._limit = limit

    def render(self, job_name: str) -> str:
        """Return a combined report string for a single job."""
        history_report = HistoryReport(self._history, limit=self._limit)
        metrics_report = MetricsReport(self._collector)

        lines: list[str] = [
            f"=== Report for: {job_name} ===",
            "",
            "-- Run History --",
            history_report.render(job_name),
            "",
            "-- Metrics --",
            metrics_report.render(job_name),
        ]
        return "\n".join(lines)

    def render_all(self) -> str:
        """Return a combined report for every job in history."""
        jobs = sorted(self._history.all_jobs())
        if not jobs:
            return "No job history available."

        sections = [self.render(job) for job in jobs]
        return "\n\n".join(sections)
