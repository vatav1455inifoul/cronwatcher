"""Tests for CircuitBreakerNotifier."""
import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.circuit_breaker import CircuitBreakerConfig, BreakerState
from cronwatcher.circuit_breaker_notifier import CircuitBreakerNotifier


def _alert(name: str = "job.test") -> Alert:
    return Alert(
        job_name=name,
        level=AlertLevel.WARNING,
        message="test alert",
        timestamp=datetime.now(timezone.utc),
    )


def test_forwards_alert_to_notifier():
    inner = MagicMock()
    cbn = CircuitBreakerNotifier(inner)
    alert = _alert()
    cbn(alert)
    inner.assert_called_once_with(alert)


def test_initial_state_is_closed():
    cbn = CircuitBreakerNotifier(MagicMock())
    assert cbn.state == BreakerState.CLOSED


def test_blocked_starts_at_zero():
    cbn = CircuitBreakerNotifier(MagicMock())
    assert cbn.blocked == 0


def test_failing_notifier_opens_circuit():
    inner = MagicMock(side_effect=OSError("smtp down"))
    cfg = CircuitBreakerConfig(failure_threshold=2)
    cbn = CircuitBreakerNotifier(inner, cfg)

    for _ in range(2):
        cbn(_alert())  # exceptions are re-raised by breaker, swallowed by notifier? No — re-raised

    # After threshold failures the circuit should be open
    assert cbn.state == BreakerState.OPEN


def test_open_circuit_blocks_call_and_increments_counter():
    inner = MagicMock(side_effect=OSError("down"))
    cfg = CircuitBreakerConfig(failure_threshold=1)
    cbn = CircuitBreakerNotifier(inner, cfg)

    cbn(_alert())  # trips the breaker
    assert cbn.state == BreakerState.OPEN

    cbn(_alert())  # should be blocked
    assert cbn.blocked == 1
    # inner was only called once (the first time)
    assert inner.call_count == 1


def test_reset_clears_blocked_count():
    inner = MagicMock(side_effect=OSError())
    cfg = CircuitBreakerConfig(failure_threshold=1)
    cbn = CircuitBreakerNotifier(inner, cfg)
    cbn(_alert())  # open
    cbn(_alert())  # blocked
    assert cbn.blocked == 1
    cbn.reset()
    assert cbn.blocked == 0
    assert cbn.state == BreakerState.CLOSED


def test_multiple_alerts_forwarded_while_closed():
    inner = MagicMock()
    cbn = CircuitBreakerNotifier(inner)
    alerts = [_alert(f"job.{i}") for i in range(5)]
    for a in alerts:
        cbn(a)
    assert inner.call_count == 5
