"""Tests for the alerter module."""

from cronwatcher.alerter import Alert, AlertLevel, Alerter


def test_alert_str_contains_job_name():
    alert = Alert(job_name="backup", level=AlertLevel.CRITICAL, message="missed")
    assert "backup" in str(alert)
    assert "CRITICAL" in str(alert).upper()


def test_add_handler_and_send():
    alerter = Alerter()
    received = []
    alerter.add_handler(received.append)

    alerter.send(Alert(job_name="job1", level=AlertLevel.WARNING, message="late"))

    assert len(received) == 1
    assert received[0].job_name == "job1"


def test_alert_missed_sends_critical():
    alerter = Alerter()
    received = []
    alerter.add_handler(received.append)

    alerter.alert_missed("db-backup", overdue_seconds=300.0)

    assert len(received) == 1
    assert received[0].level == AlertLevel.CRITICAL
    assert "300.0" in received[0].message


def test_alert_delayed_sends_warning():
    alerter = Alerter()
    received = []
    alerter.add_handler(received.append)

    alerter.alert_delayed("report", delay_seconds=45.5)

    assert len(received) == 1
    assert received[0].level == AlertLevel.WARNING
    assert "45.5" in received[0].message


def test_history_records_all_alerts():
    alerter = Alerter()
    alerter.alert_missed("job-a", 60.0)
    alerter.alert_delayed("job-b", 10.0)

    assert len(alerter.history) == 2


def test_clear_history():
    alerter = Alerter()
    alerter.alert_missed("job-a", 60.0)
    alerter.clear_history()

    assert alerter.history == []


def test_multiple_handlers_all_called():
    alerter = Alerter()
    bucket_a, bucket_b = [], []
    alerter.add_handler(bucket_a.append)
    alerter.add_handler(bucket_b.append)

    alerter.alert_delayed("sync", 5.0)

    assert len(bucket_a) == 1
    assert len(bucket_b) == 1


def test_no_handlers_does_not_raise():
    alerter = Alerter()
    # should not raise even with no handlers registered
    alerter.alert_missed("lonely-job", 999.0)
    assert len(alerter.history) == 1
