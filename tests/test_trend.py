"""Tests for cronwatcher.trend and cronwatcher.trend_alerter."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerter import Alerter
from cronwatcher.trend import TrendAnalyzer, TrendResult
from cronwatcher.trend_alerter import TrendAlerter


def _utc(offset: int = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=offset)


# ---------------------------------------------------------------------------
# TrendAnalyzer
# ---------------------------------------------------------------------------

def test_invalid_min_samples_raises():
    with pytest.raises(ValueError):
        TrendAnalyzer(min_samples=1)


def test_analyze_returns_none_before_min_samples():
    ta = TrendAnalyzer(min_samples=3)
    ta.record("job", 5.0, now=_utc(0))
    ta.record("job", 6.0, now=_utc(60))
    assert ta.analyze("job") is None


def test_analyze_returns_result_after_min_samples():
    ta = TrendAnalyzer(min_samples=3)
    for i in range(3):
        ta.record("job", float(i * 10), now=_utc(i * 60))
    result = ta.analyze("job")
    assert isinstance(result, TrendResult)
    assert result.job_name == "job"
    assert result.samples == 3


def test_worsening_trend_detected():
    ta = TrendAnalyzer(min_samples=3, worsen_threshold=1.0)
    # delays grow: 0, 10, 20 -> slope = 10
    for i in range(3):
        ta.record("job", float(i * 10), now=_utc(i * 60))
    result = ta.analyze("job")
    assert result is not None
    assert result.is_worsening is True
    assert result.is_improving is False


def test_improving_trend_detected():
    ta = TrendAnalyzer(min_samples=3, improve_threshold=-1.0)
    for i in range(3):
        ta.record("job", float(20 - i * 10), now=_utc(i * 60))
    result = ta.analyze("job")
    assert result is not None
    assert result.is_improving is True
    assert result.is_worsening is False


def test_stable_trend_neither_flag():
    ta = TrendAnalyzer(min_samples=3, worsen_threshold=5.0, improve_threshold=-5.0)
    for i in range(3):
        ta.record("job", 3.0, now=_utc(i * 60))
    result = ta.analyze("job")
    assert result is not None
    assert result.is_worsening is False
    assert result.is_improving is False


def test_jobs_lists_recorded_names():
    ta = TrendAnalyzer()
    ta.record("alpha", 1.0)
    ta.record("beta", 2.0)
    assert set(ta.jobs()) == {"alpha", "beta"}


def test_clear_removes_samples():
    ta = TrendAnalyzer(min_samples=2)
    ta.record("job", 5.0)
    ta.record("job", 6.0)
    ta.clear("job")
    assert ta.analyze("job") is None


def test_trend_result_str_contains_job_name():
    r = TrendResult(job_name="myjob", slope=3.5, samples=5,
                    is_worsening=True, is_improving=False)
    assert "myjob" in str(r)
    assert "worsening" in str(r)


# ---------------------------------------------------------------------------
# TrendAlerter
# ---------------------------------------------------------------------------

def _make_trend_alerter(min_samples: int = 3):
    inner = MagicMock(spec=Alerter)
    ta = TrendAlerter(inner, min_samples=min_samples)
    return ta, inner


def test_alert_missed_forwards_to_inner():
    ta, inner = _make_trend_alerter()
    ta.alert_missed("job")
    inner.alert_missed.assert_called_once_with("job")


def test_alert_delayed_forwards_to_inner():
    ta, inner = _make_trend_alerter()
    ta.alert_delayed("job", 30.0)
    inner.alert_delayed.assert_called_once_with("job", 30.0)


def test_trend_handler_called_on_worsening():
    ta, _ = _make_trend_alerter(min_samples=3)
    handler = MagicMock()
    ta.add_trend_handler(handler)
    for i in range(3):
        ta.alert_delayed("job", float(i * 20), now=_utc(i * 60))
    handler.assert_called()
    result: TrendResult = handler.call_args[0][0]
    assert result.is_worsening is True


def test_trend_handler_not_called_when_stable():
    ta, _ = _make_trend_alerter(min_samples=3)
    handler = MagicMock()
    ta.add_trend_handler(handler)
    for i in range(3):
        ta.alert_delayed("job", 2.0, now=_utc(i * 60))
    handler.assert_not_called()


def test_record_ok_feeds_zero_delay():
    ta, _ = _make_trend_alerter(min_samples=3)
    handler = MagicMock()
    ta.add_trend_handler(handler)
    ta.alert_delayed("job", 30.0, now=_utc(0))
    ta.alert_delayed("job", 20.0, now=_utc(60))
    ta.record_ok("job", now=_utc(120))   # slope becomes negative -> not worsening
    handler.assert_not_called()
