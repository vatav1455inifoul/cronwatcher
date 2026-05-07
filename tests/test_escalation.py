"""Tests for escalation policy and escalating alerter."""
from __future__ import annotations

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.escalation import EscalationPolicy, EscalationTracker
from cronwatcher.escalating_alerter import EscalatingAlerter


# ---------------------------------------------------------------------------
# EscalationPolicy
# ---------------------------------------------------------------------------

def test_invalid_warn_after_raises():
    with pytest.raises(ValueError):
        EscalationPolicy(warn_after=0)


def test_invalid_critical_before_warn_raises():
    with pytest.raises(ValueError):
        EscalationPolicy(warn_after=3, critical_after=2)


def test_level_below_warn_is_info():
    policy = EscalationPolicy(warn_after=2, critical_after=4)
    assert policy.level_for(1) == AlertLevel.INFO


def test_level_at_warn_threshold_is_warning():
    policy = EscalationPolicy(warn_after=2, critical_after=4)
    assert policy.level_for(2) == AlertLevel.WARNING


def test_level_at_critical_threshold_is_critical():
    policy = EscalationPolicy(warn_after=2, critical_after=4)
    assert policy.level_for(4) == AlertLevel.CRITICAL
    assert policy.level_for(10) == AlertLevel.CRITICAL


# ---------------------------------------------------------------------------
# EscalationTracker
# ---------------------------------------------------------------------------

def test_record_miss_increments_counter():
    tracker = EscalationTracker()
    tracker.record_miss("job_a")
    assert tracker.consecutive_misses("job_a") == 1


def test_record_ok_resets_counter():
    tracker = EscalationTracker()
    tracker.record_miss("job_a")
    tracker.record_miss("job_a")
    tracker.record_ok("job_a")
    assert tracker.consecutive_misses("job_a") == 0


def test_escalate_alert_returns_new_alert_with_escalated_level():
    policy = EscalationPolicy(warn_after=1, critical_after=3)
    tracker = EscalationTracker(policy)
    alert = Alert(job_name="job_x", level=AlertLevel.CRITICAL, message="missed")
    result = tracker.escalate_alert(alert)
    assert result.level == AlertLevel.WARNING  # 1st miss => warn_after=1
    assert result.job_name == "job_x"


# ---------------------------------------------------------------------------
# EscalatingAlerter
# ---------------------------------------------------------------------------

def _make_ea(warn_after=1, critical_after=3):
    inner = Alerter()
    sent = []
    inner.add_handler(sent.append)
    policy = EscalationPolicy(warn_after=warn_after, critical_after=critical_after)
    ea = EscalatingAlerter(inner, policy)
    return ea, sent


def test_first_miss_sends_warning():
    ea, sent = _make_ea(warn_after=1, critical_after=3)
    ea.alert_missed("job_a")
    assert len(sent) == 1
    assert sent[0].level == AlertLevel.WARNING


def test_third_miss_escalates_to_critical():
    ea, sent = _make_ea(warn_after=1, critical_after=3)
    for _ in range(3):
        ea.alert_missed("job_a")
    assert sent[-1].level == AlertLevel.CRITICAL


def test_ok_resets_escalation():
    ea, sent = _make_ea(warn_after=1, critical_after=3)
    ea.alert_missed("job_a")
    ea.alert_missed("job_a")
    ea.record_ok("job_a")
    assert ea.consecutive_misses("job_a") == 0


def test_delayed_does_not_escalate():
    ea, sent = _make_ea()
    ea.alert_delayed("job_b", "ran late")
    assert sent[0].level == AlertLevel.WARNING
    assert ea.consecutive_misses("job_b") == 0


def test_escalated_property_tracks_all_miss_alerts():
    ea, _ = _make_ea()
    ea.alert_missed("job_c")
    ea.alert_missed("job_c")
    assert len(ea.escalated) == 2
