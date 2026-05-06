"""Append-only run log that writes job execution events to a plain text file."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DT_FMT = "%Y-%m-%dT%H:%M:%S%z"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class RunLog:
    """Writes and reads a newline-delimited log of job run events.

    Each line has the format::

        <ISO-timestamp>\t<job_name>\t<status>\t<delay_seconds>

    ``delay_seconds`` is ``-`` when there is no delay recorded.
    """

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # touch the file so it exists
        self._path.touch(exist_ok=True)

    # ------------------------------------------------------------------
    # writing
    # ------------------------------------------------------------------

    def append(self, job_name: str, status: str, delay_seconds: float | None = None) -> None:
        """Append a single run event to the log file."""
        ts = _now().strftime(DT_FMT)
        delay_field = f"{delay_seconds:.2f}" if delay_seconds is not None else "-"
        line = f"{ts}\t{job_name}\t{status}\t{delay_field}\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    # ------------------------------------------------------------------
    # reading
    # ------------------------------------------------------------------

    def _iter_lines(self) -> Iterator[tuple[datetime, str, str, float | None]]:
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                parts = raw.split("\t")
                if len(parts) != 4:
                    continue
                ts_str, name, status, delay_str = parts
                try:
                    ts = datetime.strptime(ts_str, DT_FMT)
                except ValueError:
                    continue
                delay = None if delay_str == "-" else float(delay_str)
                yield ts, name, status, delay

    def read_all(self) -> list[dict]:
        """Return all log entries as a list of dicts."""
        return [
            {"timestamp": ts, "job": name, "status": status, "delay_seconds": delay}
            for ts, name, status, delay in self._iter_lines()
        ]

    def read_job(self, job_name: str) -> list[dict]:
        """Return log entries for a specific job."""
        return [
            {"timestamp": ts, "job": name, "status": status, "delay_seconds": delay}
            for ts, name, status, delay in self._iter_lines()
            if name == job_name
        ]

    def clear(self) -> None:
        """Truncate the log file."""
        self._path.write_text("", encoding="utf-8")
