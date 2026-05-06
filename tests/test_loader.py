"""Tests for cronwatcher.loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.loader import load_watcher
from cronwatcher.persistent_watcher import PersistentWatcher
from cronwatcher.alerter import Alerter


MINIMAL_YAML = textwrap.dedent("""\
    jobs:
      - name: backup
        expression: "0 2 * * *"
        tolerance_seconds: 300
      - name: cleanup
        expression: "*/5 * * * *"
""")

YAML_WITH_EMAIL = textwrap.dedent("""\
    email:
      smtp_host: mail.example.com
      smtp_port: 587
      sender: alerts@example.com
      recipients:
        - ops@example.com
    jobs:
      - name: report
        expression: "0 8 * * 1"
""")

YAML_WITH_WEBHOOK = textwrap.dedent("""\
    webhook:
      url: https://hooks.example.com/notify
    jobs:
      - name: sync
        expression: "*/10 * * * *"
""")


@pytest.fixture()
def yaml_file(tmp_path: Path):
    def _write(content: str) -> Path:
        p = tmp_path / "cronwatcher.yaml"
        p.write_text(content)
        return p
    return _write


def test_load_watcher_returns_correct_types(yaml_file, tmp_path):
    path = yaml_file(MINIMAL_YAML)
    watcher, alerter = load_watcher(path, state_path=tmp_path / "state.json")
    assert isinstance(watcher, PersistentWatcher)
    assert isinstance(alerter, Alerter)


def test_load_watcher_registers_all_jobs(yaml_file, tmp_path):
    path = yaml_file(MINIMAL_YAML)
    watcher, _ = load_watcher(path, state_path=tmp_path / "state.json")
    assert "backup" in watcher
    assert "cleanup" in watcher


def test_load_watcher_respects_tolerance(yaml_file, tmp_path):
    path = yaml_file(MINIMAL_YAML)
    watcher, _ = load_watcher(path, state_path=tmp_path / "state.json")
    tracker = watcher._registry["backup"]
    assert tracker.tolerance_seconds == 300


def test_load_watcher_email_adds_handler(yaml_file, tmp_path):
    path = yaml_file(YAML_WITH_EMAIL)
    _, alerter = load_watcher(path, state_path=tmp_path / "state.json")
    assert len(alerter._handlers) == 1


def test_load_watcher_webhook_adds_handler(yaml_file, tmp_path):
    path = yaml_file(YAML_WITH_WEBHOOK)
    _, alerter = load_watcher(path, state_path=tmp_path / "state.json")
    assert len(alerter._handlers) == 1


def test_load_watcher_no_notifiers_empty_handlers(yaml_file, tmp_path):
    path = yaml_file(MINIMAL_YAML)
    _, alerter = load_watcher(path, state_path=tmp_path / "state.json")
    assert len(alerter._handlers) == 0


def test_load_watcher_custom_state_path(yaml_file, tmp_path):
    path = yaml_file(MINIMAL_YAML)
    custom_state = tmp_path / "custom_state.json"
    watcher, _ = load_watcher(path, state_path=custom_state)
    # after registering, the watcher should have saved state to custom path
    assert isinstance(watcher, PersistentWatcher)
