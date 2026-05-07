"""Tests for DigestCollector."""
from datetime import datetime, timedelta

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.digest import DigestCollector, DigestEntry


def _alert(name: str = "job1", level: AlertLevel = AlertLevel.CRITICAL) -> Alert:
    return Alert(job_name=name, level=level, message="test")


def _now_factory(base: datetime):
    """Returns a callable that always returns *base*."""
    def _now():
        return base
    return _now


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        DigestCollector(window=timedelta(seconds=0))


def test_empty_flush_returns_no_alerts_message():
    dc = DigestCollector()
    result = dc.flush()
    assert "No alerts" in result


def test_collect_increments_pending():
    dc = DigestCollector()
    assert dc.pending == 0
    dc.collect(_alert())
    assert dc.pending == 1


def test_flush_clears_buffer():
    dc = DigestCollector()
    dc.collect(_alert())
    dc.flush()
    assert dc.pending == 0


def test_flush_contains_missed_label():
    dc = DigestCollector()
    dc.collect(_alert(level=AlertLevel.CRITICAL))
    result = dc.flush()
    assert "MISSED" in result


def test_flush_contains_delayed_label():
    dc = DigestCollector()
    dc.collect(_alert(level=AlertLevel.WARNING))
    result = dc.flush()
    assert "DELAYED" in result


def test_flush_counts_correctly():
    dc = DigestCollector()
    for _ in range(3):
        dc.collect(_alert())
    result = dc.flush()
    assert "3 alert" in result


def test_digest_entry_str_contains_job_name():
    now = datetime(2024, 1, 15, 12, 0, 0)
    entry = DigestEntry(alert=_alert(name="backup"), received_at=now)
    assert "backup" in str(entry)
    assert "2024-01-15" in str(entry)


def test_window_property():
    w = timedelta(minutes=30)
    dc = DigestCollector(window=w)
    assert dc.window == w
