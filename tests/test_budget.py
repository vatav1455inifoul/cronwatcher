"""Tests for alert budget and budgeted alerter."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.budget import AlertBudget, BudgetConfig
from cronwatcher.budgeted_alerter import BudgetedAlerter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeNow:
    def __init__(self, ts: float = 1_000_000.0):
        self._ts = ts

    def __call__(self) -> datetime:
        return datetime.fromtimestamp(self._ts, tz=timezone.utc)

    def advance(self, seconds: float) -> None:
        self._ts += seconds


def _alert(name: str = "job") -> Alert:
    return Alert(job_name=name, level=AlertLevel.WARNING, message="test")


# ---------------------------------------------------------------------------
# BudgetConfig validation
# ---------------------------------------------------------------------------

def test_invalid_max_alerts_raises():
    with pytest.raises(ValueError):
        BudgetConfig(max_alerts=0, window_seconds=60)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        BudgetConfig(max_alerts=5, window_seconds=0)


# ---------------------------------------------------------------------------
# AlertBudget behaviour
# ---------------------------------------------------------------------------

def test_allow_up_to_max():
    now = _FakeNow()
    budget = AlertBudget(BudgetConfig(max_alerts=3, window_seconds=60), _now=now)
    for _ in range(3):
        assert budget.should_allow()
        budget.record()
    assert not budget.should_allow()


def test_used_and_remaining():
    now = _FakeNow()
    budget = AlertBudget(BudgetConfig(max_alerts=5, window_seconds=60), _now=now)
    budget.record()
    budget.record()
    assert budget.used == 2
    assert budget.remaining == 3


def test_old_entries_evicted():
    now = _FakeNow()
    budget = AlertBudget(BudgetConfig(max_alerts=2, window_seconds=30), _now=now)
    budget.record()
    budget.record()
    assert not budget.should_allow()
    now.advance(31)
    assert budget.should_allow()


def test_reset_clears_all():
    now = _FakeNow()
    budget = AlertBudget(BudgetConfig(max_alerts=2, window_seconds=60), _now=now)
    budget.record()
    budget.record()
    budget.reset()
    assert budget.used == 0
    assert budget.should_allow()


# ---------------------------------------------------------------------------
# BudgetedAlerter
# ---------------------------------------------------------------------------

def _make_budgeted(max_alerts: int = 2, window: int = 60):
    inner = MagicMock(spec=Alerter)
    now = _FakeNow()
    cfg = BudgetConfig(max_alerts=max_alerts, window_seconds=window)
    alerter = BudgetedAlerter(inner, cfg, _now=now)
    return alerter, inner, now


def test_forwards_within_budget():
    alerter, inner, _ = _make_budgeted(max_alerts=3)
    alerter.send(_alert())
    alerter.send(_alert())
    assert inner.send.call_count == 2
    assert len(alerter.suppressed) == 0


def test_suppresses_beyond_budget():
    alerter, inner, _ = _make_budgeted(max_alerts=2)
    for _ in range(4):
        alerter.send(_alert())
    assert inner.send.call_count == 2
    assert len(alerter.suppressed) == 2


def test_alert_missed_uses_critical_level():
    alerter, inner, _ = _make_budgeted(max_alerts=5)
    alerter.alert_missed("backup")
    sent: Alert = inner.send.call_args[0][0]
    assert sent.level == AlertLevel.CRITICAL
    assert sent.job_name == "backup"


def test_alert_delayed_uses_warning_level():
    alerter, inner, _ = _make_budgeted(max_alerts=5)
    alerter.alert_delayed("sync", 45.0)
    sent: Alert = inner.send.call_args[0][0]
    assert sent.level == AlertLevel.WARNING
    assert "45.0" in sent.message


def test_budget_property_exposed():
    alerter, _, _ = _make_budgeted(max_alerts=3)
    assert alerter.budget.remaining == 3
