"""Run history tracking for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RunRecord:
    """A single recorded execution of a cron job."""
    job_name: str
    ran_at: datetime
    delay_seconds: float  # 0.0 if on time
    missed: bool = False

    def __str__(self) -> str:
        status = "MISSED" if self.missed else ("DELAYED" if self.delay_seconds > 0 else "OK")
        ts = self.ran_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] {self.job_name}: {status} (delay={self.delay_seconds:.1f}s)"


class RunHistory:
    """Stores and queries the run history for all tracked jobs."""

    def __init__(self, max_records_per_job: int = 100) -> None:
        self._max = max_records_per_job
        self._records: dict[str, List[RunRecord]] = {}

    def record(self, run: RunRecord) -> None:
        """Append a RunRecord, evicting oldest if over the cap."""
        records = self._records.setdefault(run.job_name, [])
        records.append(run)
        if len(records) > self._max:
            records.pop(0)

    def get(self, job_name: str) -> List[RunRecord]:
        """Return all records for a job (oldest first)."""
        return list(self._records.get(job_name, []))

    def last(self, job_name: str) -> Optional[RunRecord]:
        """Return the most recent record for a job, or None."""
        records = self._records.get(job_name)
        return records[-1] if records else None

    def all_jobs(self) -> List[str]:
        """Return all job names that have at least one record."""
        return list(self._records.keys())

    def missed_runs(self, job_name: str) -> List[RunRecord]:
        """Return only the missed records for a job."""
        return [r for r in self.get(job_name) if r.missed]

    def delayed_runs(self, job_name: str) -> List[RunRecord]:
        """Return only the delayed (but not missed) records for a job."""
        return [r for r in self.get(job_name) if r.delay_seconds > 0 and not r.missed]

    def __len__(self) -> int:
        return sum(len(v) for v in self._records.values())
