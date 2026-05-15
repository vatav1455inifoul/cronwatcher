"""Tests for DependencyGraph and DependencyAlerter."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.dependency import DependencyGraph, DependencyViolation
from cronwatcher.dependency_alerter import DependencyAlerter


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=offset_seconds)


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------

def test_no_deps_check_returns_none():
    g = DependencyGraph()
    g.record_run("job_a", _utc())
    assert g.check("job_a") is None


def test_upstream_ran_before_returns_none():
    g = DependencyGraph()
    g.add_dependency("job_b", "job_a")
    g.record_run("job_a", _utc(0))
    g.record_run("job_b", _utc(10))
    assert g.check("job_b") is None


def test_upstream_not_run_returns_violation():
    g = DependencyGraph()
    g.add_dependency("job_b", "job_a")
    g.record_run("job_b", _utc(10))
    v = g.check("job_b")
    assert v is not None
    assert "job_a" in v.missing_upstream


def test_upstream_ran_after_job_returns_violation():
    g = DependencyGraph()
    g.add_dependency("job_b", "job_a")
    g.record_run("job_b", _utc(5))
    g.record_run("job_a", _utc(10))  # upstream ran AFTER job_b
    v = g.check("job_b")
    assert v is not None
    assert "job_a" in v.missing_upstream


def test_check_all_returns_all_violations():
    g = DependencyGraph()
    g.add_dependency("job_b", "job_a")
    g.add_dependency("job_c", "job_a")
    g.record_run("job_b", _utc(5))
    g.record_run("job_c", _utc(5))
    # job_a never ran
    violations = g.check_all()
    assert len(violations) == 2


def test_violation_str_contains_job_name():
    v = DependencyViolation(job="job_b", missing_upstream=["job_a"], checked_at=_utc())
    assert "job_b" in str(v)
    assert "job_a" in str(v)


def test_upstream_of_returns_declared_deps():
    g = DependencyGraph()
    g.add_dependency("job_b", "job_a")
    assert g.upstream_of("job_b") == ["job_a"]


# ---------------------------------------------------------------------------
# DependencyAlerter
# ---------------------------------------------------------------------------

def _make_alerter() -> tuple[DependencyAlerter, Alerter, DependencyGraph]:
    inner = Alerter()
    graph = DependencyGraph()
    da = DependencyAlerter(inner=inner, graph=graph)
    return da, inner, graph


def test_check_dependencies_fires_alert_on_violation():
    da, inner, graph = _make_alerter()
    graph.add_dependency("job_b", "job_a")
    da.record_run("job_b")
    received: list[Alert] = []
    inner.add_handler(received.append)
    da.check_dependencies()
    assert len(received) == 1
    assert received[0].job_name == "job_b"
    assert received[0].level == AlertLevel.WARNING


def test_check_dependencies_no_violation_no_alert():
    da, inner, graph = _make_alerter()
    graph.add_dependency("job_b", "job_a")
    graph.record_run("job_a", _utc(0))
    da.record_run("job_b")
    received: list[Alert] = []
    inner.add_handler(received.append)
    da.check_dependencies()
    assert received == []


def test_violation_handler_called():
    da, _, graph = _make_alerter()
    graph.add_dependency("job_b", "job_a")
    da.record_run("job_b")
    seen: list[DependencyViolation] = []
    da.add_violation_handler(seen.append)
    da.check_dependencies()
    assert len(seen) == 1
    assert seen[0].job == "job_b"


def test_violations_property_accumulates():
    da, _, graph = _make_alerter()
    graph.add_dependency("job_b", "job_a")
    da.record_run("job_b")
    da.check_dependencies()
    da.record_run("job_b")
    da.check_dependencies()
    assert len(da.violations) == 2
