"""Generates summary reports of cron job health status."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cronwatcher.registry import JobRegistry
from cronwatcher.tracker import JobStatus


@dataclass
class JobReport:
    job_name: str
    last_run: Optional[datetime]
    next_expected: Optional[datetime]
    is_missed: bool
    is_delayed: bool
    delay_seconds: float
    run_count: int

    def status_label(self) -> str:
        if self.is_missed:
            return "MISSED"
        if self.is_delayed:
            return "DELAYED"
        return "OK"

    def __str__(self) -> str:
        delay_info = f", delay={self.delay_seconds:.1f}s" if self.is_delayed else ""
        last = self.last_run.isoformat() if self.last_run else "never"
        return (
            f"[{self.status_label()}] {self.job_name} "
            f"(last_run={last}, runs={self.run_count}{delay_info})"
        )


@dataclass
class SummaryReport:
    generated_at: datetime = field(default_factory=datetime.utcnow)
    jobs: List[JobReport] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def missed_count(self) -> int:
        return sum(1 for j in self.jobs if j.is_missed)

    @property
    def delayed_count(self) -> int:
        return sum(1 for j in self.jobs if j.is_delayed)

    @property
    def healthy_count(self) -> int:
        return sum(1 for j in self.jobs if not j.is_missed and not j.is_delayed)

    def __str__(self) -> str:
        lines = [
            f"=== CronWatcher Report [{self.generated_at.isoformat()}] ===",
            f"Total: {self.total}  OK: {self.healthy_count}  "
            f"Delayed: {self.delayed_count}  Missed: {self.missed_count}",
            "-" * 60,
        ]
        for job in self.jobs:
            lines.append(str(job))
        return "\n".join(lines)


class Reporter:
    def __init__(self, registry: JobRegistry) -> None:
        self._registry = registry

    def generate(self, now: Optional[datetime] = None) -> SummaryReport:
        if now is None:
            now = datetime.utcnow()
        report = SummaryReport(generated_at=now)
        for name, tracker in self._registry.items():
            status: JobStatus = tracker.check(now)
            report.jobs.append(
                JobReport(
                    job_name=name,
                    last_run=tracker.last_run,
                    next_expected=tracker.schedule.next_expected_run(now),
                    is_missed=status.is_missed,
                    is_delayed=status.is_delayed,
                    delay_seconds=status.delay_seconds,
                    run_count=tracker.run_count,
                )
            )
        return report
