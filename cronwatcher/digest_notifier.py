"""Notifier that batches alerts into periodic digests."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, List, Optional

from cronwatcher.alerter import Alert
from cronwatcher.digest import DigestCollector


def _utcnow() -> datetime:
    return datetime.utcnow()


class DigestNotifier:
    """Wraps a downstream notifier, batching alerts until the window expires.

    Call :meth:`flush` (or rely on :meth:`__call__` with *force_flush=True*)
    to drain the buffer and send one summary message.
    """

    def __init__(
        self,
        downstream: Callable[[Alert], None],
        window: timedelta = timedelta(hours=1),
        _now: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._downstream = downstream
        self._now = _now or _utcnow
        self._collector = DigestCollector(window=window, _now=_now)
        self._last_flush: datetime = self._now()
        self._sent_digests: List[str] = []

    # ------------------------------------------------------------------
    def __call__(self, alert: Alert) -> None:
        """Collect the alert; auto-flush if the window has elapsed."""
        self._collector.collect(alert)
        if (self._now() - self._last_flush) >= self._collector.window:
            self.flush()

    def flush(self) -> None:
        """Force-send the current digest to the downstream notifier."""
        digest_text = self._collector.flush()
        self._last_flush = self._now()
        self._sent_digests.append(digest_text)
        # Build a synthetic Alert so the downstream callable receives a
        # proper object (mirrors the rest of the notifier contract).
        from cronwatcher.alerter import Alert, AlertLevel
        digest_alert = Alert(
            job_name="__digest__",
            level=AlertLevel.INFO,
            message=digest_text,
        )
        self._downstream(digest_alert)

    @property
    def pending(self) -> int:
        return self._collector.pending

    @property
    def sent_digests(self) -> List[str]:
        return list(self._sent_digests)

    def __repr__(self) -> str:
        return (
            f"DigestNotifier(window={self._collector.window}, "
            f"pending={self.pending})"
        )
