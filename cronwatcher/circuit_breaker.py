"""Circuit breaker for notifiers — stops hammering a failing endpoint."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class BreakerState(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # failing, requests blocked
    HALF_OPEN = "half_open"  # testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3    # failures before opening
    recovery_timeout: float = 60.0  # seconds before trying again
    success_threshold: int = 1    # successes in HALF_OPEN to close

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")


class CircuitBreaker:
    """Wraps a callable and opens the circuit after repeated failures."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._cfg = config or CircuitBreakerConfig()
        self._state = BreakerState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> BreakerState:
        if self._state == BreakerState.OPEN:
            if self._opened_at is not None:
                elapsed = time.monotonic() - self._opened_at
                if elapsed >= self._cfg.recovery_timeout:
                    self._state = BreakerState.HALF_OPEN
                    self._success_count = 0
        return self._state

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call *fn* if circuit allows; raise RuntimeError when open."""
        state = self.state
        if state == BreakerState.OPEN:
            raise RuntimeError("Circuit breaker is OPEN — call blocked")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        if self._state == BreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._cfg.success_threshold:
                self._state = BreakerState.CLOSED
                self._failure_count = 0
        elif self._state == BreakerState.CLOSED:
            self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._state == BreakerState.HALF_OPEN or \
                self._failure_count >= self._cfg.failure_threshold:
            self._state = BreakerState.OPEN
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        self._state = BreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
