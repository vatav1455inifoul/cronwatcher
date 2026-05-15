"""Tests for cronwatcher.sla — SLA tracking module."""
from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.sla import SLAConfig, SLAResult, SLATracker


def _utc(**kwargs) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(**kwargs)


NOW = _utc()


# --- SLAConfig validation ---

def test_invalid_target_zero_raises():
    with pytest.raises(ValueError, match="target_success_rate"):
        SLAConfig(target_success_rate=0.0)


def test_invalid_target_above_one_raises():
    with pytest.raises(ValueError, match="target_success_rate"):
        SLAConfig(target_success_rate=1.1)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_hours"):
        SLAConfig(target_success_rate=0.99, window_hours=0)


def test_valid_config_created():
    cfg = SLAConfig(target_success_rate=0.95, window_hours=48)
    assert cfg.target_success_rate == 0.95
    assert cfg.window_hours == 48


# --- SLATracker core behaviour ---

def _tracker_with_job(rate: float = 0.99, hours: int = 24) -> SLATracker:
    t = SLATracker()
    t.configure("backup", SLAConfig(target_success_rate=rate, window_hours=hours))
    return t


def test_configure_unknown_job_can_be_recorded():
    t = _tracker_with_job()
    # no error expected
    t.record("backup", on_time=True, ran_at=NOW)


def test_record_unknown_job_raises():
    t = SLATracker()
    with pytest.raises(KeyError, match="backup"):
        t.record("backup", on_time=True)


def test_evaluate_unknown_job_raises():
    t = SLATracker()
    with pytest.raises(KeyError):
        t.evaluate("missing")


def test_evaluate_no_runs_returns_full_rate():
    t = _tracker_with_job(rate=0.99)
    result = t.evaluate("backup", now=NOW)
    assert result.actual == 1.0
    assert result.total_runs == 0
    assert not result.breached


def test_evaluate_all_on_time_not_breached():
    t = _tracker_with_job(rate=0.9)
    for i in range(5):
        t.record("backup", on_time=True, ran_at=_utc(hours=-i))
    result = t.evaluate("backup", now=NOW)
    assert result.actual == 1.0
    assert not result.breached


def test_evaluate_below_target_is_breached():
    t = _tracker_with_job(rate=0.9)
    # 2 on-time, 8 late => 20% success rate
    for i in range(2):
        t.record("backup", on_time=True, ran_at=_utc(hours=-i))
    for i in range(8):
        t.record("backup", on_time=False, ran_at=_utc(hours=-(i + 2)))
    result = t.evaluate("backup", now=NOW)
    assert result.breached
    assert result.actual == pytest.approx(0.2)


def test_runs_outside_window_excluded():
    t = _tracker_with_job(rate=0.99, hours=24)
    # old failing run outside window
    t.record("backup", on_time=False, ran_at=_utc(hours=-25))
    # recent passing run
    t.record("backup", on_time=True, ran_at=_utc(hours=-1))
    result = t.evaluate("backup", now=NOW)
    assert result.total_runs == 1
    assert result.on_time_runs == 1
    assert not result.breached


def test_evaluate_all_returns_results_for_all_jobs():
    t = SLATracker()
    t.configure("job_a", SLAConfig(target_success_rate=0.99))
    t.configure("job_b", SLAConfig(target_success_rate=0.95))
    results = t.evaluate_all(now=NOW)
    assert len(results) == 2
    names = {r.job_name for r in results}
    assert names == {"job_a", "job_b"}


def test_sla_result_str_ok():
    r = SLAResult("myjob", 0.9, 1.0, 10, 10, 24, breached=False)
    assert "OK" in str(r)
    assert "myjob" in str(r)


def test_sla_result_str_breached():
    r = SLAResult("myjob", 0.99, 0.5, 10, 5, 24, breached=True)
    assert "BREACHED" in str(r)
    assert "myjob" in str(r)
