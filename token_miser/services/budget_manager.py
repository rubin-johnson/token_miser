"""Budget alert management service."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from token_miser.models import (
    TokenUsage,
    Project,
    BudgetLimit,
    BudgetAlert,
)


class BudgetAlertManager:
    """Manages budget limits and alerts for spending."""
    
    def __init__(self):
        """Initialize the budget alert manager."""
        self.alerts_sent = {}  # Track which alerts have been sent to avoid duplicates
        self.db = None  # Will be injected for database access in tests
    
    def configure_budget_limit(
        self,
        project: Project,
        team_id: int,
        monthly_budget: float,
        alert_thresholds: Optional[List[int]] = None,
    ) -> BudgetLimit:
        """
        Configure a budget limit for a project.
        
        Args:
            project: The project to set budget for
            team_id: The team ID
            monthly_budget: Monthly budget in USD
            alert_thresholds: List of percentage thresholds (e.g., [75, 90, 100])
        
        Returns:
            Created BudgetLimit instance
        """
        if alert_thresholds is None:
            alert_thresholds = [75, 90, 100]
        
        budget_limit = BudgetLimit(
            project=project,
            team_id=team_id,
            monthly_budget=monthly_budget,
            alert_thresholds=alert_thresholds,
        )
        return budget_limit
    
    def calculate_current_spending(
        self,
        project: Project,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """
        Calculate total spending for a project within a date range.
        
        Args:
            project: The project to calculate spending for
            start_date: Start of the date range
            end_date: End of the date range
        
        Returns:
            Total cost in USD
        """
        if self.db is None:
            return 0.0
        
        # Query token usages for the project in the date range
        usages = self.db.get_token_usages(project, start_date, end_date)
        total_cost = sum(usage.cost_usd for usage in usages)
        return total_cost
    
    def calculate_burn_rate(
        self,
        project: Project,
        lookback_days: int = 7,
    ) -> float:
        """
        Calculate the daily burn rate (spending per day) for a project.
        
        Args:
            project: The project to calculate burn rate for
            lookback_days: Number of days to look back for calculation
        
        Returns:
            Daily spend rate in USD/day
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=lookback_days)
        total_spent = self.calculate_current_spending(project, start_date, now)
        
        if lookback_days == 0:
            return 0.0
        return total_spent / lookback_days
    
    def project_end_of_month_spend(
        self,
        project: Project,
        current_date: datetime,
    ) -> float:
        """
        Project spending at end of month based on current burn rate.
        
        Args:
            project: The project to project spending for
            current_date: Current date
        
        Returns:
            Projected spending by end of month in USD
        """
        days_in_month = self._days_remaining_in_month(current_date)
        burn_rate = self.calculate_burn_rate(project)
        
        # Get current spend so far this month
        first_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_spend = self.calculate_current_spending(project, first_of_month, current_date)
        
        # Project remaining spend
        projected_remaining = burn_rate * days_in_month
        return current_spend + projected_remaining
    
    def _days_remaining_in_month(self, date: datetime) -> int:
        """Get number of days remaining in the month including today."""
        # Get first day of next month
        if date.month == 12:
            next_month = date.replace(year=date.year + 1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month + 1, day=1)
        
        # Calculate days remaining
        last_day_of_month = next_month - timedelta(days=1)
        days_remaining = (last_day_of_month - date).days + 1
        return max(0, days_remaining)
    
    def check_budget_alert(
        self,
        budget_limit: BudgetLimit,
        current_spend: float,
        projected_spend: Optional[float] = None,
    ) -> Optional[BudgetAlert]:
        """
        Check if an alert should be triggered for a budget limit.
        
        Args:
            budget_limit: The budget limit to check
            current_spend: Current spending amount in USD
            projected_spend: Projected spending by end of period
        
        Returns:
            BudgetAlert if threshold is exceeded, None otherwise
        """
        if budget_limit.monthly_budget == 0:
            return None
        
        percentage_used = int((current_spend / budget_limit.monthly_budget) * 100)
        
        # Find which threshold is triggered
        triggered_threshold = None
        for threshold in sorted(budget_limit.alert_thresholds):
            if percentage_used >= threshold:
                triggered_threshold = threshold
        
        if triggered_threshold is None:
            return None
        
        # Create alert - use constructor directly, not .objects.create()
        alert = BudgetAlert(
            budget_limit=budget_limit,
            current_spend=current_spend,
            percentage_used=percentage_used,
            alert_threshold=triggered_threshold,
            projected_spend=projected_spend or current_spend,
        )
        
        return alert
    
    def should_send_alert(
        self,
        budget_limit: BudgetLimit,
        threshold: int,
    ) -> bool:
        """
        Check if an alert for this threshold has already been sent.
        
        Args:
            budget_limit: The budget limit
            threshold: The threshold percentage
        
        Returns:
            True if alert should be sent (not already sent), False otherwise
        """
        key = (budget_limit.id, threshold)
        return key not in self.alerts_sent
    
    def mark_alert_sent(
        self,
        budget_limit: BudgetLimit,
        threshold: int,
    ) -> None:
        """
        Mark an alert as sent to prevent duplicates.
        
        Args:
            budget_limit: The budget limit
            threshold: The threshold percentage
        """
        key = (budget_limit.id, threshold)
        self.alerts_sent[key] = True
    
    def get_budget_status(
        self,
        budget_limit: BudgetLimit,
        current_spend: float,
        projected_spend: float,
    ) -> dict:
        """
        Get a formatted budget status summary.
        
        Args:
            budget_limit: The budget limit
            current_spend: Current spending
            projected_spend: Projected end-of-month spending
        
        Returns:
            Dictionary with budget status information
        """
        percentage_used = int((current_spend / budget_limit.monthly_budget) * 100)
        remaining = budget_limit.monthly_budget - current_spend
        
        return {
            "budget_limit": budget_limit.monthly_budget,
            "current_spend": current_spend,
            "projected_spend": projected_spend,
            "percentage_used": percentage_used,
            "remaining": remaining,
            "status": self._get_status_label(percentage_used),
        }
    
    def _get_status_label(self, percentage_used: int) -> str:
        """Get a status label based on percentage used."""
        if percentage_used >= 100:
            return "EXCEEDED"
        elif percentage_used >= 90:
            return "CRITICAL"
        elif percentage_used >= 75:
            return "WARNING"
        else:
            return "OK"
