"""Alerter wrapper that suppresses alerts using TagFilter."""
from __future__ import annotations

from typing import List

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.tag_filter import TagFilter, TagRule


class TagFilteredAlerter:
    """Wraps an Alerter and skips alerts that match tag-based suppression rules.

    Example::

        inner = Alerter()
        tfa = TagFilteredAlerter(inner)
        tfa.set_tags("nightly-backup", {"env:staging"})
        tfa.add_rule(TagRule(tag="env:staging"))
        tfa.alert_missed("nightly-backup")  # suppressed
    """

    def __init__(self, inner: Alerter, tag_filter: TagFilter | None = None) -> None:
        self._inner = inner
        self._filter = tag_filter if tag_filter is not None else TagFilter()
        self._suppressed: List[Alert] = []

    # -- delegation helpers --------------------------------------------------

    def set_tags(self, job_name: str, tags: set) -> None:
        self._filter.set_tags(job_name, tags)

    def add_rule(self, rule: TagRule) -> None:
        self._filter.add_rule(rule)

    # -- alerting interface --------------------------------------------------

    def send(self, alert: Alert) -> None:
        if self._filter.should_suppress(alert):
            self._suppressed.append(alert)
            return
        self._inner.send(alert)

    def alert_missed(self, job_name: str) -> None:
        alert = Alert(job_name=job_name, level=AlertLevel.CRITICAL, message="Job missed")
        self.send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        msg = f"Job delayed by {delay_seconds:.1f}s"
        alert = Alert(job_name=job_name, level=AlertLevel.WARNING, message=msg)
        self.send(alert)

    # -- introspection -------------------------------------------------------

    @property
    def suppressed(self) -> List[Alert]:
        return list(self._suppressed)

    @property
    def suppressed_count(self) -> int:
        return len(self._suppressed)
