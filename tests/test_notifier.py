"""Tests for EmailNotifier and WebhookNotifier."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import Alert, AlertLevel
from cronwatcher.notifier import EmailNotifier, WebhookNotifier


@pytest.fixture
def warning_alert():
    return Alert(
        job_name="backup",
        level=AlertLevel.WARNING,
        message="Job is 5 minutes late",
        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def critical_alert():
    return Alert(
        job_name="backup",
        level=AlertLevel.CRITICAL,
        message="Job was missed",
        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestEmailNotifier:
    def _make_notifier(self):
        return EmailNotifier(
            host="smtp.example.com",
            port=587,
            sender="alerts@example.com",
            recipients=["ops@example.com"],
            username="user",
            password="secret",
        )

    def test_sends_email_with_correct_subject(self, warning_alert):
        notifier = self._make_notifier()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("cronwatcher.notifier.smtplib.SMTP", return_value=mock_smtp):
            notifier(warning_alert)

        mock_smtp.send_message.assert_called_once()
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert "WARNING" in sent_msg["Subject"]
        assert "backup" in sent_msg["Subject"]

    def test_uses_tls_and_login(self, warning_alert):
        notifier = self._make_notifier()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = lambda s: mock_smtp
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("cronwatcher.notifier.smtplib.SMTP", return_value=mock_smtp):
            notifier(warning_alert)

        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "secret")


class TestWebhookNotifier:
    def test_posts_json_payload(self, critical_alert):
        notifier = WebhookNotifier(url="https://hooks.example.com/alert")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cronwatcher.notifier.urllib.request.urlopen", return_value=mock_resp) as mock_open:
            notifier(critical_alert)

        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["job"] == "backup"
        assert body["level"] == "CRITICAL"

    def test_skips_below_min_level(self, warning_alert):
        notifier = WebhookNotifier(
            url="https://hooks.example.com/alert",
            min_level=AlertLevel.CRITICAL,
        )
        with patch("cronwatcher.notifier.urllib.request.urlopen") as mock_open:
            notifier(warning_alert)
            mock_open.assert_not_called()

    def test_raises_on_http_error(self, critical_alert):
        notifier = WebhookNotifier(url="https://hooks.example.com/alert")
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cronwatcher.notifier.urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="HTTP 500"):
                notifier(critical_alert)
