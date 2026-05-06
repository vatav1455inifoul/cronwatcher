"""Simple polling daemon that periodically checks all jobs and fires alerts."""

from __future__ import annotations

import logging
import signal
import time
from typing import Optional

from cronwatcher.persistent_watcher import PersistentWatcher

logger = logging.getLogger(__name__)


class Daemon:
    """Runs check_all on a PersistentWatcher at a fixed interval."""

    def __init__(
        self,
        watcher: PersistentWatcher,
        interval: int = 60,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be a positive integer (seconds)")
        self.watcher = watcher
        self.interval = interval
        self._running = False
        self._tick_count = 0

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Block and run the check loop until stop() is called or a signal arrives."""
        self._running = True
        self._tick_count = 0

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        logger.info("Daemon started (interval=%ds)", self.interval)
        try:
            while self._running:
                self._tick()
                self._sleep_interruptible(self.interval)
        finally:
            logger.info("Daemon stopped after %d tick(s)", self._tick_count)

    def stop(self) -> None:
        """Request a graceful shutdown."""
        self._running = False

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        self._tick_count += 1
        logger.debug("Tick %d — running check_all", self._tick_count)
        try:
            self.watcher.check_all()
        except Exception:  # pragma: no cover
            logger.exception("Unexpected error during check_all")

    def _sleep_interruptible(self, seconds: int) -> None:
        """Sleep in small chunks so stop() is noticed quickly."""
        chunk = min(1, seconds)
        elapsed = 0
        while self._running and elapsed < seconds:
            time.sleep(chunk)
            elapsed += chunk

    def _handle_signal(self, signum: int, _frame: object) -> None:  # pragma: no cover
        logger.info("Received signal %d — stopping", signum)
        self.stop()
