"""Tests for cronwatcher.retry and cronwatcher.retrying_notifier."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.retry import RetryPolicy, RetryResult, with_retry
from cronwatcher.retrying_notifier import RetryingNotifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alert() -> Alert:
    return Alert(
        job_name="backup",
        level=AlertLevel.WARNING,
        message="delayed",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_invalid_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)


def test_invalid_base_delay_raises():
    with pytest.raises(ValueError, match="base_delay"):
        RetryPolicy(base_delay=0)


def test_invalid_backoff_factor_raises():
    with pytest.raises(ValueError, match="backoff_factor"):
        RetryPolicy(backoff_factor=0.5)


def test_delay_for_first_attempt_is_zero():
    policy = RetryPolicy(base_delay=2.0, backoff_factor=3.0)
    assert policy.delay_for(0) == 0.0


def test_delay_for_respects_backoff():
    policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=100.0)
    assert policy.delay_for(1) == 1.0
    assert policy.delay_for(2) == 2.0
    assert policy.delay_for(3) == 4.0


def test_delay_for_capped_at_max():
    policy = RetryPolicy(base_delay=10.0, backoff_factor=10.0, max_delay=50.0)
    assert policy.delay_for(3) == 50.0


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def test_with_retry_succeeds_first_attempt():
    fn = MagicMock()
    sleep = MagicMock()
    result = with_retry(fn, RetryPolicy(max_attempts=3), _sleep=sleep)
    assert result.success is True
    assert result.attempts == 1
    sleep.assert_not_called()


def test_with_retry_retries_on_failure():
    fn = MagicMock(side_effect=[RuntimeError("boom"), RuntimeError("boom"), None])
    sleep = MagicMock()
    result = with_retry(fn, RetryPolicy(max_attempts=3, base_delay=1.0), _sleep=sleep)
    assert result.success is True
    assert result.attempts == 3
    assert sleep.call_count == 2  # slept before attempt 1 and 2


def test_with_retry_exhausts_attempts():
    exc = IOError("network")
    fn = MagicMock(side_effect=exc)
    result = with_retry(fn, RetryPolicy(max_attempts=2, base_delay=0.1), _sleep=MagicMock())
    assert result.success is False
    assert result.attempts == 2
    assert result.last_exception is exc


# ---------------------------------------------------------------------------
# RetryingNotifier
# ---------------------------------------------------------------------------

def test_retrying_notifier_calls_underlying():
    inner = MagicMock()
    notifier = RetryingNotifier(inner, RetryPolicy(max_attempts=1))
    alert = _alert()
    result = notifier(alert)
    inner.assert_called_once_with(alert)
    assert result.success is True


def test_retrying_notifier_retries_and_succeeds():
    inner = MagicMock(side_effect=[Exception("fail"), None])
    notifier = RetryingNotifier(inner, RetryPolicy(max_attempts=2, base_delay=0.01))
    result = notifier(_alert())
    assert result.success is True
    assert inner.call_count == 2


def test_retrying_notifier_returns_failure_after_exhaustion():
    inner = MagicMock(side_effect=Exception("always fails"))
    notifier = RetryingNotifier(inner, RetryPolicy(max_attempts=3, base_delay=0.01))
    result = notifier(_alert())
    assert result.success is False
    assert result.attempts == 3
