"""AnomalyAlert model for Token Miser."""
from datetime import datetime


class AnomalyAlert:
    """Represents an alert when token usage spikes unexpectedly."""

    _id_counter = 1
    _instances = {}

    def __init__(
        self,
        team_id,
        project_id,
        project_name,
        baseline_tokens,
        current_tokens,
        spike_magnitude,
        spike_percentage,
        status="active",
        timestamp=None,
        created_at=None,
    ):
        """Initialize anomaly alert.
        
        Args:
            team_id: The team ID
            project_id: The project ID
            project_name: The project name
            baseline_tokens: The baseline tokens
            current_tokens: The current tokens
            spike_magnitude: The spike magnitude (current / baseline)
            spike_percentage: The spike percentage
            status: Alert status ('active' or 'resolved')
            timestamp: Datetime of the alert
            created_at: Datetime when alert was created
        """
        self.id = AnomalyAlert._id_counter
        AnomalyAlert._id_counter += 1
        self.team_id = team_id
        self.project_id = project_id
        self.project_name = project_name
        self.baseline_tokens = baseline_tokens
        self.current_tokens = current_tokens
        self.spike_magnitude = spike_magnitude
        self.spike_percentage = spike_percentage
        self.status = status
        self.timestamp = timestamp or datetime.utcnow()
        self.created_at = created_at or datetime.utcnow()
        AnomalyAlert._instances[self.id] = self

    @classmethod
    def objects(cls):
        """Return the objects manager."""
        return AnomalyAlertManager()

    def save(self):
        """Save the anomaly alert (for compatibility with Django-like usage)."""
        if self.id not in AnomalyAlert._instances:
            AnomalyAlert._instances[self.id] = self
        return self

    def __repr__(self):
        return f"<AnomalyAlert {self.id}: {self.project_name} ({self.spike_magnitude}x spike)>"


class AnomalyAlertManager:
    """Manager for AnomalyAlert objects (mimics Django ORM)."""

    def create(
        self,
        team_id,
        project_id,
        project_name,
        baseline_tokens,
        current_tokens,
        spike_magnitude,
        spike_percentage,
        status="active",
        timestamp=None,
        created_at=None,
    ):
        """Create a new anomaly alert.
        
        Args:
            team_id: The team ID
            project_id: The project ID
            project_name: The project name
            baseline_tokens: The baseline tokens
            current_tokens: The current tokens
            spike_magnitude: The spike magnitude (current / baseline)
            spike_percentage: The spike percentage
            status: Alert status ('active' or 'resolved')
            timestamp: Datetime of the alert
            created_at: Datetime when alert was created
            
        Returns:
            The created AnomalyAlert instance
        """
        return AnomalyAlert(
            team_id=team_id,
            project_id=project_id,
            project_name=project_name,
            baseline_tokens=baseline_tokens,
            current_tokens=current_tokens,
            spike_magnitude=spike_magnitude,
            spike_percentage=spike_percentage,
            status=status,
            timestamp=timestamp,
            created_at=created_at,
        )

    def get(self, id):
        """Get anomaly alert by ID."""
        return AnomalyAlert._instances[id]

    def all(self):
        """Get all anomaly alerts."""
        return list(AnomalyAlert._instances.values())

    def filter(self, **kwargs):
        """Filter anomaly alerts by attributes."""
        results = []
        for alert in AnomalyAlert._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(alert, key) or getattr(alert, key) != value:
                    match = False
                    break
            if match:
                results.append(alert)
        return results


# Module-level objects manager
class Objects:
    """Module-level manager for anomaly alerts."""

    @staticmethod
    def create(
        team_id,
        project_id,
        project_name,
        baseline_tokens,
        current_tokens,
        spike_magnitude,
        spike_percentage,
        status="active",
        timestamp=None,
        created_at=None,
    ):
        """Create a new anomaly alert."""
        return AnomalyAlert(
            team_id=team_id,
            project_id=project_id,
            project_name=project_name,
            baseline_tokens=baseline_tokens,
            current_tokens=current_tokens,
            spike_magnitude=spike_magnitude,
            spike_percentage=spike_percentage,
            status=status,
            timestamp=timestamp,
            created_at=created_at,
        )

    @staticmethod
    def get(id):
        """Get anomaly alert by ID."""
        return AnomalyAlert._instances[id]

    @staticmethod
    def all():
        """Get all anomaly alerts."""
        return list(AnomalyAlert._instances.values())

    @staticmethod
    def filter(**kwargs):
        """Filter anomaly alerts by attributes."""
        results = []
        for alert in AnomalyAlert._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(alert, key) or getattr(alert, key) != value:
                    match = False
                    break
            if match:
                results.append(alert)
        return results


# Attach objects manager to class
AnomalyAlert.objects = Objects
