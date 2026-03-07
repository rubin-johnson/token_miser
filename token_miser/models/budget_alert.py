"""BudgetAlert model for Token Miser."""
from datetime import datetime
from typing import Optional


class BudgetAlert:
    """Represents an alert when spending approaches budget limit."""

    _id_counter = 1
    _instances = {}

    def __init__(
        self,
        budget_limit=None,
        current_spend=0.0,
        percentage_used=0,
        alert_threshold=0,
        projected_spend=0.0,
        timestamp=None,
        alert_sent=False,
    ):
        """Initialize budget alert.
        
        Args:
            budget_limit: The BudgetLimit instance
            current_spend: Current spending in USD
            percentage_used: Percentage of budget used
            alert_threshold: Alert threshold that triggered
            projected_spend: Projected spending by end of period
            timestamp: Datetime of the alert
            alert_sent: Whether alert has been sent
        """
        self.id = BudgetAlert._id_counter
        BudgetAlert._id_counter += 1
        self.budget_limit = budget_limit
        self.current_spend = current_spend
        self.percentage_used = percentage_used
        self.alert_threshold = alert_threshold
        self.projected_spend = projected_spend
        self.timestamp = timestamp or datetime.utcnow()
        self.alert_sent = alert_sent
        BudgetAlert._instances[self.id] = self

    @classmethod
    def objects(cls):
        """Return the objects manager."""
        return BudgetAlertManager()

    def __repr__(self):
        return f"<BudgetAlert {self.id}: {self.percentage_used}% of budget>"


class BudgetAlertManager:
    """Manager for BudgetAlert objects (mimics Django ORM)."""

    def create(
        self,
        budget_limit=None,
        current_spend=0.0,
        percentage_used=0,
        alert_threshold=0,
        projected_spend=0.0,
        timestamp=None,
        alert_sent=False,
    ):
        """Create a new budget alert.
        
        Args:
            budget_limit: The BudgetLimit instance
            current_spend: Current spending in USD
            percentage_used: Percentage of budget used
            alert_threshold: Alert threshold that triggered
            projected_spend: Projected spending by end of period
            timestamp: Datetime of the alert
            alert_sent: Whether alert has been sent
            
        Returns:
            The created BudgetAlert instance
        """
        return BudgetAlert(
            budget_limit=budget_limit,
            current_spend=current_spend,
            percentage_used=percentage_used,
            alert_threshold=alert_threshold,
            projected_spend=projected_spend,
            timestamp=timestamp,
            alert_sent=alert_sent,
        )

    def get(self, id):
        """Get budget alert by ID."""
        return BudgetAlert._instances[id]

    def all(self):
        """Get all budget alerts."""
        return list(BudgetAlert._instances.values())

    def filter(self, **kwargs):
        """Filter budget alerts by attributes."""
        results = []
        for alert in BudgetAlert._instances.values():
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
    """Module-level manager for budget alerts."""

    @staticmethod
    def create(
        budget_limit=None,
        current_spend=0.0,
        percentage_used=0,
        alert_threshold=0,
        projected_spend=0.0,
        timestamp=None,
        alert_sent=False,
    ):
        """Create a new budget alert."""
        return BudgetAlert(
            budget_limit=budget_limit,
            current_spend=current_spend,
            percentage_used=percentage_used,
            alert_threshold=alert_threshold,
            projected_spend=projected_spend,
            timestamp=timestamp,
            alert_sent=alert_sent,
        )

    @staticmethod
    def get(id):
        """Get budget alert by ID."""
        return BudgetAlert._instances[id]

    @staticmethod
    def all():
        """Get all budget alerts."""
        return list(BudgetAlert._instances.values())

    @staticmethod
    def filter(**kwargs):
        """Filter budget alerts by attributes."""
        results = []
        for alert in BudgetAlert._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(alert, key) or getattr(alert, key) != value:
                    match = False
                    break
            if match:
                results.append(alert)
        return results


# Attach objects manager to class
BudgetAlert.objects = Objects
