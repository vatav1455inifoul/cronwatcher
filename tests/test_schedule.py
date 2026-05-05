"""Tests for cronwatcher.schedule.CronSchedule."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.schedule import CronSchedule


REFERENCE = datetime(2024, 6, 15, 12, 30, 0)  # Saturday 12:30:00


def test_invalid_expression_raises():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        CronSchedule("not-a-cron", "bad_job")


def test_last_expected_run_every_minute():
    sched = CronSchedule("* * * * *", "minutely")
    last = sched.last_expected_run(REFERENCE)
    # For an every-minute schedule the previous tick should be exactly 1 min before
    assert last == datetime(2024, 6, 15, 12, 29, 0)


def test_next_expected_run_every_minute():
    sched = CronSchedule("* * * * *", "minutely")
    nxt = sched.next_expected_run(REFERENCE)
    assert nxt == datetime(2024, 6, 15, 12, 31, 0)


def test_seconds_until_next():
    sched = CronSchedule("* * * * *", "minutely")
    seconds = sched.seconds_until_next(REFERENCE)
    assert seconds == pytest.approx(60.0)


def test_seconds_since_last():
    sched = CronSchedule("* * * * *", "minutely")
    seconds = sched.seconds_since_last(REFERENCE)
    assert seconds == pytest.approx(60.0)


def test_is_overdue_when_missed():
    sched = CronSchedule("* * * * *", "minutely")
    # last_run was 3 minutes ago — job missed at least one tick
    last_run = REFERENCE - timedelta(minutes=3)
    assert sched.is_overdue(last_run, grace_seconds=60.0) is True


def test_is_not_overdue_when_ran_on_time():
    sched = CronSchedule("* * * * *", "minutely")
    # last_run is within the current minute window
    last_run = REFERENCE - timedelta(seconds=10)
    assert sched.is_overdue(last_run, grace_seconds=60.0) is False


def test_repr():
    sched = CronSchedule("0 * * * *", "hourly_job")
    assert "hourly_job" in repr(sched)
    assert "0 * * * *" in repr(sched)
