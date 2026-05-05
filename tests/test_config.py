"""Tests for cronwatcher.config."""

import pytest
import yaml
from pathlib import Path

from cronwatcher.config import CronwatcherConfig, JobConfig


MINIMAL_DICT = {
    "jobs": [
        {"name": "backup", "schedule": "0 2 * * *"},
        {"name": "report", "schedule": "*/5 * * * *", "tolerance_seconds": 30},
    ]
}


def test_from_dict_creates_jobs():
    cfg = CronwatcherConfig.from_dict(MINIMAL_DICT)
    assert len(cfg.jobs) == 2
    assert cfg.jobs[0].name == "backup"
    assert cfg.jobs[1].name == "report"


def test_default_tolerance():
    cfg = CronwatcherConfig.from_dict(MINIMAL_DICT)
    assert cfg.jobs[0].tolerance_seconds == 60


def test_custom_tolerance():
    cfg = CronwatcherConfig.from_dict(MINIMAL_DICT)
    assert cfg.jobs[1].tolerance_seconds == 30


def test_job_names():
    cfg = CronwatcherConfig.from_dict(MINIMAL_DICT)
    assert cfg.job_names() == ["backup", "report"]


def test_optional_fields_default_none():
    cfg = CronwatcherConfig.from_dict(MINIMAL_DICT)
    assert cfg.jobs[0].alert_email is None
    assert cfg.jobs[0].alert_webhook is None
    assert cfg.jobs[0].tags == []


def test_optional_fields_populated():
    data = {
        "jobs": [
            {
                "name": "sync",
                "schedule": "@hourly",
                "alert_email": "ops@example.com",
                "alert_webhook": "https://hooks.example.com/alert",
                "tags": ["prod", "critical"],
            }
        ]
    }
    cfg = CronwatcherConfig.from_dict(data)
    job = cfg.jobs[0]
    assert job.alert_email == "ops@example.com"
    assert job.alert_webhook == "https://hooks.example.com/alert"
    assert job.tags == ["prod", "critical"]


def test_empty_jobs_list():
    cfg = CronwatcherConfig.from_dict({"jobs": []})
    assert cfg.jobs == []


def test_missing_jobs_key():
    cfg = CronwatcherConfig.from_dict({})
    assert cfg.jobs == []


def test_invalid_jobs_type_raises():
    with pytest.raises(ValueError, match="'jobs' must be a list"):
        CronwatcherConfig.from_dict({"jobs": "not-a-list"})


def test_empty_name_raises():
    with pytest.raises(ValueError, match="name must not be empty"):
        JobConfig(name="", schedule="* * * * *")


def test_negative_tolerance_raises():
    with pytest.raises(ValueError, match="tolerance_seconds"):
        JobConfig(name="job", schedule="* * * * *", tolerance_seconds=-1)


def test_from_yaml(tmp_path: Path):
    config_file = tmp_path / "cronwatcher.yml"
    data = {"jobs": [{"name": "cleanup", "schedule": "0 3 * * 0"}]}
    config_file.write_text(yaml.dump(data))
    cfg = CronwatcherConfig.from_yaml(config_file)
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0].name == "cleanup"
