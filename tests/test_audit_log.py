"""Tests for cronwatcher.audit_log."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.audit_log import AuditEntry, AuditLog


@pytest.fixture()
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "audit" / "audit.log"


@pytest.fixture()
def audit_log(log_path: Path) -> AuditLog:
    return AuditLog(log_path)


def _alert(job: str = "backup", level: AlertLevel = AlertLevel.WARNING) -> Alert:
    return Alert(job_name=job, level=level, message=f"{job} is late")


def test_file_created_on_init(log_path: Path) -> None:
    AuditLog(log_path)
    assert log_path.exists()


def test_parent_dirs_created(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "audit.log"
    AuditLog(deep)
    assert deep.exists()


def test_record_returns_entry(audit_log: AuditLog) -> None:
    entry = audit_log.record(_alert())
    assert isinstance(entry, AuditEntry)
    assert entry.job_name == "backup"
    assert entry.level == "WARNING"


def test_all_empty_initially(audit_log: AuditLog) -> None:
    assert audit_log.all() == []


def test_record_and_all(audit_log: AuditLog) -> None:
    audit_log.record(_alert("job_a"))
    audit_log.record(_alert("job_b"))
    entries = audit_log.all()
    assert len(entries) == 2
    assert entries[0].job_name == "job_a"
    assert entries[1].job_name == "job_b"


def test_for_job_filters_correctly(audit_log: AuditLog) -> None:
    audit_log.record(_alert("alpha"))
    audit_log.record(_alert("beta"))
    audit_log.record(_alert("alpha"))
    result = audit_log.for_job("alpha")
    assert len(result) == 2
    assert all(e.job_name == "alpha" for e in result)


def test_for_job_unknown_returns_empty(audit_log: AuditLog) -> None:
    audit_log.record(_alert("alpha"))
    assert audit_log.for_job("ghost") == []


def test_last_returns_most_recent(audit_log: AuditLog) -> None:
    for i in range(5):
        audit_log.record(_alert(f"job_{i}"))
    last = audit_log.last(3)
    assert len(last) == 3
    assert last[-1].job_name == "job_4"


def test_last_fewer_than_n(audit_log: AuditLog) -> None:
    audit_log.record(_alert("only"))
    assert len(audit_log.last(10)) == 1


def test_entry_str_contains_fields(audit_log: AuditLog) -> None:
    entry = audit_log.record(_alert("myjob", AlertLevel.CRITICAL))
    s = str(entry)
    assert "myjob" in s
    assert "CRITICAL" in s


def test_clear_removes_entries(audit_log: AuditLog) -> None:
    audit_log.record(_alert())
    audit_log.record(_alert())
    audit_log.clear()
    assert audit_log.all() == []


def test_persists_across_instances(log_path: Path) -> None:
    a = AuditLog(log_path)
    a.record(_alert("persistent"))
    b = AuditLog(log_path)
    entries = b.all()
    assert len(entries) == 1
    assert entries[0].job_name == "persistent"
