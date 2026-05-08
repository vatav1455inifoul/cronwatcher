"""Notifier wrapper that applies a circuit breaker to any notifier callable."""
from __future__ import annotations

from cronwatcher.alerter import Alert
from cronwatcher.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, BreakerState
from typing import Callable


class CircuitBreakerNotifier:
    """Wraps a notifier and stops calling it while the circuit is open.

    Parameters
    ----------
    notifier:
        Any callable that accepts an :class:`~cronwatcher.alerter.Alert`.
    config:
        Optional :class:`CircuitBreakerConfig`; defaults are used when omitted.
    """

    def __init__(
        self,
        notifier: Callable[[Alert], None],
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self._notifier = notifier
        self._breaker = CircuitBreaker(config)
        self._blocked: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(self, alert: Alert) -> None:
        """Forward *alert* to the wrapped notifier unless the circuit is open."""
        try:
            self._breaker.call(self._notifier, alert)
        except RuntimeError:
            # Circuit is open — swallow the block silently but count it.
            self._blocked += 1

    @property
    def state(self) -> BreakerState:
        """Current state of the underlying circuit breaker."""
        return self._breaker.state

    @property
    def blocked(self) -> int:
        """Number of calls blocked while the circuit was open."""
        return self._blocked

    def reset(self) -> None:
        """Manually close the circuit and reset counters."""
        self._breaker.reset()
        self._blocked = 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CircuitBreakerNotifier(notifier={self._notifier!r}, "
            f"state={self.state.value})"
        )
