"""Tests for the CLI module."""

import json
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest

from cronwatcher.cli import main
from cronwatcher.registry import JobRegistry


FIXED_NOW = datetime(2024, 1, 15, 12, 0, 0)


@pytest.fixture
def populated_registry():
    reg = JobRegistry()
    reg.register("heartbeat", "* * * * *", tolerance_seconds=30)
    reg.register("cleanup", "0 * * * *", tolerance_seconds=120)
    reg.record_run("heartbeat", FIXED_NOW - timedelta(seconds=5))
    return reg


def test_no_command_prints_help_and_returns_1(populated_registry, capsys):
    result = main(argv=[], registry=populated_registry)
    assert result == 1


def test_report_text_exits_zero(populated_registry, capsys):
    with patch("cronwatcher.reporter.datetime") as mock_dt:
        mock_dt.utcnow.return_value = FIXED_NOW
        result = main(argv=["report"], registry=populated_registry)
    assert result == 0


def test_report_text_output_contains_job_names(populated_registry, capsys):
    result = main(argv=["report", "--format", "text"], registry=populated_registry)
    captured = capsys.readouterr()
    assert "heartbeat" in captured.out
    assert "cleanup" in captured.out
    assert result == 0


def test_report_text_contains_header(populated_registry, capsys):
    main(argv=["report"], registry=populated_registry)
    captured = capsys.readouterr()
    assert "CronWatcher Report" in captured.out


def test_report_json_is_valid_json(populated_registry, capsys):
    result = main(argv=["report", "--format", "json"], registry=populated_registry)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "jobs" in data
    assert "total" in data
    assert result == 0


def test_report_json_contains_expected_fields(populated_registry, capsys):
    main(argv=["report", "--format", "json"], registry=populated_registry)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 2
    job_names = [j["name"] for j in data["jobs"]]
    assert "heartbeat" in job_names
    assert "cleanup" in job_names
    for job in data["jobs"]:
        assert "status" in job
        assert "run_count" in job


def test_report_json_status_values_are_valid(populated_registry, capsys):
    main(argv=["report", "--format", "json"], registry=populated_registry)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    valid_statuses = {"OK", "MISSED", "DELAYED"}
    for job in data["jobs"]:
        assert job["status"] in valid_statuses
