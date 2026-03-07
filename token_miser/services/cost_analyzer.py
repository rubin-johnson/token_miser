"""Cost analysis services for Token Miser."""
from datetime import datetime
from token_miser.models import TokenUsage, Project


class CostPerProjectAnalyzer:
    """Analyzes token costs grouped by project."""

    def __init__(self, team_id):
        """Initialize the analyzer.
        
        Args:
            team_id: The team ID to analyze costs for
        """
        self.team_id = team_id

    def get_costs_by_project(
        self,
        project_id=None,
        sort_by=None,
        order="asc",
        start_date=None,
        end_date=None,
    ):
        """Get costs grouped by project.
        
        Args:
            project_id: Optional project ID to filter by
            sort_by: Optional field to sort by (e.g., "cost")
            order: Sort order ("asc" or "desc")
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of dicts with project cost data
        """
        # Get all projects for this team
        projects = Project.objects.filter(team_id=self.team_id)
        
        # Filter by specific project if provided
        if project_id is not None:
            projects = [p for p in projects if p.id == project_id]
        
        # Build cost data for each project
        costs_by_project = []
        for project in projects:
            # Get all token usage for this project
            usages = TokenUsage.objects.filter(project=project)
            
            # Filter by date range if provided
            if start_date is not None or end_date is not None:
                filtered_usages = []
                for usage in usages:
                    if start_date is not None and usage.timestamp < start_date:
                        continue
                    if end_date is not None and usage.timestamp > end_date:
                        continue
                    filtered_usages.append(usage)
                usages = filtered_usages
            
            # Calculate totals
            total_cost = sum(u.cost for u in usages)
            total_tokens = sum(u.total_tokens for u in usages)
            
            # Calculate cost per token
            cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0.0
            
            costs_by_project.append({
                "project_id": project.id,
                "project_name": project.name,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "cost_per_token": cost_per_token,
            })
        
        # Sort if requested
        if sort_by == "cost":
            reverse = order == "desc"
            costs_by_project.sort(
                key=lambda x: x["total_cost"],
                reverse=reverse
            )
        
        return costs_by_project

    def compare_projects(self, project_ids):
        """Compare costs between multiple projects.
        
        Args:
            project_ids: List of project IDs to compare
            
        Returns:
            List of dicts with comparison data
        """
        # Get costs for each project
        costs_data = []
        total_costs = {}
        
        for pid in project_ids:
            costs = self.get_costs_by_project(project_id=pid)
            if costs:
                costs_data.append(costs[0])
                total_costs[pid] = costs[0]["total_cost"]
        
        # Add comparison info
        if len(costs_data) >= 2:
            # Compare each to the first one
            first_cost = costs_data[0]["total_cost"]
            for data in costs_data[1:]:
                data["cost_vs_other"] = data["total_cost"] - first_cost
        
        return costs_data
