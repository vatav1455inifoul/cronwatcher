"""Tests for AlertCorrelator and CorrelationGroup."""
from datetime import datetime, timedelta

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.correlation import AlertCorrelator, CorrelationGroup


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=offset_seconds)


def _alert(job: str, level: AlertLevel = AlertLevel.CRITICAL) -> Alert:
    return Alert(job_name=job, level=level, message="test")


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        AlertCorrelator(window_seconds=0)


def test_negative_window_raises():
    with pytest.raises(ValueError):
        AlertCorrelator(window_seconds=-5)


def test_observe_within_window_returns_none():
    t = _utc(0)
    corr = AlertCorrelator(window_seconds=60, _now=lambda: t)
    result = corr.observe(_alert("job_a"))
    assert result is None


def test_observe_beyond_window_returns_group():
    calls = [_utc(0), _utc(0), _utc(70)]
    idx = [0]

    def _now():
        val = calls[min(idx[0], len(calls) - 1)]
        idx[0] += 1
        return val

    corr = AlertCorrelator(window_seconds=60, _now=_now)
    corr.observe(_alert("job_a"))
    group = corr.observe(_alert("job_b"))
    assert group is not None
    assert len(group.alerts) == 1  # first alert flushed


def test_flush_returns_pending_alerts():
    t = _utc(0)
    corr = AlertCorrelator(window_seconds=60, _now=lambda: t)
    corr.observe(_alert("job_a"))
    corr.observe(_alert("job_b"))
    group = corr.flush()
    assert group is not None
    assert len(group.alerts) == 2


def test_flush_empty_returns_none():
    corr = AlertCorrelator(window_seconds=60)
    assert corr.flush() is None


def test_group_is_systemic_multiple_jobs():
    group = CorrelationGroup(
        window_start=_utc(0),
        window_end=_utc(10),
        alerts=[_alert("job_a"), _alert("job_b")],
    )
    assert group.is_systemic is True


def test_group_not_systemic_single_job():
    group = CorrelationGroup(
        window_start=_utc(0),
        window_end=_utc(10),
        alerts=[_alert("job_a"), _alert("job_a")],
    )
    assert group.is_systemic is False


def test_group_highest_level_critical():
    group = CorrelationGroup(
        window_start=_utc(0),
        window_end=_utc(10),
        alerts=[_alert("job_a", AlertLevel.WARNING), _alert("job_b", AlertLevel.CRITICAL)],
    )
    assert group.highest_level == AlertLevel.CRITICAL


def test_group_str_contains_job_names():
    group = CorrelationGroup(
        window_start=_utc(0),
        window_end=_utc(10),
        alerts=[_alert("job_a"), _alert("job_b")],
    )
    s = str(group)
    assert "job_a" in s
    assert "job_b" in s


def test_groups_accumulate():
    t = _utc(0)
    corr = AlertCorrelator(window_seconds=60, _now=lambda: t)
    corr.observe(_alert("job_a"))
    corr.flush()
    corr.observe(_alert("job_b"))
    corr.flush()
    assert len(corr.groups) == 2
