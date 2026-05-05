"""Tests for JobTracker."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.tracker import JobTracker


BASE_TIME = datetime(2024, 1, 15, 12, 0, 0)  # Monday 12:00:00 UTC


def test_record_run_returns_status():
    tracker = JobTracker("backup", "* * * * *", tolerance_seconds=30)
    status = tracker.record_run(at=BASE_TIME)
    assert status.name == "backup"
    assert status.last_run == BASE_TIME
    assert status.missed_count == 0


def test_record_run_on_time_no_delay():
    tracker = JobTracker("backup", "* * * * *", tolerance_seconds=30)
    # Run exactly at the expected minute boundary
    on_time = datetime(2024, 1, 15, 12, 0, 0)
    status = tracker.record_run(at=on_time)
    assert status.delay_seconds == 0.0
    assert not status.is_delayed


def test_record_run_late_shows_delay():
    tracker = JobTracker("backup", "* * * * *", tolerance_seconds=30)
    late_time = datetime(2024, 1, 15, 12, 0, 45)  # 45s into the minute
    status = tracker.record_run(at=late_time)
    assert status.delay_seconds == pytest.approx(45.0)
    assert status.is_delayed


def test_check_no_run_within_tolerance_not_missed():
    tracker = JobTracker("heartbeat", "* * * * *", tolerance_seconds=120)
    # 30 seconds after the last expected run — within tolerance
    check_time = datetime(2024, 1, 15, 12, 0, 30)
    status = tracker.check(at=check_time)
    assert status.missed_count == 0
    assert not status.is_missed


def test_check_no_run_beyond_tolerance_is_missed():
    tracker = JobTracker("heartbeat", "* * * * *", tolerance_seconds=30)
    # 90 seconds after the minute boundary with no recorded run
    check_time = datetime(2024, 1, 15, 12, 1, 30)
    status = tracker.check(at=check_time)
    assert status.missed_count == 1
    assert status.is_missed


def test_check_after_run_not_missed():
    tracker = JobTracker("cleanup", "* * * * *", tolerance_seconds=30)
    run_time = datetime(2024, 1, 15, 12, 0, 5)
    tracker.record_run(at=run_time)
    check_time = datetime(2024, 1, 15, 12, 0, 50)
    status = tracker.check(at=check_time)
    assert status.missed_count == 0


def test_invalid_expression_raises():
    with pytest.raises(Exception):
        JobTracker("bad", "not a cron expression")
