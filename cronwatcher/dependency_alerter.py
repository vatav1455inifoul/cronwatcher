"""Alerter wrapper that raises alerts for dependency violations."""
from __future__ import annotations

from typing import Callable, List

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.dependency import DependencyGraph, DependencyViolation

ViolationHandler = Callable[[DependencyViolation], None]


class DependencyAlerter:
    """Wraps an *Alerter* and a *DependencyGraph*.

    Call :meth:`check_dependencies` after recording runs to fire alerts
    for any upstream-ordering violations.
    """

    def __init__(self, inner: Alerter, graph: DependencyGraph) -> None:
        self._inner = inner
        self._graph = graph
        self._violation_handlers: List[ViolationHandler] = []
        self._violations: List[DependencyViolation] = []

    def add_violation_handler(self, handler: ViolationHandler) -> None:
        self._violation_handlers.append(handler)

    @property
    def violations(self) -> List[DependencyViolation]:
        return list(self._violations)

    def record_run(self, job: str) -> None:
        self._graph.record_run(job)

    def check_dependencies(self) -> None:
        """Check all jobs with declared dependencies and alert on violations."""
        for violation in self._graph.check_all():
            self._violations.append(violation)
            alert = Alert(
                job_name=violation.job,
                level=AlertLevel.WARNING,
                message=str(violation),
                timestamp=violation.checked_at,
            )
            self._inner.send(alert)
            for handler in self._violation_handlers:
                handler(violation)

    def alert_missed(self, job_name: str) -> None:
        self._inner.alert_missed(job_name)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        self._inner.alert_delayed(job_name, delay_seconds)
