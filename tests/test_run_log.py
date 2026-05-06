"""Tests for cronwatcher.run_log."""

from __future__ import annotations

import pytest
from pathlib import Path

from cronwatcher.run_log import RunLog


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "runs" / "run.log"


@pytest.fixture
def run_log(log_path: Path) -> RunLog:
    return RunLog(log_path)


def test_file_created_on_init(log_path: Path) -> None:
    RunLog(log_path)
    assert log_path.exists()


def test_parent_dirs_created(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "run.log"
    RunLog(deep)
    assert deep.exists()


def test_append_and_read_all(run_log: RunLog) -> None:
    run_log.append("backup", "ok")
    entries = run_log.read_all()
    assert len(entries) == 1
    assert entries[0]["job"] == "backup"
    assert entries[0]["status"] == "ok"
    assert entries[0]["delay_seconds"] is None


def test_append_with_delay(run_log: RunLog) -> None:
    run_log.append("sync", "delayed", delay_seconds=12.5)
    entries = run_log.read_all()
    assert entries[0]["delay_seconds"] == pytest.approx(12.5)


def test_multiple_entries_preserved(run_log: RunLog) -> None:
    run_log.append("job_a", "ok")
    run_log.append("job_b", "missed")
    run_log.append("job_a", "delayed", delay_seconds=5.0)
    assert len(run_log.read_all()) == 3


def test_read_job_filters_by_name(run_log: RunLog) -> None:
    run_log.append("job_a", "ok")
    run_log.append("job_b", "missed")
    run_log.append("job_a", "delayed", delay_seconds=3.0)

    results = run_log.read_job("job_a")
    assert len(results) == 2
    assert all(r["job"] == "job_a" for r in results)


def test_read_job_missing_returns_empty(run_log: RunLog) -> None:
    run_log.append("job_a", "ok")
    assert run_log.read_job("nonexistent") == []


def test_clear_removes_entries(run_log: RunLog) -> None:
    run_log.append("job_a", "ok")
    run_log.append("job_b", "missed")
    run_log.clear()
    assert run_log.read_all() == []


def test_entries_have_timestamp(run_log: RunLog) -> None:
    from datetime import datetime
    run_log.append("job_x", "ok")
    entry = run_log.read_all()[0]
    assert isinstance(entry["timestamp"], datetime)


def test_append_after_clear(run_log: RunLog) -> None:
    run_log.append("job_a", "ok")
    run_log.clear()
    run_log.append("job_b", "missed")
    entries = run_log.read_all()
    assert len(entries) == 1
    assert entries[0]["job"] == "job_b"
