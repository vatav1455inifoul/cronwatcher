"""Parse and evaluate cron schedule expressions."""

from datetime import datetime
from croniter import croniter


class CronSchedule:
    """Wraps a cron expression and provides timing utilities."""

    def __init__(self, expression: str, job_name: str):
        if not croniter.is_valid(expression):
            raise ValueError(f"Invalid cron expression: '{expression}'")
        self.expression = expression
        self.job_name = job_name

    def last_expected_run(self, reference: datetime | None = None) -> datetime:
        """Return the most recent scheduled run time before *reference*."""
        ref = reference or datetime.now()
        it = croniter(self.expression, ref)
        return it.get_prev(datetime)

    def next_expected_run(self, reference: datetime | None = None) -> datetime:
        """Return the next scheduled run time after *reference*."""
        ref = reference or datetime.now()
        it = croniter(self.expression, ref)
        return it.get_next(datetime)

    def seconds_until_next(self, reference: datetime | None = None) -> float:
        """Seconds remaining until the next scheduled run."""
        ref = reference or datetime.now()
        return (self.next_expected_run(ref) - ref).total_seconds()

    def seconds_since_last(self, reference: datetime | None = None) -> float:
        """Seconds elapsed since the last scheduled run."""
        ref = reference or datetime.now()
        return (ref - self.last_expected_run(ref)).total_seconds()

    def is_overdue(self, last_run: datetime, grace_seconds: float = 60.0) -> bool:
        """Return True if the job has missed its last scheduled window.

        A job is considered overdue when the time elapsed since the last
        *expected* run exceeds *grace_seconds* and *last_run* predates that
        expected run.
        """
        now = datetime.now()
        last_expected = self.last_expected_run(now)
        overdue_threshold = grace_seconds
        elapsed_since_expected = (now - last_expected).total_seconds()
        job_ran_after_expected = last_run >= last_expected
        return elapsed_since_expected > overdue_threshold and not job_ran_after_expected

    def __repr__(self) -> str:
        return f"CronSchedule(job={self.job_name!r}, expr={self.expression!r})"
