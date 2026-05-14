"""Alerter wrapper that fires an extra handler when a worsening delay trend is detected."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.trend import TrendAnalyzer, TrendResult


TrendHandler = Callable[[TrendResult], None]


class TrendAlerter:
    """Wraps an Alerter and records delay samples for trend detection.

    When a worsening trend is detected a registered trend handler is called.
    Normal missed/delayed alerts are always forwarded to the inner alerter.
    """

    def __init__(self, inner: Alerter, analyzer: Optional[TrendAnalyzer] = None,
                 min_samples: int = 3) -> None:
        self._inner = inner
        self._analyzer = analyzer or TrendAnalyzer(min_samples=min_samples)
        self._trend_handlers: List[TrendHandler] = []

    def add_trend_handler(self, handler: TrendHandler) -> None:
        self._trend_handlers.append(handler)

    # ------------------------------------------------------------------
    def alert_missed(self, job_name: str, now: Optional[datetime] = None) -> None:
        self._inner.alert_missed(job_name)

    def alert_delayed(self, job_name: str, delay_seconds: float,
                      now: Optional[datetime] = None) -> None:
        self._inner.alert_delayed(job_name, delay_seconds)
        self._analyzer.record(job_name, delay_seconds, now=now)
        self._check_trend(job_name)

    def record_ok(self, job_name: str, now: Optional[datetime] = None) -> None:
        """Record a zero-delay run so the trend can recover."""
        self._analyzer.record(job_name, 0.0, now=now)
        self._check_trend(job_name)

    # ------------------------------------------------------------------
    def _check_trend(self, job_name: str) -> None:
        result = self._analyzer.analyze(job_name)
        if result is not None and result.is_worsening:
            for handler in self._trend_handlers:
                handler(result)

    @property
    def analyzer(self) -> TrendAnalyzer:
        return self._analyzer
