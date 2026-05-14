"""Tests for CorrelatingAlerter."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.correlation import CorrelationGroup
from cronwatcher.correlation_alerter import CorrelatingAlerter


def _utc(offset: float = 0) -> datetime:
    return datetime(2024, 6, 1, 0, 0, 0) + timedelta(seconds=offset)


def _make_alerter(window: int = 60, now_offset: float = 0):
    inner = Alerter()
    t = [_utc(now_offset)]

    def _now():
        return t[0]

    ca = CorrelatingAlerter(inner, window_seconds=window, _now=_now)
    return ca, inner, t


def test_alert_missed_forwards_to_inner():
    ca, inner, _ = _make_alerter()
    ca.alert_missed("backup", 120)
    assert len(inner.history) == 1
    assert inner.history[0].level == AlertLevel.CRITICAL


def test_alert_delayed_forwards_to_inner():
    ca, inner, _ = _make_alerter()
    ca.alert_delayed("sync", 45)
    assert len(inner.history) == 1
    assert inner.history[0].level == AlertLevel.WARNING


def test_send_forwards_arbitrary_alert():
    ca, inner, _ = _make_alerter()
    alert = Alert(job_name="etl", level=AlertLevel.INFO, message="ok")
    ca.send(alert)
    assert len(inner.history) == 1


def test_no_systemic_group_for_single_job():
    ca, inner, t = _make_alerter(window=60)
    ca.alert_missed("job_a", 10)
    ca.alert_missed("job_a", 20)
    group = ca.flush()
    assert group is not None
    assert group.is_systemic is False
    assert ca.systemic_groups == []


def test_systemic_handler_called_for_multiple_jobs():
    ca, inner, t = _make_alerter(window=60)
    handler = MagicMock()
    ca.add_systemic_handler(handler)

    ca.alert_missed("job_a", 10)
    ca.alert_missed("job_b", 20)
    ca.flush()

    handler.assert_called_once()
    group: CorrelationGroup = handler.call_args[0][0]
    assert group.is_systemic is True


def test_systemic_groups_list_grows():
    ca, inner, t = _make_alerter(window=60)
    ca.alert_missed("job_a", 10)
    ca.alert_missed("job_b", 20)
    ca.flush()
    assert len(ca.systemic_groups) == 1


def test_handler_not_called_when_single_job():
    ca, _, _ = _make_alerter(window=60)
    handler = MagicMock()
    ca.add_systemic_handler(handler)
    ca.alert_missed("only_job", 5)
    ca.flush()
    handler.assert_not_called()


def test_multiple_handlers_all_called():
    ca, _, _ = _make_alerter(window=60)
    h1, h2 = MagicMock(), MagicMock()
    ca.add_systemic_handler(h1)
    ca.add_systemic_handler(h2)
    ca.alert_missed("job_a", 10)
    ca.alert_delayed("job_b", 30)
    ca.flush()
    h1.assert_called_once()
    h2.assert_called_once()
