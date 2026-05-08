"""Token-bucket rate limiter for controlling alert notification frequency."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BucketConfig:
    """Configuration for a single token bucket."""
    capacity: int
    refill_rate: float  # tokens per second

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")


@dataclass
class _Bucket:
    config: BucketConfig
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.config.capacity)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.config.capacity,
            self.tokens + elapsed * self.config.refill_rate,
        )
        self.last_refill = now

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def available(self) -> float:
        self._refill()
        return self.tokens


class RateLimiter:
    """Per-job token-bucket rate limiter."""

    def __init__(self, default_config: BucketConfig) -> None:
        self._default = default_config
        self._buckets: Dict[str, _Bucket] = {}

    def _get_bucket(self, job_name: str) -> _Bucket:
        if job_name not in self._buckets:
            self._buckets[job_name] = _Bucket(self._default)
        return self._buckets[job_name]

    def allow(self, job_name: str) -> bool:
        """Return True if the alert for *job_name* should be allowed through."""
        return self._get_bucket(job_name).consume()

    def available_tokens(self, job_name: str) -> float:
        return self._get_bucket(job_name).available

    def reset(self, job_name: str) -> None:
        """Refill the bucket for *job_name* to full capacity."""
        self._buckets.pop(job_name, None)
