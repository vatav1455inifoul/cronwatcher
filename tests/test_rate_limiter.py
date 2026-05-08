"""Tests for rate_limiter and rate_limited_alerter."""

from __future__ import annotations

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.rate_limiter import BucketConfig, RateLimiter
from cronwatcher.rate_limited_alerter import RateLimitedAlerter


# ---------------------------------------------------------------------------
# BucketConfig validation
# ---------------------------------------------------------------------------

def test_invalid_capacity_raises():
    with pytest.raises(ValueError, match="capacity"):
        BucketConfig(capacity=0, refill_rate=1.0)


def test_invalid_refill_rate_raises():
    with pytest.raises(ValueError, match="refill_rate"):
        BucketConfig(capacity=5, refill_rate=0.0)


# ---------------------------------------------------------------------------
# RateLimiter token consumption
# ---------------------------------------------------------------------------

def test_allow_up_to_capacity():
    limiter = RateLimiter(BucketConfig(capacity=3, refill_rate=0.001))
    results = [limiter.allow("job") for _ in range(4)]
    assert results[:3] == [True, True, True]
    assert results[3] is False


def test_separate_buckets_per_job():
    limiter = RateLimiter(BucketConfig(capacity=1, refill_rate=0.001))
    assert limiter.allow("job_a") is True
    assert limiter.allow("job_b") is True  # different bucket
    assert limiter.allow("job_a") is False


def test_reset_restores_full_capacity():
    limiter = RateLimiter(BucketConfig(capacity=2, refill_rate=0.001))
    limiter.allow("job")
    limiter.allow("job")
    assert limiter.allow("job") is False
    limiter.reset("job")
    assert limiter.allow("job") is True


def test_available_tokens_decrease_on_consume():
    limiter = RateLimiter(BucketConfig(capacity=5, refill_rate=0.001))
    limiter.allow("job")
    assert limiter.available_tokens("job") < 5.0


# ---------------------------------------------------------------------------
# RateLimitedAlerter
# ---------------------------------------------------------------------------

def _make_rla(capacity: int = 2) -> tuple[RateLimitedAlerter, Alerter]:
    inner = Alerter()
    cfg = BucketConfig(capacity=capacity, refill_rate=0.001)
    rla = RateLimitedAlerter(inner, cfg)
    return rla, inner


def test_alert_forwarded_within_limit():
    rla, inner = _make_rla(capacity=3)
    rla.alert_missed("job1")
    assert len(inner.history) == 1
    assert rla.suppressed_count == 0


def test_alert_suppressed_beyond_limit():
    rla, inner = _make_rla(capacity=1)
    rla.alert_missed("job1")
    rla.alert_missed("job1")  # should be suppressed
    assert len(inner.history) == 1
    assert rla.suppressed_count == 1


def test_delayed_alert_level_is_warning():
    rla, inner = _make_rla(capacity=5)
    rla.alert_delayed("job2", 42.5)
    assert inner.history[-1].level == AlertLevel.WARNING
    assert "42.5" in inner.history[-1].message


def test_reset_allows_more_alerts():
    rla, inner = _make_rla(capacity=1)
    rla.alert_missed("job3")
    rla.alert_missed("job3")  # suppressed
    assert rla.suppressed_count == 1
    rla.reset("job3")
    rla.alert_missed("job3")  # should go through now
    assert len(inner.history) == 2


def test_send_direct_alert():
    rla, inner = _make_rla(capacity=2)
    alert = Alert(job_name="j", level=AlertLevel.CRITICAL, message="oops")
    rla.send(alert)
    assert inner.history[-1].job_name == "j"
