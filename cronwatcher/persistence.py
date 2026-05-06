"""Simple JSON-based persistence for job run history."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

DEFAULT_STATE_FILE = "/tmp/cronwatcher_state.json"
DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"


def _serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(DATETIME_FMT) if dt is not None else None


def _deserialize_dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.strptime(s, DATETIME_FMT) if s is not None else None


class StateStore:
    """Reads and writes job last-run timestamps to a JSON file."""

    def __init__(self, path: str = DEFAULT_STATE_FILE) -> None:
        self.path = path
        self._data: Dict[str, Optional[str]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        with open(self.path, "w") as fh:
            json.dump(self._data, fh, indent=2)

    def set_last_run(self, job_name: str, ts: datetime) -> None:
        self._data[job_name] = _serialize_dt(ts)

    def get_last_run(self, job_name: str) -> Optional[datetime]:
        return _deserialize_dt(self._data.get(job_name))

    def all_jobs(self) -> List[str]:
        return list(self._data.keys())

    def remove(self, job_name: str) -> None:
        self._data.pop(job_name, None)

    def clear(self) -> None:
        self._data = {}
