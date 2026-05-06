"""Convenience factory that wires a Daemon from a YAML config file."""

from __future__ import annotations

from cronwatcher.daemon import Daemon
from cronwatcher.loader import load_watcher


_DEFAULT_INTERVAL = 60  # seconds


def build_daemon(config_path: str, interval: int = _DEFAULT_INTERVAL) -> Daemon:
    """Load config, build a PersistentWatcher, and wrap it in a Daemon.

    Args:
        config_path: Path to the YAML configuration file.
        interval:    How often (in seconds) the daemon calls check_all.

    Returns:
        A ready-to-start :class:`Daemon` instance.
    """
    watcher = load_watcher(config_path)
    return Daemon(watcher=watcher, interval=interval)
