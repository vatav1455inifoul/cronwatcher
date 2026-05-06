"""Load a CronwatcherConfig and populate a PersistentWatcher from it."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from cronwatcher.config import CronwatcherConfig, JobConfig
from cronwatcher.persistent_watcher import PersistentWatcher
from cronwatcher.alerter import Alerter
from cronwatcher.notifier import EmailNotifier, WebhookNotifier


def _build_alerter(cfg: CronwatcherConfig) -> Alerter:
    """Construct an Alerter with handlers derived from config."""
    alerter = Alerter()

    if cfg.email:
        alerter.add_handler(EmailNotifier(
            smtp_host=cfg.email.get("smtp_host", "localhost"),
            smtp_port=int(cfg.email.get("smtp_port", 25)),
            sender=cfg.email.get("sender", "cronwatcher@localhost"),
            recipients=cfg.email.get("recipients", []),
        ))

    if cfg.webhook:
        alerter.add_handler(WebhookNotifier(
            url=cfg.webhook.get("url"),
        ))

    return alerter


def load_watcher(
    config_path: str | Path,
    state_path: Optional[str | Path] = None,
) -> tuple[PersistentWatcher, Alerter]:
    """Parse *config_path*, build a PersistentWatcher and Alerter.

    Returns
    -------
    (watcher, alerter) ready to use.
    """
    cfg = CronwatcherConfig.from_yaml(str(config_path))

    resolved_state = state_path or cfg.state_path or "cronwatcher_state.json"
    watcher = PersistentWatcher(state_path=str(resolved_state))

    for job in cfg.jobs:
        watcher.register(
            name=job.name,
            expression=job.expression,
            tolerance_seconds=job.tolerance_seconds,
        )

    alerter = _build_alerter(cfg)
    return watcher, alerter
