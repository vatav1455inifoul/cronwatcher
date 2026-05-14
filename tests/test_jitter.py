"""Tests for cronwatcher.jitter."""

from datetime import datetime, timezone, timedelta

import pytest

from cronwatcher.jitter import JitterSample, JitterStats, JitterTracker


def _utc(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 6, 1, hour, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# JitterSample
# ---------------------------------------------------------------------------

def test_jitter_seconds_late():
    sample = JitterSample(
        job_name="backup",
        scheduled_at=_utc(10, 0, 0),
        actual_at=_utc(10, 0, 45),
    )
    assert sample.jitter_seconds == pytest.approx(45.0)


def test_jitter_seconds_early():
    sample = JitterSample(
        job_name="backup",
        scheduled_at=_utc(10, 0, 0),
        actual_at=_utc(9, 59, 50),
    )
    assert sample.jitter_seconds == pytest.approx(-10.0)


def test_jitter_sample_str_contains_job_name():
    sample = JitterSample(
        job_name="cleanup",
        scheduled_at=_utc(8),
        actual_at=_utc(8, 0, 5),
    )
    assert "cleanup" in str(sample)
    assert "+5.0s" in str(sample)


# ---------------------------------------------------------------------------
# JitterStats
# ---------------------------------------------------------------------------

def test_stats_mean_none_when_empty():
    stats = JitterStats(job_name="job")
    assert stats.mean is None


def test_stats_max_abs_none_when_empty():
    stats = JitterStats(job_name="job")
    assert stats.max_abs is None


def test_stats_mean_and_max():
    stats = JitterStats(job_name="job")
    stats.record(10.0)
    stats.record(-20.0)
    stats.record(5.0)
    assert stats.mean == pytest.approx(-5.0 / 3, rel=1e-6)
    assert stats.max_abs == pytest.approx(20.0)
    assert stats.count == 3


# ---------------------------------------------------------------------------
# JitterTracker
# ---------------------------------------------------------------------------

def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        JitterTracker(threshold_seconds=0)


def test_record_returns_sample():
    tracker = JitterTracker(threshold_seconds=30.0)
    sample = tracker.record("myjob", _utc(12), _utc(12, 0, 10))
    assert isinstance(sample, JitterSample)
    assert sample.job_name == "myjob"


def test_is_outlier_within_threshold():
    tracker = JitterTracker(threshold_seconds=30.0)
    sample = tracker.record("myjob", _utc(12), _utc(12, 0, 20))
    assert not tracker.is_outlier(sample)


def test_is_outlier_beyond_threshold():
    tracker = JitterTracker(threshold_seconds=30.0)
    sample = tracker.record("myjob", _utc(12), _utc(12, 1, 5))
    assert tracker.is_outlier(sample)


def test_stats_for_unknown_job_returns_none():
    tracker = JitterTracker()
    assert tracker.stats_for("ghost") is None


def test_stats_accumulate_across_multiple_runs():
    tracker = JitterTracker(threshold_seconds=60.0)
    for delta in [5, 10, 15]:
        tracker.record("batch", _utc(6), _utc(6, 0, delta))
    stats = tracker.stats_for("batch")
    assert stats is not None
    assert stats.count == 3
    assert stats.mean == pytest.approx(10.0)


def test_all_stats_returns_all_jobs():
    tracker = JitterTracker()
    tracker.record("job_a", _utc(1), _utc(1, 0, 2))
    tracker.record("job_b", _utc(2), _utc(2, 0, 3))
    all_stats = tracker.all_stats()
    assert "job_a" in all_stats
    assert "job_b" in all_stats
