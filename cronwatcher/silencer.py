"""Silencer — temporarily suppress alerts for specific jobs during maintenance windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SilenceWindow:
    """A time-bounded silence window for a job (or all jobs if job_name is None)."""

    start: datetime
    end: datetime
    job_name: Optional[str] = None  # None means silence everything
    reason: str = ""

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("end must be after start")

    def is_active(self, at: Optional[datetime] = None) -> bool:
        now = at or _utcnow()
        return self.start <= now <= self.end

    def covers(self, job_name: str, at: Optional[datetime] = None) -> bool:
        if not self.is_active(at):
            return False
        return self.job_name is None or self.job_name == job_name

    def __str__(self) -> str:
        target = self.job_name or "*"
        return (
            f"SilenceWindow(job={target!r}, "
            f"{self.start.isoformat()} -> {self.end.isoformat()}, "
            f"reason={self.reason!r})"
        )


class Silencer:
    """Registry of active silence windows; answers whether a job is currently silenced."""

    def __init__(self) -> None:
        self._windows: List[SilenceWindow] = []

    def add(self, window: SilenceWindow) -> None:
        self._windows.append(window)

    def is_silenced(self, job_name: str, at: Optional[datetime] = None) -> bool:
        return any(w.covers(job_name, at) for w in self._windows)

    def active_windows(self, at: Optional[datetime] = None) -> List[SilenceWindow]:
        return [w for w in self._windows if w.is_active(at)]

    def windows_for_job(self, job_name: str, at: Optional[datetime] = None) -> List[SilenceWindow]:
        """Return all active windows that cover the given job, including wildcard windows."""
        return [w for w in self._windows if w.covers(job_name, at)]

    def purge_expired(self, at: Optional[datetime] = None) -> int:
        """Remove windows that have already ended; returns number removed."""
        now = at or _utcnow()
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.end > now]
        return before - len(self._windows)

    def __len__(self) -> int:
        return len(self._windows)
