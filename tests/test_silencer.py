"""Tests for Silencer and SilenceWindow."""

from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.silencer import Silencer, SilenceWindow


def _utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def _window(
    job_name=None,
    offset_start=-60,
    offset_end=60,
    reason="maintenance",
) -> SilenceWindow:
    return SilenceWindow(
        start=_utc(seconds=offset_start),
        end=_utc(seconds=offset_end),
        job_name=job_name,
        reason=reason,
    )


def test_invalid_window_raises():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        SilenceWindow(start=now, end=now - timedelta(seconds=1))


def test_window_is_active_within_range():
    w = _window()
    assert w.is_active() is True


def test_window_not_active_before_start():
    w = _window(offset_start=10, offset_end=120)
    assert w.is_active() is False


def test_window_not_active_after_end():
    w = _window(offset_start=-120, offset_end=-10)
    assert w.is_active() is False


def test_covers_specific_job():
    w = _window(job_name="backup")
    assert w.covers("backup") is True
    assert w.covers("deploy") is False


def test_covers_all_jobs_when_no_name():
    w = _window(job_name=None)
    assert w.covers("anything") is True


def test_silencer_is_silenced():
    s = Silencer()
    s.add(_window(job_name="backup"))
    assert s.is_silenced("backup") is True
    assert s.is_silenced("other") is False


def test_silencer_global_window_silences_all():
    s = Silencer()
    s.add(_window(job_name=None))
    assert s.is_silenced("anything") is True


def test_silencer_no_windows_not_silenced():
    s = Silencer()
    assert s.is_silenced("job") is False


def test_purge_expired_removes_old_windows():
    s = Silencer()
    s.add(_window(offset_start=-120, offset_end=-10))  # expired
    s.add(_window(offset_start=-10, offset_end=120))   # active
    removed = s.purge_expired()
    assert removed == 1
    assert len(s) == 1


def test_active_windows_returns_only_active():
    s = Silencer()
    s.add(_window(offset_start=-120, offset_end=-10))  # expired
    s.add(_window(offset_start=-10, offset_end=120))   # active
    assert len(s.active_windows()) == 1


def test_str_representation():
    w = _window(job_name="deploy", reason="planned")
    text = str(w)
    assert "deploy" in text
    assert "planned" in text
