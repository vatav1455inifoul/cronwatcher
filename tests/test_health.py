"""Tests for HealthChecker and HealthReport."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.health import HealthChecker, HealthReport, JobHealth


def _utcnow():
    return datetime.now(timezone.utc)


def _make_tracker(*, last_run=None, is_missed=False, is_delayed=False, delay=0.0):
    status = MagicMock(is_missed=is_missed, is_delayed=is_delayed, delay_seconds=delay)
    tracker = MagicMock()
    tracker.last_run = last_run
    tracker.check.return_value = status
    return tracker


def _make_registry(jobs: dict):
    registry = MagicMock()
    registry.__iter__ = MagicMock(return_value=iter(jobs.items()))
    return registry


def test_job_health_status_ok():
    jh = JobHealth("job", _utcnow(), False, False, 0.0)
    assert jh.status == "ok"


def test_job_health_status_delayed():
    jh = JobHealth("job", _utcnow(), False, True, 30.0)
    assert jh.status == "delayed"


def test_job_health_status_missed():
    jh = JobHealth("job", None, True, False, 0.0)
    assert jh.status == "missed"


def test_job_health_to_dict_keys():
    jh = JobHealth("myjob", _utcnow(), False, False, 0.0)
    d = jh.to_dict()
    assert set(d.keys()) == {"job", "status", "last_run", "delay_seconds"}
    assert d["job"] == "myjob"


def test_job_health_to_dict_no_last_run():
    jh = JobHealth("myjob", None, True, False, 0.0)
    assert jh.to_dict()["last_run"] is None


def test_health_report_overall_ok():
    report = HealthReport()
    report.jobs = [JobHealth("a", _utcnow(), False, False, 0.0)]
    assert report.overall_status == "ok"


def test_health_report_overall_warning():
    report = HealthReport()
    report.jobs = [JobHealth("a", _utcnow(), False, True, 10.0)]
    assert report.overall_status == "warning"


def test_health_report_overall_critical():
    report = HealthReport()
    report.jobs = [JobHealth("a", None, True, False, 0.0)]
    assert report.overall_status == "critical"


def test_health_report_to_dict_structure():
    report = HealthReport()
    report.jobs = [JobHealth("j", None, False, False, 0.0)]
    d = report.to_dict()
    assert "status" in d
    assert "generated_at" in d
    assert "jobs" in d
    assert len(d["jobs"]) == 1


def test_health_checker_builds_report():
    t1 = _make_tracker(last_run=_utcnow(), is_missed=False, is_delayed=False)
    t2 = _make_tracker(last_run=None, is_missed=True, is_delayed=False)
    registry = _make_registry({"job_a": t1, "job_b": t2})
    checker = HealthChecker(registry)
    report = checker.check()
    assert len(report.jobs) == 2
    names = [j.job_name for j in report.jobs]
    assert "job_a" in names
    assert "job_b" in names
    assert report.overall_status == "critical"
