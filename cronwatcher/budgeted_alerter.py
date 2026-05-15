"""Alerter wrapper that enforces an alert budget."""
from __future__ import annotations

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.budget import AlertBudget, BudgetConfig


class BudgetedAlerter:
    """Wraps an :class:`Alerter` and suppresses alerts once the budget
    for the rolling window is exhausted.

    Parameters
    ----------
    inner:
        The real alerter to delegate to.
    config:
        Budget configuration (max alerts / window).
    """

    def __init__(self, inner: Alerter, config: BudgetConfig, **budget_kwargs) -> None:
        self._inner = inner
        self._budget = AlertBudget(config, **budget_kwargs)
        self._suppressed: list[Alert] = []

    # ------------------------------------------------------------------
    def _send(self, alert: Alert) -> None:
        if self._budget.should_allow():
            self._inner.send(alert)
            self._budget.record()
        else:
            self._suppressed.append(alert)

    def send(self, alert: Alert) -> None:
        self._send(alert)

    def alert_missed(self, job_name: str) -> None:
        alert = Alert(job_name=job_name, level=AlertLevel.CRITICAL, message="Job missed")
        self._send(alert)

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        msg = f"Job delayed by {delay_seconds:.1f}s"
        alert = Alert(job_name=job_name, level=AlertLevel.WARNING, message=msg)
        self._send(alert)

    # ------------------------------------------------------------------
    @property
    def suppressed(self) -> list[Alert]:
        """Alerts that were dropped due to budget exhaustion."""
        return list(self._suppressed)

    @property
    def budget(self) -> AlertBudget:
        return self._budget
