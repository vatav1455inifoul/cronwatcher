"""Tests for snapshot.py and snapshot_store.py."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatcher.snapshot import (
    JobSnapshot,
    SnapshotCollector,
    WatcherSnapshot,
)
from cronwatcher.snapshot_store import SnapshotStore


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# JobSnapshot
# ---------------------------------------------------------------------------

def test_job_snapshot_to_dict_no_last_run():
    js = JobSnapshot(name="backup", last_run=None, is_missed=True, is_delayed=False, delay_seconds=0.0)
    d = js.to_dict()
    assert d["name"] == "backup"
    assert d["last_run"] is None
    assert d["is_missed"] is True


def test_job_snapshot_to_dict_with_last_run():
    t = _utc(2024, 1, 1, 12, 0, 0)
    js = JobSnapshot(name="sync", last_run=t, is_missed=False, is_delayed=True, delay_seconds=45.5)
    d = js.to_dict()
    assert d["last_run"] == t.isoformat()
    assert d["delay_seconds"] == 45.5


# ---------------------------------------------------------------------------
# WatcherSnapshot
# ---------------------------------------------------------------------------

def _make_snapshot():
    jobs = [
        JobSnapshot("a", None, is_missed=True, is_delayed=False, delay_seconds=0.0),
        JobSnapshot("b", None, is_missed=False, is_delayed=True, delay_seconds=10.0),
        JobSnapshot("c", None, is_missed=False, is_delayed=False, delay_seconds=0.0),
    ]
    return WatcherSnapshot(captured_at=_utc(2024, 6, 1, 0, 0, 0), jobs=jobs)


def test_watcher_snapshot_missed():
    snap = _make_snapshot()
    assert [j.name for j in snap.missed] == ["a"]


def test_watcher_snapshot_delayed():
    snap = _make_snapshot()
    assert [j.name for j in snap.delayed] == ["b"]


def test_watcher_snapshot_ok():
    snap = _make_snapshot()
    assert [j.name for j in snap.ok] == ["c"]


def test_watcher_snapshot_to_dict_summary():
    snap = _make_snapshot()
    d = snap.to_dict()
    assert d["summary"] == {"total": 3, "ok": 1, "delayed": 1, "missed": 1}


# ---------------------------------------------------------------------------
# SnapshotCollector
# ---------------------------------------------------------------------------

def _fake_status(missed=False, delayed=False, delay_sec=0.0):
    s = MagicMock()
    s.is_missed = missed
    s.is_delayed = delayed
    s.delay_seconds = delay_sec
    return s


def test_snapshot_collector_capture():
    tracker_a = MagicMock(last_run=None)
    tracker_a.check.return_value = _fake_status(missed=True)
    tracker_b = MagicMock(last_run=_utc(2024, 1, 1, 0, 0, 0))
    tracker_b.check.return_value = _fake_status(delayed=True, delay_sec=30.0)

    registry = MagicMock()
    registry.__iter__ = MagicMock(return_value=iter([("job_a", tracker_a), ("job_b", tracker_b)]))

    collector = SnapshotCollector(registry)
    snap = collector.capture(now=_utc(2024, 1, 1, 1, 0, 0))

    assert len(snap.jobs) == 2
    assert snap.jobs[0].name == "job_a"
    assert snap.jobs[0].is_missed is True
    assert snap.jobs[1].delay_seconds == 30.0


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    return SnapshotStore(tmp_path / "snaps" / "data.jsonl")


def test_store_file_created(store):
    assert store._path.exists()


def test_store_save_and_load(store):
    snap = _make_snapshot()
    store.save(snap)
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].captured_at == snap.captured_at
    assert len(loaded[0].jobs) == 3


def test_store_latest(store):
    snap1 = WatcherSnapshot(captured_at=_utc(2024, 1, 1, 0, 0, 0), jobs=[])
    snap2 = WatcherSnapshot(captured_at=_utc(2024, 1, 2, 0, 0, 0), jobs=[])
    store.save(snap1)
    store.save(snap2)
    latest = store.latest()
    assert latest.captured_at == snap2.captured_at


def test_store_latest_empty_returns_none(store):
    assert store.latest() is None


def test_store_clear(store):
    store.save(_make_snapshot())
    store.clear()
    assert store.load_all() == []
