"""Tests for SilencedAlerter."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.silenced_alerter import SilencedAlerter
from cronwatcher.silencer import Silencer, SilenceWindow


def _utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def _active_window(job_name=None) -> SilenceWindow:
    return SilenceWindow(
        start=_utc(seconds=-60),
        end=_utc(seconds=60),
        job_name=job_name,
    )


def _make_sa(job_name=None):
    inner = Alerter()
    inner.send = MagicMock()
    silencer = Silencer()
    if job_name is not None:
        silencer.add(_active_window(job_name=job_name))
    sa = SilencedAlerter(alerter=inner, silencer=silencer)
    return sa, inner


def _alert(job_name="backup", level=AlertLevel.CRITICAL) -> Alert:
    return Alert(job_name=job_name, level=level, message="test")


def test_send_forwards_when_not_silenced():
    sa, inner = _make_sa()
    alert = _alert()
    sa.send(alert)
    inner.send.assert_called_once_with(alert)


def test_send_suppresses_when_silenced():
    sa, inner = _make_sa(job_name="backup")
    sa.send(_alert(job_name="backup"))
    inner.send.assert_not_called()
    assert sa.suppressed_count == 1


def test_suppressed_list_contains_alert():
    sa, _ = _make_sa(job_name="backup")
    a = _alert(job_name="backup")
    sa.send(a)
    assert sa.suppressed[0] is a


def test_other_job_not_suppressed():
    sa, inner = _make_sa(job_name="backup")
    sa.send(_alert(job_name="deploy"))
    inner.send.assert_called_once()
    assert sa.suppressed_count == 0


def test_alert_missed_suppressed():
    sa, inner = _make_sa(job_name="backup")
    sa.alert_missed("backup", 120)
    inner.send.assert_not_called()
    assert sa.suppressed_count == 1


def test_alert_delayed_forwarded_when_not_silenced():
    sa, inner = _make_sa()
    sa.alert_delayed("nightly", 45)
    inner.send.assert_called_once()


def test_suppressed_returns_copy():
    sa, _ = _make_sa(job_name="backup")
    sa.send(_alert())
    result = sa.suppressed
    result.clear()
    assert sa.suppressed_count == 1
