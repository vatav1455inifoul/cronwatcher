"""Tests for JobRegistry."""

from datetime import datetime

import pytest

from cronwatcher.registry import JobRegistry


BASE_TIME = datetime(2024, 1, 15, 12, 0, 0)


def test_register_and_contains():
    reg = JobRegistry()
    reg.register("job_a", "* * * * *")
    assert "job_a" in reg
    assert "job_b" not in reg


def test_register_returns_tracker():
    reg = JobRegistry()
    tracker = reg.register("job_a", "* * * * *")
    assert tracker.name == "job_a"


def test_len():
    reg = JobRegistry()
    reg.register("a", "* * * * *")
    reg.register("b", "0 * * * *")
    assert len(reg) == 2


def test_record_run_unknown_job_raises():
    reg = JobRegistry()
    with pytest.raises(KeyError):
        reg.record_run("nonexistent")


def test_record_run_and_check():
    reg = JobRegistry(default_tolerance=30)
    reg.register("sync", "* * * * *")
    reg.record_run("sync", at=BASE_TIME)
    status = reg.check("sync", at=BASE_TIME)
    assert status.name == "sync"
    assert status.missed_count == 0


def test_check_all_returns_all_statuses():
    reg = JobRegistry()
    reg.register("a", "* * * * *")
    reg.register("b", "0 * * * *")
    statuses = reg.check_all(at=BASE_TIME)
    assert len(statuses) == 2
    names = {s.name for s in statuses}
    assert names == {"a", "b"}


def test_alerts_returns_only_problematic_jobs():
    reg = JobRegistry(default_tolerance=10)
    reg.register("ok_job", "* * * * *")
    reg.register("missed_job", "* * * * *", tolerance_seconds=10)

    # Record run for ok_job at the boundary
    reg.record_run("ok_job", at=BASE_TIME)

    # Check 90 seconds later — missed_job has no run, ok_job ran
    from datetime import timedelta
    check_time = BASE_TIME + timedelta(seconds=90)
    alert_list = reg.alerts(at=check_time)
    alert_names = {s.name for s in alert_list}
    assert "missed_job" in alert_names


def test_custom_tolerance_per_job():
    reg = JobRegistry(default_tolerance=30)
    reg.register("strict", "* * * * *", tolerance_seconds=5)
    tracker = reg._jobs["strict"]
    assert tracker.tolerance == 5
