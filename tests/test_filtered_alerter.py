"""Tests for cronwatcher.filtered_alerter.FilteredAlerter."""
import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.filter import AlertFilter, FilterRule
from cronwatcher.filtered_alerter import FilteredAlerter


def _make_fa(pattern: str = "NOMATCH", level=None) -> FilteredAlerter:
    alerter = Alerter()
    af = AlertFilter()
    af.add_rule(FilterRule(job_pattern=pattern, level=level))
    return FilteredAlerter(alerter=alerter, alert_filter=af)


def _alert(name: str, level: AlertLevel = AlertLevel.WARNING) -> Alert:
    return Alert(job_name=name, level=level, message="msg")


def test_send_forwards_when_not_suppressed():
    fa = _make_fa(pattern="suppressed_*")
    result = fa.send(_alert("important_job"))
    assert result is True
    assert len(fa.history) == 1


def test_send_suppresses_matching_alert():
    fa = _make_fa(pattern="noisy_*")
    result = fa.send(_alert("noisy_job"))
    assert result is False
    assert len(fa.history) == 0
    assert fa.suppressed_count == 1


def test_suppressed_list_grows():
    fa = _make_fa(pattern="*")
    fa.send(_alert("a"))
    fa.send(_alert("b"))
    assert fa.suppressed_count == 2
    names = [a.job_name for a in fa.suppressed]
    assert "a" in names and "b" in names


def test_suppressed_returns_copy():
    fa = _make_fa(pattern="*")
    fa.send(_alert("x"))
    copy = fa.suppressed
    copy.clear()
    assert fa.suppressed_count == 1  # original unaffected


def test_alert_missed_is_critical_and_forwarded():
    alerter = Alerter()
    fa = FilteredAlerter(alerter=alerter, alert_filter=AlertFilter())
    result = fa.alert_missed("backup", 120)
    assert result is True
    assert alerter.history[0].level == AlertLevel.CRITICAL
    assert "backup" in alerter.history[0].message


def test_alert_delayed_is_warning_and_forwarded():
    alerter = Alerter()
    fa = FilteredAlerter(alerter=alerter, alert_filter=AlertFilter())
    result = fa.alert_delayed("sync", 45)
    assert result is True
    assert alerter.history[0].level == AlertLevel.WARNING


def test_alert_missed_suppressed_by_filter():
    alerter = Alerter()
    af = AlertFilter()
    af.add_rule(FilterRule(job_pattern="backup", level=AlertLevel.CRITICAL))
    fa = FilteredAlerter(alerter=alerter, alert_filter=af)
    result = fa.alert_missed("backup", 60)
    assert result is False
    assert len(alerter.history) == 0
    assert fa.suppressed_count == 1


def test_alert_delayed_suppressed_by_filter():
    """A WARNING-level delayed alert should be suppressed when the filter matches it."""
    alerter = Alerter()
    af = AlertFilter()
    af.add_rule(FilterRule(job_pattern="sync", level=AlertLevel.WARNING))
    fa = FilteredAlerter(alerter=alerter, alert_filter=af)
    result = fa.alert_delayed("sync", 30)
    assert result is False
    assert len(alerter.history) == 0
    assert fa.suppressed_count == 1
