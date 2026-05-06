"""Watcher variant that persists job run history across restarts."""

from datetime import datetime
from typing import Optional

from cronwatcher.alerter import Alerter
from cronwatcher.persistence import StateStore
from cronwatcher.registry import JobRegistry
from cronwatcher.tracker import JobStatus


class PersistentWatcher:
    """Wraps JobRegistry with automatic state persistence."""

    def __init__(
        self,
        registry: JobRegistry,
        store: StateStore,
        alerter: Optional[Alerter] = None,
    ) -> None:
        self._registry = registry
        self._store = store
        self._alerter = alerter
        self._restore()

    def _restore(self) -> None:
        """Replay persisted last-run times into the registry."""
        for job_name in self._store.all_jobs():
            if job_name not in self._registry:
                continue
            last_run = self._store.get_last_run(job_name)
            if last_run is not None:
                self._registry.record_run(job_name, last_run)

    def record_run(
        self, job_name: str, ts: Optional[datetime] = None
    ) -> JobStatus:
        if ts is None:
            ts = datetime.utcnow()
        status = self._registry.record_run(job_name, ts)
        self._store.set_last_run(job_name, ts)
        self._store.save()
        return status

    def check_all(self) -> None:
        results = self._registry.check()
        if self._alerter is None:
            return
        for job_name, status in results.items():
            if status.is_missed:
                self._alerter.alert_missed(job_name)
            elif status.is_delayed:
                self._alerter.alert_delayed(job_name, status.delay_seconds or 0)

    @property
    def registry(self) -> JobRegistry:
        return self._registry

    @property
    def store(self) -> StateStore:
        return self._store
