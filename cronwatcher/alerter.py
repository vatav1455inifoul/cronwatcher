"""Alert system for missed or delayed cron jobs."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional


class AlertLevel(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    job_name: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.timestamp.isoformat()} - {self.job_name}: {self.message}"


AlertHandler = Callable[[Alert], None]


class Alerter:
    """Dispatches alerts to registered handlers."""

    def __init__(self) -> None:
        self._handlers: List[AlertHandler] = []
        self._history: List[Alert] = []

    def add_handler(self, handler: AlertHandler) -> None:
        """Register a callable that receives Alert objects."""
        self._handlers.append(handler)

    def send(self, alert: Alert) -> None:
        """Dispatch an alert to all registered handlers."""
        self._history.append(alert)
        for handler in self._handlers:
            handler(alert)

    def alert_missed(self, job_name: str, overdue_seconds: float) -> None:
        """Send a CRITICAL alert for a missed job."""
        msg = f"Job missed — overdue by {overdue_seconds:.1f}s"
        self.send(Alert(job_name=job_name, level=AlertLevel.CRITICAL, message=msg))

    def alert_delayed(self, job_name: str, delay_seconds: float) -> None:
        """Send a WARNING alert for a delayed job."""
        msg = f"Job ran late by {delay_seconds:.1f}s"
        self.send(Alert(job_name=job_name, level=AlertLevel.WARNING, message=msg))

    @property
    def history(self) -> List[Alert]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
