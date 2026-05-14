"""Alerter wrapper that emits an extra systemic alert when correlation fires."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.correlation import AlertCorrelator, CorrelationGroup


SystemicHandler = Callable[[CorrelationGroup], None]


class CorrelatingAlerter:
    """Wraps an Alerter and feeds every alert through an AlertCorrelator.

    When the correlator closes a window that contains multiple distinct jobs
    (i.e. a systemic failure), each registered systemic handler is called.
    """

    def __init__(
        self,
        alerter: Alerter,
        window_seconds: int = 60,
        _now=None,
    ) -> None:
        self._alerter = alerter
        self._correlator = AlertCorrelator(
            window_seconds=window_seconds, _now=_now
        )
        self._systemic_handlers: List[SystemicHandler] = []
        self._systemic_groups: List[CorrelationGroup] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_systemic_handler(self, handler: SystemicHandler) -> None:
        self._systemic_handlers.append(handler)

    def alert_missed(self, job_name: str, seconds_overdue: float) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.CRITICAL,
            message=f"{job_name} missed (overdue {seconds_overdue:.0f}s)",
        )
        self._alerter.send(alert)
        self._observe(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        alert = Alert(
            job_name=job_name,
            level=AlertLevel.WARNING,
            message=f"{job_name} delayed by {delay_seconds:.0f}s",
        )
        self._alerter.send(alert)
        self._observe(alert)

    def send(self, alert: Alert) -> None:
        self._alerter.send(alert)
        self._observe(alert)

    def flush(self) -> Optional[CorrelationGroup]:
        """Manually close the current correlation window."""
        group = self._correlator.flush()
        if group is not None:
            self._handle_group(group)
        return group

    @property
    def systemic_groups(self) -> List[CorrelationGroup]:
        return list(self._systemic_groups)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _observe(self, alert: Alert) -> None:
        group = self._correlator.observe(alert)
        if group is not None:
            self._handle_group(group)

    def _handle_group(self, group: CorrelationGroup) -> None:
        if group.is_systemic:
            self._systemic_groups.append(group)
            for handler in self._systemic_handlers:
                handler(group)
