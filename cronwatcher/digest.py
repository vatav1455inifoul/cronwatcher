"""Periodic digest report: collects alerts over a window and summarises them."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from cronwatcher.alerter import Alert, AlertLevel


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class DigestEntry:
    alert: Alert
    received_at: datetime

    def __str__(self) -> str:
        ts = self.received_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] {self.alert}"


class DigestCollector:
    """Accumulates alerts and flushes them as a formatted digest string."""

    def __init__(self, window: timedelta = timedelta(hours=1),
                 _now: Optional[Callable[[], datetime]] = None) -> None:
        if window.total_seconds() <= 0:
            raise ValueError("window must be positive")
        self._window = window
        self._now = _now or _utcnow
        self._entries: List[DigestEntry] = []

    def collect(self, alert: Alert) -> None:
        """Add an alert to the current digest window."""
        self._entries.append(DigestEntry(alert=alert, received_at=self._now()))

    def flush(self) -> str:
        """Return a formatted digest and clear the buffer."""
        entries = self._entries[:]
        self._entries.clear()
        if not entries:
            return "[Digest] No alerts in this period."
        lines = [f"[Digest] {len(entries)} alert(s):\n"]
        missed = [e for e in entries if e.alert.level == AlertLevel.CRITICAL]
        delayed = [e for e in entries if e.alert.level == AlertLevel.WARNING]
        if missed:
            lines.append(f"  MISSED ({len(missed)}):")
            for e in missed:
                lines.append(f"    {e}")
        if delayed:
            lines.append(f"  DELAYED ({len(delayed)}):")
            for e in delayed:
                lines.append(f"    {e}")
        return "\n".join(lines)

    @property
    def pending(self) -> int:
        """Number of alerts waiting to be flushed."""
        return len(self._entries)

    @property
    def window(self) -> timedelta:
        return self._window
