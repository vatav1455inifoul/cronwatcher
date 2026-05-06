"""Tests for StateStore and PersistentWatcher."""

import os
import tempfile
from datetime import datetime

import pytest

from cronwatcher.persistence import StateStore
from cronwatcher.registry import JobRegistry
from cronwatcher.persistent_watcher import PersistentWatcher


@pytest.fixture()
def tmp_store(tmp_path):
    return StateStore(path=str(tmp_path / "state.json"))


def test_set_and_get_last_run(tmp_store):
    ts = datetime(2024, 1, 15, 12, 0, 0)
    tmp_store.set_last_run("backup", ts)
    assert tmp_store.get_last_run("backup") == ts


def test_get_missing_job_returns_none(tmp_store):
    assert tmp_store.get_last_run("nonexistent") is None


def test_save_and_reload(tmp_path):
    path = str(tmp_path / "state.json")
    store = StateStore(path=path)
    ts = datetime(2024, 6, 1, 8, 30, 0)
    store.set_last_run("cleanup", ts)
    store.save()

    reloaded = StateStore(path=path)
    assert reloaded.get_last_run("cleanup") == ts


def test_all_jobs(tmp_store):
    tmp_store.set_last_run("job_a", datetime(2024, 1, 1, 0, 0, 0))
    tmp_store.set_last_run("job_b", datetime(2024, 1, 2, 0, 0, 0))
    assert set(tmp_store.all_jobs()) == {"job_a", "job_b"}


def test_remove_job(tmp_store):
    tmp_store.set_last_run("job_x", datetime(2024, 1, 1, 0, 0, 0))
    tmp_store.remove("job_x")
    assert tmp_store.get_last_run("job_x") is None


def test_clear(tmp_store):
    tmp_store.set_last_run("a", datetime(2024, 1, 1, 0, 0, 0))
    tmp_store.clear()
    assert tmp_store.all_jobs() == []


def test_persistent_watcher_record_run_persists(tmp_path):
    path = str(tmp_path / "state.json")
    store = StateStore(path=path)
    registry = JobRegistry()
    registry.register("daily", "0 9 * * *", tolerance_seconds=300)
    watcher = PersistentWatcher(registry, store)

    ts = datetime(2024, 3, 10, 9, 0, 0)
    watcher.record_run("daily", ts)

    reloaded_store = StateStore(path=path)
    assert reloaded_store.get_last_run("daily") == ts


def test_persistent_watcher_restores_state(tmp_path):
    path = str(tmp_path / "state.json")
    ts = datetime(2024, 3, 10, 9, 0, 0)

    store = StateStore(path=path)
    store.set_last_run("daily", ts)
    store.save()

    registry = JobRegistry()
    registry.register("daily", "0 9 * * *", tolerance_seconds=300)
    watcher = PersistentWatcher(registry, StateStore(path=path))

    tracker = registry["daily"]
    assert tracker.last_run == ts
