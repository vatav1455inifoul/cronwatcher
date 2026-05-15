"""Alert budget tracking — limits total alerts fired within a rolling window."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BudgetConfig:
    max_alerts: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")


class AlertBudget:
    """Tracks how many alerts have fired in a rolling time window.

    Once the budget is exhausted, ``should_allow`` returns False until
    old entries fall outside the window.
    """

    def __init__(self, config: BudgetConfig, *, _now=None) -> None:
        self._config = config
        self._now = _now or _utcnow
        self._timestamps: Deque[datetime] = deque()

    # ------------------------------------------------------------------
    def _evict_old(self, now: datetime) -> None:
        cutoff = now.timestamp() - self._config.window_seconds
        while self._timestamps and self._timestamps[0].timestamp() < cutoff:
            self._timestamps.popleft()

    def should_allow(self) -> bool:
        """Return True if an alert is within budget."""
        now = self._now()
        self._evict_old(now)
        return len(self._timestamps) < self._config.max_alerts

    def record(self) -> None:
        """Record that an alert was fired (call after sending)."""
        self._timestamps.append(self._now())

    @property
    def used(self) -> int:
        """Number of alerts fired within the current window."""
        self._evict_old(self._now())
        return len(self._timestamps)

    @property
    def remaining(self) -> int:
        """Remaining budget within the current window."""
        return max(0, self._config.max_alerts - self.used)

    def reset(self) -> None:
        """Clear all recorded timestamps (useful for testing)."""
        self._timestamps.clear()
