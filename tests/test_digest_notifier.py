"""Tests for DigestNotifier."""
from datetime import datetime, timedelta
from typing import List

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.digest_notifier import DigestNotifier


def _alert(name: str = "job1", level: AlertLevel = AlertLevel.CRITICAL) -> Alert:
    return Alert(job_name=name, level=level, message="test")


class _FakeNow:
    def __init__(self, start: datetime):
        self._t = start

    def __call__(self) -> datetime:
        return self._t

    def advance(self, delta: timedelta) -> None:
        self._t += delta


def _make_dn(window: timedelta = timedelta(hours=1)):
    received: List[Alert] = []
    clock = _FakeNow(datetime(2024, 6, 1, 0, 0, 0))
    dn = DigestNotifier(downstream=received.append, window=window, _now=clock)
    return dn, received, clock


def test_collect_does_not_immediately_forward():
    dn, received, _ = _make_dn()
    dn(_alert())
    assert len(received) == 0


def test_pending_increments_on_collect():
    dn, _, _ = _make_dn()
    dn(_alert())
    assert dn.pending == 1


def test_flush_sends_to_downstream():
    dn, received, _ = _make_dn()
    dn(_alert())
    dn.flush()
    assert len(received) == 1


def test_flush_clears_pending():
    dn, _, _ = _make_dn()
    dn(_alert())
    dn.flush()
    assert dn.pending == 0


def test_auto_flush_when_window_elapsed():
    dn, received, clock = _make_dn(window=timedelta(minutes=30))
    dn(_alert())  # collected, no flush yet
    clock.advance(timedelta(minutes=31))
    dn(_alert())  # triggers auto-flush
    assert len(received) == 1  # one digest sent


def test_sent_digests_records_history():
    dn, _, _ = _make_dn()
    dn(_alert())
    dn.flush()
    assert len(dn.sent_digests) == 1


def test_repr_contains_window():
    dn, _, _ = _make_dn(window=timedelta(minutes=15))
    assert "0:15:00" in repr(dn) or "15" in repr(dn)


def test_empty_flush_still_sends_downstream():
    dn, received, _ = _make_dn()
    dn.flush()
    assert len(received) == 1
    assert "No alerts" in dn.sent_digests[0]
