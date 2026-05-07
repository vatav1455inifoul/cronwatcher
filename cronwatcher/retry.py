"""Retry policy for alert delivery with exponential backoff."""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behaviour."""
    max_attempts: int = 3
    base_delay: float = 1.0   # seconds
    backoff_factor: float = 2.0
    max_delay: float = 60.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be > 0")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be >= 1")

    def delay_for(self, attempt: int) -> float:
        """Return the sleep duration before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


@dataclass
class RetryResult:
    success: bool
    attempts: int
    last_exception: Optional[Exception] = field(default=None)


def with_retry(
    fn: Callable[[], None],
    policy: RetryPolicy,
    *,
    _sleep: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Call *fn* up to *policy.max_attempts* times, sleeping between retries.

    Returns a :class:`RetryResult` describing the outcome.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(policy.max_attempts):
        delay = policy.delay_for(attempt)
        if delay > 0:
            logger.debug("Retry attempt %d — sleeping %.1fs", attempt, delay)
            _sleep(delay)
        try:
            fn()
            return RetryResult(success=True, attempts=attempt + 1)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "Attempt %d/%d failed: %s",
                attempt + 1,
                policy.max_attempts,
                exc,
            )
    return RetryResult(success=False, attempts=policy.max_attempts, last_exception=last_exc)
