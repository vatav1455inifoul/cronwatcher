"""Tag-based alert filtering: suppress or route alerts by job tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional, Set

from cronwatcher.alerter import Alert, AlertLevel


@dataclass
class TagRule:
    """A rule that matches alerts whose job carries a specific tag."""

    tag: str
    level: Optional[AlertLevel] = None  # None means any level

    def __post_init__(self) -> None:
        if not self.tag or not self.tag.strip():
            raise ValueError("tag must be a non-empty string")

    def matches(self, alert: Alert, job_tags: Set[str]) -> bool:
        tag_match = any(fnmatch(t, self.tag) for t in job_tags)
        if not tag_match:
            return False
        if self.level is None:
            return True
        return alert.level == self.level


class TagFilter:
    """Decides whether an alert should be suppressed based on job tags.

    Usage::

        tf = TagFilter()
        tf.set_tags("backup", {"team:storage", "env:prod"})
        tf.add_rule(TagRule(tag="env:prod", level=AlertLevel.WARNING))
        tf.should_suppress(alert)  # True if alert.job_name == "backup" & WARNING
    """

    def __init__(self) -> None:
        self._rules: List[TagRule] = []
        self._job_tags: Dict[str, Set[str]] = {}

    def set_tags(self, job_name: str, tags: Set[str]) -> None:
        """Associate a set of tags with a job name."""
        self._job_tags[job_name] = set(tags)

    def get_tags(self, job_name: str) -> Set[str]:
        return self._job_tags.get(job_name, set())

    def add_rule(self, rule: TagRule) -> None:
        self._rules.append(rule)

    def should_suppress(self, alert: Alert) -> bool:
        """Return True if any rule matches the alert's job tags."""
        if not self._rules:
            return False
        tags = self.get_tags(alert.job_name)
        return any(r.matches(alert, tags) for r in self._rules)

    @property
    def rules(self) -> List[TagRule]:
        return list(self._rules)
