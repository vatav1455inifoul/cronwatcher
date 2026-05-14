"""Append-only audit log for alert events."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuditEntry:
    timestamp: datetime
    job_name: str
    level: str
    message: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "job_name": self.job_name,
            "level": self.level,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            job_name=d["job_name"],
            level=d["level"],
            message=d["message"],
        )

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"[{ts}] {self.level:<8} {self.job_name}: {self.message}"


class AuditLog:
    """Persists alert audit entries to a newline-delimited JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    def record(self, alert: Alert) -> AuditEntry:
        entry = AuditEntry(
            timestamp=_utcnow(),
            job_name=alert.job_name,
            level=alert.level.name,
            message=alert.message,
        )
        with self._path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
        return entry

    def _iter_lines(self) -> Iterator[str]:
        with self._path.open("r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield line

    def all(self) -> List[AuditEntry]:
        return [AuditEntry.from_dict(json.loads(l)) for l in self._iter_lines()]

    def for_job(self, job_name: str) -> List[AuditEntry]:
        return [e for e in self.all() if e.job_name == job_name]

    def last(self, n: int = 10) -> List[AuditEntry]:
        entries = self.all()
        return entries[-n:] if len(entries) >= n else entries

    def clear(self) -> None:
        self._path.write_text("")
