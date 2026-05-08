"""Tests for CircuitBreaker and CircuitBreakerConfig."""
import time
import pytest
from unittest.mock import MagicMock

from cronwatcher.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    BreakerState,
)


def test_invalid_failure_threshold_raises():
    with pytest.raises(ValueError):
        CircuitBreakerConfig(failure_threshold=0)


def test_invalid_recovery_timeout_raises():
    with pytest.raises(ValueError):
        CircuitBreakerConfig(recovery_timeout=0)


def test_invalid_success_threshold_raises():
    with pytest.raises(ValueError):
        CircuitBreakerConfig(success_threshold=0)


def test_initial_state_is_closed():
    cb = CircuitBreaker()
    assert cb.state == BreakerState.CLOSED


def test_successful_call_stays_closed():
    cb = CircuitBreaker()
    result = cb.call(lambda: 42)
    assert result == 42
    assert cb.state == BreakerState.CLOSED


def test_failures_open_circuit():
    cfg = CircuitBreakerConfig(failure_threshold=2)
    cb = CircuitBreaker(cfg)

    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))

    assert cb.state == BreakerState.OPEN


def test_open_circuit_blocks_calls():
    cfg = CircuitBreakerConfig(failure_threshold=1)
    cb = CircuitBreaker(cfg)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))

    assert cb.state == BreakerState.OPEN
    with pytest.raises(RuntimeError, match="OPEN"):
        cb.call(lambda: None)


def test_recovery_timeout_transitions_to_half_open(monkeypatch):
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1.0)
    cb = CircuitBreaker(cfg)
    with pytest.raises(Exception):
        cb.call(lambda: (_ for _ in ()).throw(Exception()))

    # Simulate time passing beyond recovery_timeout
    monkeypatch.setattr("cronwatcher.circuit_breaker.time.monotonic",
                        lambda: cb._opened_at + 2.0)  # type: ignore[operator]
    assert cb.state == BreakerState.HALF_OPEN


def test_success_in_half_open_closes_circuit(monkeypatch):
    cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1.0)
    cb = CircuitBreaker(cfg)
    with pytest.raises(Exception):
        cb.call(lambda: (_ for _ in ()).throw(Exception()))

    monkeypatch.setattr("cronwatcher.circuit_breaker.time.monotonic",
                        lambda: cb._opened_at + 2.0)  # type: ignore[operator]
    cb.call(lambda: None)
    assert cb.state == BreakerState.CLOSED


def test_reset_closes_open_circuit():
    cfg = CircuitBreakerConfig(failure_threshold=1)
    cb = CircuitBreaker(cfg)
    with pytest.raises(Exception):
        cb.call(lambda: (_ for _ in ()).throw(Exception()))
    cb.reset()
    assert cb.state == BreakerState.CLOSED
