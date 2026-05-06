"""Tests for MetricsWatcher — the metrics-aware Watcher wrapper."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.metrics import MetricsCollector
from cronwatcher.watcher import Watcher
from cronwatcher.metrics_collector_integration import MetricsWatcher


EVERY_MINUTE = "* * * * *"


@pytest.fixture()
def mw() -> MetricsWatcher:
    watcher = Watcher()
    collector = MetricsCollector()
    mw = MetricsWatcher(watcher, collector)
    mw.register("job_a", EVERY_MINUTE, tolerance=120)
    return mw


def test_register_and_contains(mw: MetricsWatcher):
    assert "job_a" in mw


def test_len(mw: MetricsWatcher):
    assert len(mw) == 1


def test_record_run_returns_status(mw: MetricsWatcher):
    status = mw.record_run("job_a")
    assert status is not None


def test_metrics_none_before_run():
    watcher = Watcher()
    mw = MetricsWatcher(watcher)
    mw.register("fresh", EVERY_MINUTE)
    assert mw.metrics("fresh") is None


def test_metrics_populated_after_run(mw: MetricsWatcher):
    mw.record_run("job_a")
    m = mw.metrics("job_a")
    assert m is not None
    assert m.total_runs == 1


def test_on_time_run_not_counted_as_delayed(mw: MetricsWatcher):
    # Run right now — should be on-time for an every-minute job
    mw.record_run("job_a")
    m = mw.metrics("job_a")
    assert m.delayed_runs == 0


def test_multiple_runs_accumulate(mw: MetricsWatcher):
    mw.record_run("job_a")
    mw.record_run("job_a")
    mw.record_run("job_a")
    m = mw.metrics("job_a")
    assert m.total_runs == 3


def test_all_metrics_returns_dict(mw: MetricsWatcher):
    mw.record_run("job_a")
    all_m = mw.all_metrics()
    assert "job_a" in all_m


def test_check_all_delegates(mw: MetricsWatcher):
    # check_all should not raise and returns a list
    result = mw.check_all()
    assert isinstance(result, list)


def test_default_collector_created_when_none_passed():
    watcher = Watcher()
    mw = MetricsWatcher(watcher)  # no collector supplied
    mw.register("solo", EVERY_MINUTE)
    mw.record_run("solo")
    assert mw.metrics("solo") is not None
