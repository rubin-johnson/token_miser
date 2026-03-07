"""Trending analysis service for Token Miser."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict
from token_miser.models import TokenUsage, Project


class TrendingAnalyzer:
    """Analyzes token cost trends over time."""

    def __init__(self, team_id: int):
        """Initialize the analyzer.
        
        Args:
            team_id: The team ID to analyze trends for
        """
        self.team_id = team_id

    def get_weekly_trends(
        self,
        project_id: Optional[int] = None,
        num_weeks: int = 12
    ) -> List[Dict[str, Any]]:
        """Get weekly cost trends.
        
        Args:
            project_id: Optional project ID to filter by
            num_weeks: Number of weeks to retrieve (default: 12)
            
        Returns:
            List of dicts with weekly trend data
        """
        return self.get_trends_for_period(
            project_id=project_id,
            num_periods=num_weeks,
            period='week'
        )

    def get_monthly_trends(
        self,
        project_id: Optional[int] = None,
        num_months: int = 12
    ) -> List[Dict[str, Any]]:
        """Get monthly cost trends.
        
        Args:
            project_id: Optional project ID to filter by
            num_months: Number of months to retrieve (default: 12)
            
        Returns:
            List of dicts with monthly trend data
        """
        return self.get_trends_for_period(
            project_id=project_id,
            num_periods=num_months,
            period='month'
        )

    def get_trends_for_date_range(
        self,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = 'week'
    ) -> List[Dict[str, Any]]:
        """Get trends for a specific date range.
        
        Args:
            project_id: Optional project ID to filter by
            start_date: Start of the date range
            end_date: End of the date range
            period: Period type ('week' or 'month')
            
        Returns:
            List of dicts with trend data
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(weeks=12)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Collect all usage data in the range
        all_usages = TokenUsage.objects.filter(project__team_id=self.team_id if hasattr(TokenUsage.objects, '__call__') else None)
        
        # Manual filtering since the mock ORM doesn't support complex lookups
        usages = []
        for usage in TokenUsage.objects.all() if hasattr(TokenUsage.objects, 'all') else []:
            # Check team_id matches
            if usage.project and usage.project.team_id != self.team_id:
                continue
            # Check project_id if specified
            if project_id is not None and (not usage.project or usage.project.id != project_id):
                continue
            # Check date range
            if usage.timestamp < start_date or usage.timestamp > end_date:
                continue
            usages.append(usage)
        
        # Group by period
        periods = defaultdict(lambda: {'cost': 0.0, 'total_tokens': 0, 'start': None, 'end': None})
        
        for usage in usages:
            if period == 'week':
                period_start = self._get_week_start(usage.timestamp)
                period_end = period_start + timedelta(days=7)
                period_key = period_start.isoformat()
            else:  # month
                period_start = self._get_month_start(usage.timestamp)
                # Calculate month end
                if period_start.month == 12:
                    period_end = period_start.replace(year=period_start.year + 1, month=1, day=1)
                else:
                    period_end = period_start.replace(month=period_start.month + 1, day=1)
                period_key = period_start.isoformat()
            
            if periods[period_key]['start'] is None:
                periods[period_key]['start'] = period_start
                periods[period_key]['end'] = period_end
            
            periods[period_key]['cost'] += usage.cost
            periods[period_key]['total_tokens'] += usage.total_tokens
        
        # Build trend list
        trends = []
        previous_cost = None
        
        # Sort by period key to ensure chronological order
        for period_key in sorted(periods.keys()):
            period_data = periods[period_key]
            cost = period_data['cost']
            
            # Calculate percentage change
            if previous_cost is not None and previous_cost > 0:
                percentage_change = ((cost - previous_cost) / previous_cost) * 100
            else:
                percentage_change = None
            
            trends.append({
                'period_start': period_data['start'],
                'period_end': period_data['end'],
                'cost': cost,
                'total_tokens': period_data['total_tokens'],
                'percentage_change': percentage_change
            })
            
            previous_cost = cost
        
        return trends

    def get_trends_for_period(
        self,
        project_id: Optional[int] = None,
        num_periods: int = 12,
        period: str = 'week'
    ) -> List[Dict[str, Any]]:
        """Get trends for a specified number of periods in the past.
        
        Args:
            project_id: Optional project ID to filter by
            num_periods: Number of periods to retrieve
            period: Period type ('week' or 'month')
            
        Returns:
            List of dicts with trend data
        """
        now = datetime.utcnow()
        
        if period == 'week':
            start_date = now - timedelta(weeks=num_periods)
        else:  # month
            # Go back num_months
            year = now.year
            month = now.month - num_periods
            day = now.day
            
            while month <= 0:
                month += 12
                year -= 1
            
            # Handle day overflow (e.g., Feb 31)
            try:
                start_date = now.replace(year=year, month=month, day=day)
            except ValueError:
                # Day doesn't exist in target month, use last day of month
                if month == 2:
                    if year % 4 == 0:
                        start_date = now.replace(year=year, month=month, day=29)
                    else:
                        start_date = now.replace(year=year, month=month, day=28)
                else:
                    start_date = now.replace(year=year, month=month, day=1)
                    start_date = start_date - timedelta(days=1)
        
        return self.get_trends_for_date_range(
            project_id=project_id,
            start_date=start_date,
            end_date=now,
            period=period
        )

    def get_trends_by_project(
        self,
        num_weeks: int = 12
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get trends for all projects in team.
        
        Args:
            num_weeks: Number of weeks to retrieve (default: 12)
            
        Returns:
            Dict with project_id as key and trend list as value
        """
        # Get all projects in this team
        projects = Project.objects.filter(team_id=self.team_id)
        
        trends_by_project = {}
        for project in projects:
            trends = self.get_weekly_trends(
                project_id=project.id,
                num_weeks=num_weeks
            )
            trends_by_project[project.id] = trends
        
        return trends_by_project

    def _get_week_start(self, date: datetime) -> datetime:
        """Get the Monday of the week for a given date.
        
        Args:
            date: The date
            
        Returns:
            The start of the week (Monday)
        """
        # Monday is weekday 0
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        # Set to start of day
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    def _get_month_start(self, date: datetime) -> datetime:
        """Get the first day of the month for a given date.
        
        Args:
            date: The date
            
        Returns:
            The first day of the month
        """
        return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
