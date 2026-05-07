"""Alert filtering — suppress alerts based on job name patterns or alert levels."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.alerter import Alert, AlertLevel


@dataclass
class FilterRule:
    """A single filter rule that can match alerts by job name glob and/or level."""

    job_pattern: str = "*"          # fnmatch-style glob, e.g. "backup_*"
    level: Optional[AlertLevel] = None  # None means match any level

    def matches(self, alert: Alert) -> bool:
        name_match = fnmatch.fnmatch(alert.job_name, self.job_pattern)
        level_match = self.level is None or alert.level == self.level
        return name_match and level_match


@dataclass
class AlertFilter:
    """Holds a list of suppression rules.  An alert is suppressed when ANY rule matches."""

    rules: List[FilterRule] = field(default_factory=list)

    def add_rule(self, rule: FilterRule) -> None:
        self.rules.append(rule)

    def should_suppress(self, alert: Alert) -> bool:
        """Return True if the alert should be dropped."""
        return any(r.matches(alert) for r in self.rules)

    def should_send(self, alert: Alert) -> bool:
        return not self.should_suppress(alert)

    # convenience factory helpers ------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "AlertFilter": 
        """Build from a plain dict, e.g. loaded from YAML config.

        Expected shape::

            suppress:
              - job_pattern: "test_*"
                level: WARNING
              - job_pattern: "*"
                level: null
        """
        instance = cls()
        for entry in data.get("suppress", []):
            level_str = entry.get("level")
            level = AlertLevel[level_str] if level_str else None
            instance.add_rule(
                FilterRule(
                    job_pattern=entry.get("job_pattern", "*"),
                    level=level,
                )
            )
        return instance
