"""Tests for cronwatcher.filter (FilterRule + AlertFilter)."""
import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.filter import AlertFilter, FilterRule


def _alert(name: str, level: AlertLevel = AlertLevel.WARNING) -> Alert:
    return Alert(job_name=name, level=level, message="test")


# ---------------------------------------------------------------------------
# FilterRule.matches
# ---------------------------------------------------------------------------

def test_rule_matches_exact_name():
    rule = FilterRule(job_pattern="backup")
    assert rule.matches(_alert("backup"))
    assert not rule.matches(_alert("restore"))


def test_rule_glob_matches_prefix():
    rule = FilterRule(job_pattern="backup_*")
    assert rule.matches(_alert("backup_daily"))
    assert rule.matches(_alert("backup_weekly"))
    assert not rule.matches(_alert("restore_daily"))


def test_rule_matches_any_level_when_none():
    rule = FilterRule(job_pattern="*", level=None)
    assert rule.matches(_alert("any_job", AlertLevel.CRITICAL))
    assert rule.matches(_alert("any_job", AlertLevel.WARNING))


def test_rule_filters_by_level():
    rule = FilterRule(job_pattern="*", level=AlertLevel.WARNING)
    assert rule.matches(_alert("x", AlertLevel.WARNING))
    assert not rule.matches(_alert("x", AlertLevel.CRITICAL))


# ---------------------------------------------------------------------------
# AlertFilter
# ---------------------------------------------------------------------------

def test_empty_filter_never_suppresses():
    af = AlertFilter()
    assert af.should_send(_alert("anything"))
    assert not af.should_suppress(_alert("anything"))


def test_add_rule_suppresses_match():
    af = AlertFilter()
    af.add_rule(FilterRule(job_pattern="test_*"))
    assert af.should_suppress(_alert("test_job"))
    assert af.should_send(_alert("prod_job"))


def test_multiple_rules_any_match_suppresses():
    af = AlertFilter()
    af.add_rule(FilterRule(job_pattern="a_*"))
    af.add_rule(FilterRule(job_pattern="b_*"))
    assert af.should_suppress(_alert("a_job"))
    assert af.should_suppress(_alert("b_job"))
    assert af.should_send(_alert("c_job"))


def test_from_dict_no_suppress_key():
    af = AlertFilter.from_dict({})
    assert af.should_send(_alert("anything"))


def test_from_dict_parses_level():
    data = {"suppress": [{"job_pattern": "*", "level": "WARNING"}]}
    af = AlertFilter.from_dict(data)
    assert af.should_suppress(_alert("x", AlertLevel.WARNING))
    assert af.should_send(_alert("x", AlertLevel.CRITICAL))


def test_from_dict_null_level_matches_all():
    data = {"suppress": [{"job_pattern": "noisy_*", "level": None}]}
    af = AlertFilter.from_dict(data)
    assert af.should_suppress(_alert("noisy_job", AlertLevel.CRITICAL))
    assert af.should_send(_alert("important_job", AlertLevel.CRITICAL))
