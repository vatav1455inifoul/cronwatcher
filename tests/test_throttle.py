"""Tests for alert throttling logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.throttle import AlertThrottle, ThrottleRule


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _alert(job: str = "backup", level: AlertLevel = AlertLevel.WARNING) -> Alert:
    return Alert(job_name=job, level=level, message="test alert")


def test_invalid_rule_raises():
    with pytest.raises(ValueError):
        ThrottleRule(AlertLevel.WARNING, -1)


def test_should_send_no_rules_always_true():
    throttle = AlertThrottle()
    assert throttle.should_send(_alert()) is True


def test_should_send_first_time_always_true():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    assert throttle.should_send(_alert()) is True


def test_should_send_within_interval_is_false():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    alert = _alert()
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(alert)
    # 100 seconds later — still within 300s window
    later = NOW + timedelta(seconds=100)
    with patch("cronwatcher.throttle._utcnow", return_value=later):
        assert throttle.should_send(alert) is False


def test_should_send_after_interval_is_true():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    alert = _alert()
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(alert)
    later = NOW + timedelta(seconds=301)
    with patch("cronwatcher.throttle._utcnow", return_value=later):
        assert throttle.should_send(alert) is True


def test_different_levels_tracked_independently():
    throttle = AlertThrottle([
        ThrottleRule(AlertLevel.WARNING, 300),
        ThrottleRule(AlertLevel.CRITICAL, 600),
    ])
    warn = _alert(level=AlertLevel.WARNING)
    crit = _alert(level=AlertLevel.CRITICAL)
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(warn)
    later = NOW + timedelta(seconds=350)
    with patch("cronwatcher.throttle._utcnow", return_value=later):
        assert throttle.should_send(warn) is True   # past 300s
        assert throttle.should_send(crit) is True   # never sent


def test_send_calls_alerter_and_returns_true():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    alerter = MagicMock()
    alert = _alert()
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        result = throttle.send(alert, alerter)
    assert result is True
    alerter.send.assert_called_once_with(alert)


def test_send_suppressed_does_not_call_alerter():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    alerter = MagicMock()
    alert = _alert()
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(alert)
        result = throttle.send(alert, alerter)
    assert result is False
    alerter.send.assert_not_called()


def test_reset_clears_state():
    throttle = AlertThrottle([ThrottleRule(AlertLevel.WARNING, 300)])
    alert = _alert()
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(alert)
    throttle.reset("backup")
    later = NOW + timedelta(seconds=10)
    with patch("cronwatcher.throttle._utcnow", return_value=later):
        assert throttle.should_send(alert) is True


def test_reset_specific_level_only():
    throttle = AlertThrottle([
        ThrottleRule(AlertLevel.WARNING, 300),
        ThrottleRule(AlertLevel.CRITICAL, 300),
    ])
    warn = _alert(level=AlertLevel.WARNING)
    crit = _alert(level=AlertLevel.CRITICAL)
    with patch("cronwatcher.throttle._utcnow", return_value=NOW):
        throttle.record(warn)
        throttle.record(crit)
    throttle.reset("backup", AlertLevel.WARNING)
    later = NOW + timedelta(seconds=10)
    with patch("cronwatcher.throttle._utcnow", return_value=later):
        assert throttle.should_send(warn) is True
        assert throttle.should_send(crit) is False
