"""Email and webhook notification handlers for the Alerter."""

import json
import smtplib
import urllib.request
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Optional

from cronwatcher.alerter import Alert, AlertLevel


@dataclass
class EmailNotifier:
    """Sends alert notifications via SMTP email."""

    host: str
    port: int
    sender: str
    recipients: list
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True

    def __call__(self, alert: Alert) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[cronwatcher] {alert.level.name}: {alert.job_name}"
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(str(alert))

        with smtplib.SMTP(self.host, self.port) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)


@dataclass
class WebhookNotifier:
    """Sends alert notifications as JSON POST to a webhook URL."""

    url: str
    headers: dict = field(default_factory=lambda: {"Content-Type": "application/json"})
    min_level: AlertLevel = AlertLevel.WARNING

    def __call__(self, alert: Alert) -> None:
        if alert.level.value < self.min_level.value:
            return

        payload = {
            "job": alert.job_name,
            "level": alert.level.name,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(self.url, data=data, headers=self.headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Webhook returned HTTP {resp.status}")
