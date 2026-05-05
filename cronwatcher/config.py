"""Load and validate cronwatcher job configuration from a YAML or dict source."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    tolerance_seconds: int = 60
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Job name must not be empty")
        if not self.schedule or not self.schedule.strip():
            raise ValueError(f"Job '{self.name}' must have a schedule")
        if self.tolerance_seconds < 0:
            raise ValueError(f"Job '{self.name}' tolerance_seconds must be >= 0")


@dataclass
class CronwatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "CronwatcherConfig":
        jobs_data = data.get("jobs", [])
        if not isinstance(jobs_data, list):
            raise ValueError("'jobs' must be a list")
        jobs = []
        for item in jobs_data:
            jobs.append(
                JobConfig(
                    name=item["name"],
                    schedule=item["schedule"],
                    tolerance_seconds=int(item.get("tolerance_seconds", 60)),
                    alert_email=item.get("alert_email"),
                    alert_webhook=item.get("alert_webhook"),
                    tags=list(item.get("tags", [])),
                )
            )
        return cls(jobs=jobs)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CronwatcherConfig":
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)

    def job_names(self) -> List[str]:
        return [j.name for j in self.jobs]
