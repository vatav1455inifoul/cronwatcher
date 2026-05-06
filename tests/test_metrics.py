"""Tests for MetricsCollector and MetricsReport."""

from datetime import datetime

import pytest

from cronwatcher.metrics import MetricsCollector
from cronwatcher.metrics_reporter import MetricsReport


@pytest.fixture()
def collector() -> MetricsCollector:
    return MetricsCollector()


def _now() -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0)


def test_initial_get_returns_none(collector):
    assert collector.get("backup") is None


def test_record_run_increments_total(collector):
    collector.record_run("backup", delay_seconds=0.0, run_time=_now())
    assert collector.get("backup").total_runs == 1


def test_record_run_no_delay_not_counted(collector):
    collector.record_run("backup", delay_seconds=0.0, run_time=_now())
    m = collector.get("backup")
    assert m.delayed_count == 0
    assert m.delay_seconds == []


def test_record_run_with_delay_tracked(collector):
    collector.record_run("backup", delay_seconds=45.0, run_time=_now())
    m = collector.get("backup")
    assert m.delayed_count == 1
    assert m.delay_seconds == [45.0]


def test_average_delay(collector):
    collector.record_run("backup", delay_seconds=30.0, run_time=_now())
    collector.record_run("backup", delay_seconds=60.0, run_time=_now())
    assert collector.get("backup").average_delay == 45.0


def test_average_delay_no_delays_returns_zero(collector):
    """average_delay should be 0.0 when no delayed runs have been recorded."""
    collector.record_run("backup", delay_seconds=0.0, run_time=_now())
    assert collector.get("backup").average_delay == 0.0


def test_max_delay(collector):
    collector.record_run("backup", delay_seconds=10.0, run_time=_now())
    collector.record_run("backup", delay_seconds=90.0, run_time=_now())
    assert collector.get("backup").max_delay == 90.0


def test_on_time_rate(collector):
    collector.record_run("backup", delay_seconds=0.0, run_time=_now())
    collector.record_run("backup", delay_seconds=0.0, run_time=_now())
    collector.record_run("backup", delay_seconds=5.0, run_time=_now())
    rate = collector.get("backup").on_time_rate
    assert abs(rate - 2 / 3) < 1e-9


def test_record_missed(collector):
    collector.record_missed("nightly")
    collector.record_missed("nightly")
    assert collector.get("nightly").missed_count == 2


def test_reset_removes_entry(collector):
    collector.record_run("job", delay_seconds=0.0, run_time=_now())
    collector.reset("job")
    assert collector.get("job") is None


def test_all_returns_all_jobs(collector):
    collector.record_run("a", 0.0, _now())
    collector.record_run("b", 0.0, _now())
    assert set(collector.all().keys()) == {"a", "b"}


def test_metrics_report_contains_job_name(collector):
    collector.record_run("nightly_backup", delay_seconds=0.0, run_time=_now())
    report = MetricsReport(collector)
    assert "nightly_backup" in str(report)


def test_metrics_report_empty_shows_no_data(collector):
    report = MetricsReport(collector)
    assert "(no data)" in str(report)


def test_metrics_report_shows_missed_count(collector):
    collector.record_missed("hourly")
    collector.record_missed("hourly")
    report = str(MetricsReport(collector))
    assert "2" in report
