"""Formats run history into a human-readable table."""
from __future__ import annotations

from typing import Optional

from cronwatcher.history import RunHistory

_COL_WIDTH = 24
_STATUS_WIDTH = 8
_DELAY_WIDTH = 10


def _status_label(record) -> str:
    if record.missed:
        return "MISSED"
    if record.delay_seconds > 0:
        return "DELAYED"
    return "OK"


class HistoryReport:
    """Renders a run history for one or all jobs."""

    def __init__(self, history: RunHistory) -> None:
        self._history = history

    def _header(self) -> str:
        return (
            f"{'Timestamp':<{_COL_WIDTH}}"
            f"{'Job':<{_COL_WIDTH}}"
            f"{'Status':<{_STATUS_WIDTH}}"
            f"{'Delay(s)':>{_DELAY_WIDTH}}"
        )

    def _separator(self) -> str:
        return "-" * (_COL_WIDTH * 2 + _STATUS_WIDTH + _DELAY_WIDTH)

    def _format_row(self, record) -> str:
        ts = record.ran_at.strftime("%Y-%m-%d %H:%M:%S")
        status = _status_label(record)
        delay = f"{record.delay_seconds:.1f}"
        return (
            f"{ts:<{_COL_WIDTH}}"
            f"{record.job_name:<{_COL_WIDTH}}"
            f"{status:<{_STATUS_WIDTH}}"
            f"{delay:>{_DELAY_WIDTH}}"
        )

    def render(self, job_name: Optional[str] = None) -> str:
        """Render history table. If job_name is given, show only that job."""
        if job_name:
            jobs = [job_name]
        else:
            jobs = sorted(self._history.all_jobs())

        lines = [self._header(), self._separator()]
        for job in jobs:
            for record in self._history.get(job):
                lines.append(self._format_row(record))

        if len(lines) == 2:
            lines.append("(no history recorded)")

        return "\n".join(lines)
