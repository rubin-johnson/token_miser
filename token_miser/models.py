"""Token Miser models for budget tracking and management."""
from datetime import datetime
from typing import List, Optional


class Project:
    """Represents a project that can have a budget."""
    
    objects = None  # Will be mocked in tests
    
    def __init__(self, name: str, team_id: int):
        self.name = name
        self.team_id = team_id
        self.id = None
    
    def __repr__(self):
        return f"Project(name={self.name!r}, team_id={self.team_id})"


class BudgetLimit:
    """Represents a budget limit for a project, team, or organization."""
    
    objects = None  # Will be mocked in tests
    
    def __init__(
        self,
        project: Optional[Project] = None,
        team_id: Optional[int] = None,
        monthly_budget: float = 0.0,
        alert_thresholds: Optional[List[int]] = None,
    ):
        self.project = project
        self.team_id = team_id
        self.monthly_budget = monthly_budget
        self.alert_thresholds = alert_thresholds or []
        self.id = None
    
    def __repr__(self):
        return (
            f"BudgetLimit(project={self.project!r}, team_id={self.team_id}, "
            f"monthly_budget={self.monthly_budget}, alert_thresholds={self.alert_thresholds})"
        )


class TokenUsage:
    """Represents token usage for a prompt."""
    
    objects = None  # Will be mocked in tests
    
    def __init__(
        self,
        project: Optional[Project] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        timestamp: Optional[datetime] = None,
        cost_usd: float = 0.0,
    ):
        self.project = project
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.timestamp = timestamp or datetime.utcnow()
        self.cost_usd = cost_usd
        self.id = None
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens (input + output)."""
        return self.input_tokens + self.output_tokens
    
    def __repr__(self):
        return (
            f"TokenUsage(project={self.project!r}, input={self.input_tokens}, "
            f"output={self.output_tokens}, cost=${self.cost_usd:.4f})"
        )


class BudgetAlert:
    """Represents an alert when spending approaches budget limit."""
    
    objects = None  # Will be mocked in tests
    
    def __init__(
        self,
        budget_limit: Optional[BudgetLimit] = None,
        current_spend: float = 0.0,
        percentage_used: int = 0,
        alert_threshold: int = 0,
        projected_spend: float = 0.0,
        timestamp: Optional[datetime] = None,
        alert_sent: bool = False,
    ):
        self.budget_limit = budget_limit
        self.current_spend = current_spend
        self.percentage_used = percentage_used
        self.alert_threshold = alert_threshold
        self.projected_spend = projected_spend
        self.timestamp = timestamp or datetime.utcnow()
        self.alert_sent = alert_sent
        self.id = None
    
    def __repr__(self):
        return (
            f"BudgetAlert(budget={self.budget_limit!r}, spend=${self.current_spend:.2f}, "
            f"percentage={self.percentage_used}%, threshold={self.alert_threshold}%, "
            f"projected=${self.projected_spend:.2f})"
        )