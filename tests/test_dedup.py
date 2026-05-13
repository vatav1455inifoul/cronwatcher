"""Tests for cronwatcher.dedup — alert deduplication logic."""

from datetime import datetime, timezone, timedelta

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.dedup import AlertDeduplicator, DedupConfig


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset_seconds
    )


def _alert(job: str = "backup", level: AlertLevel = AlertLevel.WARNING) -> Alert:
    return Alert(job_name=job, level=level, message="test alert")


# --- DedupConfig validation ---

def test_invalid_window_raises() -> None:
    with pytest.raises(ValueError):
        DedupConfig(window_seconds=0)


def test_negative_window_raises() -> None:
    with pytest.raises(ValueError):
        DedupConfig(window_seconds=-60)


# --- First-time send ---

def test_first_alert_always_forwarded() -> None:
    d = AlertDeduplicator(now_fn=lambda: _utc(0))
    assert d.should_send(_alert()) is True


# --- Suppression within window ---

def test_second_alert_within_window_suppressed() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    alert = _alert()
    d.record_sent(alert)

    t = _utc(100)  # still within 300s window
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(alert) is False


def test_alert_forwarded_after_window_expires() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    alert = _alert()
    d.record_sent(alert)

    t = _utc(300)
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(alert) is True


# --- Different jobs / levels are independent ---

def test_different_jobs_not_deduplicated() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    d.record_sent(_alert(job="backup"))

    t = _utc(10)
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(_alert(job="sync")) is True


def test_different_levels_not_deduplicated() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    d.record_sent(_alert(level=AlertLevel.WARNING))

    t = _utc(10)
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(_alert(level=AlertLevel.CRITICAL)) is True


# --- Counters ---

def test_forwarded_counter() -> None:
    d = AlertDeduplicator(now_fn=lambda: _utc(0))
    d.record_sent(_alert())
    d.record_sent(_alert())
    assert d.forwarded == 2


def test_suppressed_counter() -> None:
    d = AlertDeduplicator(now_fn=lambda: _utc(0))
    d.record_suppressed()
    d.record_suppressed()
    assert d.suppressed == 2


# --- Reset ---

def test_reset_clears_job_state() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    alert = _alert(job="backup")
    d.record_sent(alert)

    d.reset("backup")

    t = _utc(10)
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(alert) is True


def test_reset_only_affects_named_job() -> None:
    t = _utc(0)
    d = AlertDeduplicator(DedupConfig(window_seconds=300), now_fn=lambda: t)
    d.record_sent(_alert(job="backup"))
    d.record_sent(_alert(job="sync"))

    d.reset("backup")

    t = _utc(10)
    d._now = lambda: t  # type: ignore[assignment]
    assert d.should_send(_alert(job="sync")) is False
