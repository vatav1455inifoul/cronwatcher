"""Tests for RunHistory and HistoryReport."""
from datetime import datetime, timezone

import pytest

from cronwatcher.history import RunHistory, RunRecord
from cronwatcher.history_reporter import HistoryReport


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _record(job: str, delay: float = 0.0, missed: bool = False) -> RunRecord:
    return RunRecord(job_name=job, ran_at=_now(), delay_seconds=delay, missed=missed)


# --- RunHistory ---

def test_record_and_get():
    h = RunHistory()
    r = _record("backup")
    h.record(r)
    assert h.get("backup") == [r]


def test_get_missing_returns_empty():
    h = RunHistory()
    assert h.get("nonexistent") == []


def test_last_returns_most_recent():
    h = RunHistory()
    r1 = _record("job")
    r2 = _record("job", delay=5.0)
    h.record(r1)
    h.record(r2)
    assert h.last("job") is r2


def test_last_missing_returns_none():
    h = RunHistory()
    assert h.last("ghost") is None


def test_eviction_at_cap():
    h = RunHistory(max_records_per_job=3)
    records = [_record("job") for _ in range(5)]
    for r in records:
        h.record(r)
    stored = h.get("job")
    assert len(stored) == 3
    assert stored == records[-3:]


def test_missed_runs_filter():
    h = RunHistory()
    h.record(_record("job", missed=True))
    h.record(_record("job", delay=2.0))
    h.record(_record("job"))
    assert len(h.missed_runs("job")) == 1


def test_delayed_runs_filter():
    h = RunHistory()
    h.record(_record("job", missed=True))
    h.record(_record("job", delay=3.0))
    h.record(_record("job"))
    delayed = h.delayed_runs("job")
    assert len(delayed) == 1
    assert delayed[0].delay_seconds == 3.0


def test_all_jobs():
    h = RunHistory()
    h.record(_record("a"))
    h.record(_record("b"))
    assert set(h.all_jobs()) == {"a", "b"}


def test_len():
    h = RunHistory()
    h.record(_record("a"))
    h.record(_record("a"))
    h.record(_record("b"))
    assert len(h) == 3


# --- HistoryReport ---

def test_render_contains_job_name():
    h = RunHistory()
    h.record(_record("daily-backup", delay=10.0))
    report = HistoryReport(h).render()
    assert "daily-backup" in report


def test_render_shows_status_ok():
    h = RunHistory()
    h.record(_record("myjob"))
    report = HistoryReport(h).render()
    assert "OK" in report


def test_render_shows_delayed():
    h = RunHistory()
    h.record(_record("myjob", delay=30.0))
    report = HistoryReport(h).render()
    assert "DELAYED" in report


def test_render_no_history_message():
    h = RunHistory()
    report = HistoryReport(h).render()
    assert "no history" in report


def test_render_filter_by_job():
    h = RunHistory()
    h.record(_record("job-a"))
    h.record(_record("job-b"))
    report = HistoryReport(h).render(job_name="job-a")
    assert "job-a" in report
    assert "job-b" not in report
