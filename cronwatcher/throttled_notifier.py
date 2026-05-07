"""Wraps a notifier with throttle logic so repeated alerts don't spam handlers."""

from __future__ import annotations

from typing import Callable

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.throttle import AlertThrottle, ThrottleRule


class ThrottledNotifier:
    """Decorator around a callable notifier that suppresses sends within a throttle window.

    Parameters
    ----------
    notifier:
        Any callable that accepts an :class:`~cronwatcher.alerter.Alert`.
    rules:
        Mapping of ``AlertLevel`` to :class:`~cronwatcher.throttle.ThrottleRule`.
        Levels not present in the mapping are never throttled.
    """

    def __init__(
        self,
        notifier: Callable[[Alert], None],
        rules: dict[AlertLevel, ThrottleRule] | None = None,
    ) -> None:
        self._notifier = notifier
        self._throttle = AlertThrottle(rules or {})
        self._suppressed: int = 0
        self._sent: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(self, alert: Alert) -> bool:
        """Send *alert* through the underlying notifier if the throttle allows it.

        Returns
        -------
        bool
            ``True`` if the alert was forwarded, ``False`` if it was suppressed.
        """
        if not self._throttle.should_send(alert):
            self._suppressed += 1
            return False

        self._notifier(alert)
        self._sent += 1
        return True

    @property
    def sent(self) -> int:
        """Total number of alerts forwarded to the underlying notifier."""
        return self._sent

    @property
    def suppressed(self) -> int:
        """Total number of alerts suppressed by the throttle."""
        return self._suppressed

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ThrottledNotifier(notifier={self._notifier!r}, "
            f"sent={self._sent}, suppressed={self._suppressed})"
        )
