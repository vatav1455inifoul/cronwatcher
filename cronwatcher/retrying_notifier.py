"""Wraps any callable notifier with retry logic."""
from __future__ import annotations

import logging
from typing import Callable

from cronwatcher.alerter import Alert
from cronwatcher.retry import RetryPolicy, RetryResult, with_retry

logger = logging.getLogger(__name__)

# A notifier is any callable that accepts an Alert.
NotifierFn = Callable[[Alert], None]


class RetryingNotifier:
    """Decorator that retries a notifier callable on failure.

    Parameters
    ----------
    notifier:
        The underlying notifier (e.g. :class:`~cronwatcher.notifier.EmailNotifier`).
    policy:
        Retry configuration.  Defaults to 3 attempts with 2× backoff.
    """

    def __init__(
        self,
        notifier: NotifierFn,
        policy: RetryPolicy | None = None,
    ) -> None:
        self._notifier = notifier
        self._policy = policy or RetryPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def __call__(self, alert: Alert) -> RetryResult:
        """Attempt to deliver *alert*, retrying according to the policy."""
        result = with_retry(lambda: self._notifier(alert), self._policy)
        if result.success:
            logger.debug(
                "Alert delivered for '%s' after %d attempt(s)",
                alert.job_name,
                result.attempts,
            )
        else:
            logger.error(
                "Failed to deliver alert for '%s' after %d attempt(s): %s",
                alert.job_name,
                result.attempts,
                result.last_exception,
            )
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetryingNotifier(notifier={self._notifier!r}, policy={self._policy!r})"
        )
