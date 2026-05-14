"""Tests for anomaly detection module and alerter wrapper."""
from __future__ import annotations

import pytest

from cronwatcher.alerter import Alert, AlertLevel, Alerter
from cronwatcher.anomaly import AnomalyDetector, AnomalyResult
from cronwatcher.anomaly_alerter import AnomalyAlerter


# ---------------------------------------------------------------------------
# AnomalyDetector
# ---------------------------------------------------------------------------

def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window"):
        AnomalyDetector(window=1)


def test_invalid_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        AnomalyDetector(threshold=0.0)


def test_returns_none_for_first_sample():
    det = AnomalyDetector()
    assert det.record("job", 5.0) is None


def test_returns_result_after_two_samples():
    det = AnomalyDetector()
    det.record("job", 5.0)
    result = det.record("job", 6.0)
    assert isinstance(result, AnomalyResult)


def test_no_anomaly_for_consistent_delays():
    det = AnomalyDetector(window=10, threshold=3.0)
    for _ in range(9):
        det.record("job", 2.0)
    result = det.record("job", 2.1)
    assert result is not None
    assert not result.is_anomaly


def test_anomaly_detected_for_spike():
    det = AnomalyDetector(window=20, threshold=3.0)
    for _ in range(19):
        det.record("job", 2.0)
    result = det.record("job", 200.0)
    assert result is not None
    assert result.is_anomaly
    assert result.z_score > 3.0


def test_sample_count_tracks_window():
    det = AnomalyDetector(window=5)
    for i in range(8):
        det.record("job", float(i))
    assert det.sample_count("job") == 5


def test_reset_clears_samples():
    det = AnomalyDetector()
    det.record("job", 1.0)
    det.reset("job")
    assert det.sample_count("job") == 0


def test_anomaly_result_str_contains_job_name():
    r = AnomalyResult("myjob", 100.0, 2.0, 1.0, 98.0, True)
    assert "myjob" in str(r)
    assert "ANOMALY" in str(r)


# ---------------------------------------------------------------------------
# AnomalyAlerter
# ---------------------------------------------------------------------------

def _make_alerter() -> tuple[AnomalyAlerter, list]:
    inner = Alerter()
    det = AnomalyDetector(window=10, threshold=2.0)
    aa = AnomalyAlerter(inner, det)
    fired: list = []
    aa.add_anomaly_handler(fired.append)
    return aa, fired


def test_no_anomaly_handler_not_called_for_normal_delay():
    aa, fired = _make_alerter()
    for _ in range(9):
        aa.record_ok("job", 1.0)
    aa.alert_delayed("job", 1.2)
    assert fired == []


def test_anomaly_handler_called_on_spike():
    aa, fired = _make_alerter()
    for _ in range(9):
        aa.record_ok("job", 1.0)
    aa.alert_delayed("job", 500.0)
    assert len(fired) == 1
    assert fired[0].job_name == "job"


def test_anomalies_list_grows():
    aa, _ = _make_alerter()
    for _ in range(9):
        aa.record_ok("job", 1.0)
    aa.alert_delayed("job", 999.0)
    assert len(aa.anomalies) == 1


def test_alert_missed_delegates_to_inner():
    inner = Alerter()
    received: list = []
    inner.add_handler(received.append)
    aa = AnomalyAlerter(inner)
    aa.alert_missed("job")
    assert len(received) == 1
