"""Tests for ThrottledNotifier."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.throttle import ThrottleRule
from cronwatcher.throttled_notifier import ThrottledNotifier

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _alert(level: AlertLevel = AlertLevel.WARNING, job: str = "backup") -> Alert:
    return Alert(job_name=job, level=level, message="test alert", timestamp=_NOW)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_notifier(
    rules: dict | None = None,
) -> tuple[ThrottledNotifier, MagicMock]:
    inner = MagicMock()
    tn = ThrottledNotifier(inner, rules)
    return tn, inner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_forwards_alert_when_no_rules():
    tn, inner = _make_notifier()
    result = tn(_alert())
    assert result is True
    inner.assert_called_once()


def test_sent_counter_increments():
    tn, _ = _make_notifier()
    tn(_alert())
    tn(_alert())
    assert tn.sent == 2
    assert tn.suppressed == 0


def test_suppressed_when_within_throttle_window():
    rules = {AlertLevel.WARNING: ThrottleRule(interval_seconds=300)}
    tn, inner = _make_notifier(rules)

    t1 = _NOW
    t2 = datetime(2024, 6, 1, 12, 1, 0, tzinfo=timezone.utc)  # 60 s later

    with patch("cronwatcher.throttle._utcnow", return_value=t1):
        r1 = tn(_alert(AlertLevel.WARNING))

    with patch("cronwatcher.throttle._utcnow", return_value=t2):
        r2 = tn(_alert(AlertLevel.WARNING))

    assert r1 is True
    assert r2 is False
    assert tn.sent == 1
    assert tn.suppressed == 1
    inner.assert_called_once()


def test_not_suppressed_after_window_expires():
    rules = {AlertLevel.WARNING: ThrottleRule(interval_seconds=60)}
    tn, inner = _make_notifier(rules)

    t1 = _NOW
    t2 = datetime(2024, 6, 1, 12, 2, 0, tzinfo=timezone.utc)  # 120 s later

    with patch("cronwatcher.throttle._utcnow", return_value=t1):
        tn(_alert(AlertLevel.WARNING))

    with patch("cronwatcher.throttle._utcnow", return_value=t2):
        result = tn(_alert(AlertLevel.WARNING))

    assert result is True
    assert tn.sent == 2
    assert inner.call_count == 2


def test_different_jobs_tracked_independently():
    rules = {AlertLevel.CRITICAL: ThrottleRule(interval_seconds=600)}
    tn, inner = _make_notifier(rules)

    with patch("cronwatcher.throttle._utcnow", return_value=_NOW):
        r1 = tn(_alert(AlertLevel.CRITICAL, job="job_a"))
        r2 = tn(_alert(AlertLevel.CRITICAL, job="job_b"))

    assert r1 is True
    assert r2 is True
    assert tn.sent == 2


def test_level_without_rule_always_passes():
    # Only WARNING is throttled; CRITICAL has no rule
    rules = {AlertLevel.WARNING: ThrottleRule(interval_seconds=300)}
    tn, inner = _make_notifier(rules)

    with patch("cronwatcher.throttle._utcnow", return_value=_NOW):
        tn(_alert(AlertLevel.CRITICAL))
        result = tn(_alert(AlertLevel.CRITICAL))

    assert result is True
    assert tn.sent == 2
