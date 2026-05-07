"""Tests for cronwatcher.daemon_factory.build_daemon."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.daemon import Daemon
from cronwatcher.daemon_factory import build_daemon


def _fake_watcher():
    return MagicMock()


def test_build_daemon_returns_daemon_instance():
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        daemon = build_daemon("fake_config.yaml")
    assert isinstance(daemon, Daemon)


def test_build_daemon_uses_load_watcher_with_path():
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher) as mock_load:
        build_daemon("my_config.yaml")
    mock_load.assert_called_once_with("my_config.yaml")


def test_build_daemon_default_interval():
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        daemon = build_daemon("cfg.yaml")
    assert daemon.interval == 60


def test_build_daemon_custom_interval():
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        daemon = build_daemon("cfg.yaml", interval=120)
    assert daemon.interval == 120


def test_build_daemon_watcher_is_set():
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        daemon = build_daemon("cfg.yaml")
    assert daemon.watcher is fake_watcher


def test_build_daemon_invalid_interval_raises():
    """build_daemon should raise ValueError when interval is not positive."""
    fake_watcher = _fake_watcher()
    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        with pytest.raises(ValueError, match="interval"):
            build_daemon("cfg.yaml", interval=0)

    with patch("cronwatcher.daemon_factory.load_watcher", return_value=fake_watcher):
        with pytest.raises(ValueError, match="interval"):
            build_daemon("cfg.yaml", interval=-5)
