"""Tests for tag_filter and tag_filtered_alerter."""
from __future__ import annotations

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.tag_filter import TagFilter, TagRule
from cronwatcher.tag_filtered_alerter import TagFilteredAlerter


# ---------------------------------------------------------------------------
# TagRule
# ---------------------------------------------------------------------------

def _alert(job: str, level: AlertLevel = AlertLevel.CRITICAL) -> Alert:
    return Alert(job_name=job, level=level, message="test")


def test_invalid_tag_raises():
    with pytest.raises(ValueError):
        TagRule(tag="")


def test_invalid_tag_whitespace_raises():
    with pytest.raises(ValueError):
        TagRule(tag="   ")


def test_rule_matches_exact_tag():
    rule = TagRule(tag="env:prod")
    assert rule.matches(_alert("job"), {"env:prod", "team:ops"})


def test_rule_no_match_when_tag_absent():
    rule = TagRule(tag="env:prod")
    assert not rule.matches(_alert("job"), {"env:staging"})


def test_rule_glob_matches():
    rule = TagRule(tag="env:*")
    assert rule.matches(_alert("job"), {"env:staging"})


def test_rule_level_filter_matches():
    rule = TagRule(tag="env:prod", level=AlertLevel.WARNING)
    assert rule.matches(_alert("job", AlertLevel.WARNING), {"env:prod"})


def test_rule_level_filter_no_match_wrong_level():
    rule = TagRule(tag="env:prod", level=AlertLevel.WARNING)
    assert not rule.matches(_alert("job", AlertLevel.CRITICAL), {"env:prod"})


# ---------------------------------------------------------------------------
# TagFilter
# ---------------------------------------------------------------------------

def test_no_rules_never_suppresses():
    tf = TagFilter()
    tf.set_tags("job", {"env:prod"})
    assert not tf.should_suppress(_alert("job"))


def test_suppress_when_rule_matches():
    tf = TagFilter()
    tf.set_tags("job", {"env:staging"})
    tf.add_rule(TagRule(tag="env:staging"))
    assert tf.should_suppress(_alert("job"))


def test_no_suppress_when_tags_not_set():
    tf = TagFilter()
    tf.add_rule(TagRule(tag="env:staging"))
    assert not tf.should_suppress(_alert("job"))


def test_get_tags_returns_empty_for_unknown():
    tf = TagFilter()
    assert tf.get_tags("unknown") == set()


# ---------------------------------------------------------------------------
# TagFilteredAlerter
# ---------------------------------------------------------------------------

def _make_tfa():
    inner = Alerter()
    inner.add_handler(lambda a: None)
    tfa = TagFilteredAlerter(inner)
    return tfa, inner


def test_alert_missed_forwarded_when_no_rules():
    tfa, inner = _make_tfa()
    tfa.alert_missed("job")
    assert tfa.suppressed_count == 0


def test_alert_missed_suppressed_by_tag():
    tfa, _ = _make_tfa()
    tfa.set_tags("job", {"env:dev"})
    tfa.add_rule(TagRule(tag="env:dev"))
    tfa.alert_missed("job")
    assert tfa.suppressed_count == 1


def test_alert_delayed_suppressed_by_tag_and_level():
    tfa, _ = _make_tfa()
    tfa.set_tags("slow-job", {"team:data"})
    tfa.add_rule(TagRule(tag="team:data", level=AlertLevel.WARNING))
    tfa.alert_delayed("slow-job", 45.0)
    assert tfa.suppressed_count == 1


def test_suppressed_list_contains_alert():
    tfa, _ = _make_tfa()
    tfa.set_tags("job", {"env:dev"})
    tfa.add_rule(TagRule(tag="env:dev"))
    tfa.alert_missed("job")
    assert tfa.suppressed[0].job_name == "job"


def test_non_matching_job_not_suppressed():
    tfa, _ = _make_tfa()
    tfa.set_tags("other-job", {"env:dev"})
    tfa.add_rule(TagRule(tag="env:dev"))
    tfa.alert_missed("prod-job")  # no tags registered
    assert tfa.suppressed_count == 0
