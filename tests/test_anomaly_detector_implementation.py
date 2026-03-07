"""Tests for anomaly detector implementation."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project, AnomalyAlert
from token_miser.services.anomaly_detector import AnomalyDetector


def test_anomaly_detector_initialization(db):
    """Test that detector initializes correctly."""
    detector = AnomalyDetector(team_id=1, sensitivity=2.0)
    assert detector.team_id == 1
    assert detector.sensitivity == 2.0


def test_anomaly_detector_default_sensitivity(db):
    """Test that default sensitivity is 1.5."""
    detector = AnomalyDetector(team_id=1)
    assert detector.sensitivity == 1.5


def test_detect_anomalies_returns_list(db):
    """Test that detect_anomalies returns a list."""
    detector = AnomalyDetector(team_id=1)
    result = detector.detect_anomalies()
    assert isinstance(result, list)


def test_anomaly_alert_model_creation(db):
    """Test that AnomalyAlert model can be created."""
    alert = AnomalyAlert(
        team_id=1,
        project_id=1,
        project_name="TestProject",
        baseline_tokens=100,
        current_tokens=500,
        spike_magnitude=5.0,
        spike_percentage=400,
        status="active"
    )
    alert.save()
    assert AnomalyAlert.objects.filter(id=alert.id)
    # Verify the alert exists in instances
    assert alert.id in AnomalyAlert._instances
