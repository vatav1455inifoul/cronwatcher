"""Alerter wrapper that fires on anomalous job delays."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.anomaly import AnomalyDetector, AnomalyResult

AnomalyHandler = Callable[[AnomalyResult], None]


class AnomalyAlerter:
    """Wraps an Alerter and fires extra handlers when a z-score anomaly is detected."""

    def __init__(
        self,
        inner: Alerter,
        detector: Optional[AnomalyDetector] = None,
    ) -> None:
        self._inner = inner
        self._detector = detector or AnomalyDetector()
        self._anomaly_handlers: List[AnomalyHandler] = []
        self._anomalies: List[AnomalyResult] = []

    def add_anomaly_handler(self, handler: AnomalyHandler) -> None:
        self._anomaly_handlers.append(handler)

    @property
    def anomalies(self) -> List[AnomalyResult]:
        return list(self._anomalies)

    def alert_missed(self, job_name: str) -> None:
        self._inner.alert_missed(job_name)

    def alert_delayed(self, job_name: str, seconds: float) -> None:
        self._inner.alert_delayed(job_name, seconds)
        result = self._detector.record(job_name, seconds)
        if result is not None and result.is_anomaly:
            self._anomalies.append(result)
            for handler in self._anomaly_handlers:
                handler(result)

    def record_ok(self, job_name: str, delay: float = 0.0) -> None:
        """Record an on-time run so the detector keeps its rolling window fresh."""
        self._detector.record(job_name, delay)
