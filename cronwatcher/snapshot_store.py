"""Persist and retrieve watcher snapshots as JSON."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatcher.snapshot import JobSnapshot, WatcherSnapshot


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


class SnapshotStore:
    """Appends snapshots to a newline-delimited JSON file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    def save(self, snapshot: WatcherSnapshot) -> None:
        with self._path.open("a") as fh:
            fh.write(json.dumps(snapshot.to_dict()) + "\n")

    def load_all(self) -> List[WatcherSnapshot]:
        snapshots: List[WatcherSnapshot] = []
        with self._path.open("r") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                captured_at = _parse_dt(data["captured_at"])
                jobs = [
                    JobSnapshot(
                        name=j["name"],
                        last_run=_parse_dt(j["last_run"]),
                        is_missed=j["is_missed"],
                        is_delayed=j["is_delayed"],
                        delay_seconds=j["delay_seconds"],
                    )
                    for j in data["jobs"]
                ]
                snapshots.append(WatcherSnapshot(captured_at=captured_at, jobs=jobs))
        return snapshots

    def latest(self) -> Optional[WatcherSnapshot]:
        all_snaps = self.load_all()
        return all_snaps[-1] if all_snaps else None

    def clear(self) -> None:
        self._path.write_text("")
