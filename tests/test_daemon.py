"""Tests for cronwatcher.daemon.Daemon."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.daemon import Daemon


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_daemon(interval: int = 60) -> tuple[Daemon, MagicMock]:
    watcher = MagicMock()
    return Daemon(watcher=watcher, interval=interval), watcher


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------

def test_invalid_interval_raises():
    watcher = MagicMock()
    with pytest.raises(ValueError, match="interval must be"):
        Daemon(watcher=watcher, interval=0)


def test_invalid_negative_interval_raises():
    watcher = MagicMock()
    with pytest.raises(ValueError):
        Daemon(watcher=watcher, interval=-5)


# ---------------------------------------------------------------------------
# tick behaviour
# ---------------------------------------------------------------------------

def test_tick_calls_check_all():
    daemon, watcher = _make_daemon()
    daemon._tick()
    watcher.check_all.assert_called_once()


def test_tick_increments_count():
    daemon, _ = _make_daemon()
    daemon._tick()
    daemon._tick()
    assert daemon._tick_count == 2


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

def test_stop_sets_running_false():
    daemon, _ = _make_daemon()
    daemon._running = True
    daemon.stop()
    assert daemon._running is False


def test_start_runs_ticks_then_stops():
    """Daemon should tick at least once and stop when stop() is called."""
    daemon, watcher = _make_daemon(interval=1)

    def _stopper():
        time.sleep(0.15)  # let one tick happen
        daemon.stop()

    t = threading.Thread(target=_stopper, daemon=True)
    with patch("signal.signal"):  # avoid messing with test-process signals
        t.start()
        daemon.start()
        t.join(timeout=3)

    assert watcher.check_all.call_count >= 1
    assert daemon._running is False


def test_tick_count_resets_on_start():
    daemon, _ = _make_daemon(interval=1)
    daemon._tick_count = 99

    def _stopper():
        time.sleep(0.05)
        daemon.stop()

    t = threading.Thread(target=_stopper, daemon=True)
    with patch("signal.signal"):
        t.start()
        daemon.start()
        t.join(timeout=3)

    # counter was reset to 0 then incremented by actual ticks
    assert daemon._tick_count < 99
