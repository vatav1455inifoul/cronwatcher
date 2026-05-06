"""Configuration dataclasses and YAML loader for cronwatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    expression: str
    tolerance_seconds: int = 60
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Job name must not be empty.")
        if not self.expression:
            raise ValueError("Cron expression must not be empty.")
        if self.tolerance_seconds < 0:
            raise ValueError("tolerance_seconds must be >= 0.")


@dataclass
class CronwatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    state_path: Optional[str] = None
    email: Optional[Dict[str, Any]] = None
    webhook: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CronwatcherConfig":
        raw_jobs = data.get("jobs", [])
        jobs = [
            JobConfig(
                name=j["name"],
                expression=j["expression"],
                tolerance_seconds=int(j.get("tolerance_seconds", 60)),
                description=j.get("description"),
                tags=j.get("tags", []),
            )
            for j in raw_jobs
        ]
        return cls(
            jobs=jobs,
            state_path=data.get("state_path"),
            email=data.get("email"),
            webhook=data.get("webhook"),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "CronwatcherConfig":
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)
