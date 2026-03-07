"""BudgetLimit model for Token Miser."""
from datetime import datetime
from typing import List, Optional


class BudgetLimit:
    """Represents a budget limit for a project, team, or organization."""

    _id_counter = 1
    _instances = {}

    def __init__(
        self,
        project=None,
        team_id=None,
        monthly_budget=0.0,
        alert_thresholds=None,
    ):
        """Initialize budget limit.
        
        Args:
            project: The Project instance
            team_id: The team ID
            monthly_budget: Monthly budget in USD
            alert_thresholds: List of percentage thresholds for alerts
        """
        self.id = BudgetLimit._id_counter
        BudgetLimit._id_counter += 1
        self.project = project
        self.team_id = team_id
        self.monthly_budget = monthly_budget
        self.alert_thresholds = alert_thresholds or []
        BudgetLimit._instances[self.id] = self

    @classmethod
    def objects(cls):
        """Return the objects manager."""
        return BudgetLimitManager()

    def __repr__(self):
        return f"<BudgetLimit {self.id}: ${self.monthly_budget}>"


class BudgetLimitManager:
    """Manager for BudgetLimit objects (mimics Django ORM)."""

    def create(self, project=None, team_id=None, monthly_budget=0.0, alert_thresholds=None):
        """Create a new budget limit.
        
        Args:
            project: The Project instance
            team_id: The team ID
            monthly_budget: Monthly budget in USD
            alert_thresholds: List of percentage thresholds for alerts
            
        Returns:
            The created BudgetLimit instance
        """
        return BudgetLimit(
            project=project,
            team_id=team_id,
            monthly_budget=monthly_budget,
            alert_thresholds=alert_thresholds
        )

    def get(self, id):
        """Get budget limit by ID."""
        return BudgetLimit._instances[id]

    def all(self):
        """Get all budget limits."""
        return list(BudgetLimit._instances.values())

    def filter(self, **kwargs):
        """Filter budget limits by attributes."""
        results = []
        for budget in BudgetLimit._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(budget, key) or getattr(budget, key) != value:
                    match = False
                    break
            if match:
                results.append(budget)
        return results


# Module-level objects manager
class Objects:
    """Module-level manager for budget limits."""

    @staticmethod
    def create(project=None, team_id=None, monthly_budget=0.0, alert_thresholds=None):
        """Create a new budget limit."""
        return BudgetLimit(
            project=project,
            team_id=team_id,
            monthly_budget=monthly_budget,
            alert_thresholds=alert_thresholds
        )

    @staticmethod
    def get(id):
        """Get budget limit by ID."""
        return BudgetLimit._instances[id]

    @staticmethod
    def all():
        """Get all budget limits."""
        return list(BudgetLimit._instances.values())

    @staticmethod
    def filter(**kwargs):
        """Filter budget limits by attributes."""
        results = []
        for budget in BudgetLimit._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(budget, key) or getattr(budget, key) != value:
                    match = False
                    break
            if match:
                results.append(budget)
        return results


# Attach objects manager to class
BudgetLimit.objects = Objects
