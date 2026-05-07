"""Tests for HealthServer HTTP endpoint."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.health import HealthReport, JobHealth
from cronwatcher.health_server import HealthServer


def _make_checker(overall: str = "ok"):
    is_missed = overall == "critical"
    is_delayed = overall == "warning"
    report = HealthReport()
    report.jobs = [
        JobHealth("test_job", datetime.now(timezone.utc), is_missed, is_delayed, 0.0)
    ]
    checker = MagicMock()
    checker.check.return_value = report
    return checker


@pytest.fixture()
def server():
    checker = _make_checker("ok")
    srv = HealthServer(checker, host="127.0.0.1", port=19876)
    srv.start()
    time.sleep(0.05)
    yield srv
    srv.stop()


def test_health_returns_200_when_ok(server):
    with urllib.request.urlopen("http://127.0.0.1:19876/health") as resp:
        assert resp.status == 200


def test_health_returns_json(server):
    with urllib.request.urlopen("http://127.0.0.1:19876/health") as resp:
        data = json.loads(resp.read())
    assert "status" in data
    assert "jobs" in data


def test_health_503_when_critical():
    checker = _make_checker("critical")
    srv = HealthServer(checker, host="127.0.0.1", port=19877)
    srv.start()
    time.sleep(0.05)
    try:
        try:
            urllib.request.urlopen("http://127.0.0.1:19877/health")
            pytest.fail("Expected HTTPError")
        except urllib.error.HTTPError as exc:
            assert exc.code == 503
    finally:
        srv.stop()


def test_unknown_path_returns_404(server):
    try:
        urllib.request.urlopen("http://127.0.0.1:19876/unknown")
        pytest.fail("Expected HTTPError")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_address_property(server):
    assert server.address == "http://127.0.0.1:19876/health"
