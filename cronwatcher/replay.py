"""Replay engine for simulating historical cron job runs.

Allows you to feed a sequence of past run timestamps into a watcher/tracker
and observe what alerts or status changes would have been generated.  Useful
for back-testing alert rules, tuning tolerances, and debugging incidents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, List, Optional

from cronwatcher.tracker import JobStatus


def _utcnow() -> datetime:  # pragma: no cover
    return datetime.now(timezone.utc)


@dataclass
class ReplayEvent:
    """A single event produced during a replay."""

    job_name: str
    timestamp: datetime
    status: JobStatus
    delay_seconds: float
    missed: bool

    def __str__(self) -> str:
        parts = [f"[{self.timestamp.isoformat()}] {self.job_name}"]
        if self.missed:
            parts.append("MISSED")
        elif self.delay_seconds > 0:
            parts.append(f"DELAYED +{self.delay_seconds:.1f}s")
        else:
            parts.append("OK")
        return " ".join(parts)


@dataclass
class ReplaySummary:
    """Aggregated results from a completed replay."""

    job_name: str
    total_runs: int = 0
    on_time: int = 0
    delayed: int = 0
    missed: int = 0
    events: List[ReplayEvent] = field(default_factory=list)

    @property
    def on_time_rate(self) -> Optional[float]:
        """Fraction of runs that were on time (0.0–1.0), or None if no runs."""
        if self.total_runs == 0:
            return None
        return self.on_time / self.total_runs

    def __str__(self) -> str:
        rate = self.on_time_rate
        rate_str = f"{rate * 100:.1f}%" if rate is not None else "n/a"
        return (
            f"{self.job_name}: {self.total_runs} runs, "
            f"{self.on_time} on-time ({rate_str}), "
            f"{self.delayed} delayed, {self.missed} missed"
        )


class ReplayEngine:
    """Replays a sequence of run timestamps against a job's tracker.

    Parameters
    ----------
    record_run_fn:
        Callable that accepts ``(job_name, timestamp)`` and returns a
        :class:`~cronwatcher.tracker.JobStatus`.
    check_fn:
        Callable that accepts ``(job_name, now)`` and returns a
        :class:`~cronwatcher.tracker.JobStatus` (used to detect missed runs
        between recorded events).
    event_handler:
        Optional callback invoked with each :class:`ReplayEvent` as it is
        produced.  Useful for streaming output during long replays.
    """

    def __init__(
        self,
        record_run_fn: Callable[[str, datetime], JobStatus],
        check_fn: Callable[[str, datetime], JobStatus],
        event_handler: Optional[Callable[[ReplayEvent], None]] = None,
    ) -> None:
        self._record_run = record_run_fn
        self._check = check_fn
        self._event_handler = event_handler

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def replay(
        self,
        job_name: str,
        timestamps: Iterable[datetime],
    ) -> ReplaySummary:
        """Replay *timestamps* for *job_name* and return a summary.

        Timestamps must be in ascending chronological order.
        """
        summary = ReplaySummary(job_name=job_name)

        for ts in timestamps:
            status = self._record_run(job_name, ts)
            event = ReplayEvent(
                job_name=job_name,
                timestamp=ts,
                status=status,
                delay_seconds=status.delay_seconds if status.delay_seconds else 0.0,
                missed=status.is_missed,
            )
            summary.total_runs += 1
            if event.missed:
                summary.missed += 1
            elif event.delay_seconds > 0:
                summary.delayed += 1
            else:
                summary.on_time += 1
            summary.events.append(event)
            if self._event_handler is not None:
                self._event_handler(event)

        return summary
