"""Point-in-time snapshot of watcher state for reporting and diffing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobSnapshot:
    """Captured state of a single job at snapshot time."""
    name: str
    last_run: Optional[datetime]
    is_missed: bool
    is_delayed: bool
    delay_seconds: float

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "is_missed": self.is_missed,
            "is_delayed": self.is_delayed,
            "delay_seconds": round(self.delay_seconds, 3),
        }


@dataclass
class WatcherSnapshot:
    """Full snapshot of all jobs at a given moment."""
    captured_at: datetime = field(default_factory=_utcnow)
    jobs: List[JobSnapshot] = field(default_factory=list)

    @property
    def missed(self) -> List[JobSnapshot]:
        return [j for j in self.jobs if j.is_missed]

    @property
    def delayed(self) -> List[JobSnapshot]:
        return [j for j in self.jobs if j.is_delayed]

    @property
    def ok(self) -> List[JobSnapshot]:
        return [j for j in self.jobs if not j.is_missed and not j.is_delayed]

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at.isoformat(),
            "jobs": [j.to_dict() for j in self.jobs],
            "summary": {
                "total": len(self.jobs),
                "ok": len(self.ok),
                "delayed": len(self.delayed),
                "missed": len(self.missed),
            },
        }


class SnapshotCollector:
    """Builds WatcherSnapshot instances from a registry."""

    def __init__(self, registry) -> None:
        self._registry = registry

    def capture(self, now: Optional[datetime] = None) -> WatcherSnapshot:
        now = now or _utcnow()
        snapshot = WatcherSnapshot(captured_at=now)
        for name, tracker in self._registry:
            status = tracker.check(now=now)
            snapshot.jobs.append(
                JobSnapshot(
                    name=name,
                    last_run=tracker.last_run,
                    is_missed=status.is_missed,
                    is_delayed=status.is_delayed,
                    delay_seconds=status.delay_seconds if status.is_delayed else 0.0,
                )
            )
        return snapshot
