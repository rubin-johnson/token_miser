"""Cost analysis service for breaking down costs by project."""
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict


class CostPerProjectAnalyzer:
    """Analyzes token costs broken down by project."""
    
    def __init__(self, team_id: int):
        """Initialize the analyzer with a team_id.
        
        Args:
            team_id: The team ID to analyze costs for.
        """
        self.team_id = team_id
        # In-memory storage for testing purposes
        self._token_usages = []
    
    def add_usage(self, usage):
        """Add a token usage record (for testing)."""
        self._token_usages.append(usage)
    
    def get_costs_by_project(
        self,
        project_id: Optional[int] = None,
        sort_by: str = "cost",
        order: str = "desc",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get costs broken down by project.
        
        Args:
            project_id: Optional project ID to filter to a single project.
            sort_by: Field to sort by: "cost", "name", or "tokens".
            order: Sort order: "asc" or "desc".
            start_date: Optional start date for filtering.
            end_date: Optional end date for filtering.
        
        Returns:
            List of dicts with keys: project_id, project_name, total_cost, 
            total_tokens, cost_per_token.
        """
        # Filter usages by team
        filtered_usages = [
            u for u in self._token_usages
            if u.project.team_id == self.team_id
        ]
        
        # Filter by project_id if provided
        if project_id is not None:
            filtered_usages = [u for u in filtered_usages if u.project.id == project_id]
        
        # Filter by date range if provided
        if start_date is not None:
            filtered_usages = [u for u in filtered_usages if u.timestamp >= start_date]
        if end_date is not None:
            filtered_usages = [u for u in filtered_usages if u.timestamp <= end_date]
        
        # Group by project
        projects_data = defaultdict(lambda: {
            'project_id': None,
            'project_name': None,
            'total_cost': 0.0,
            'total_tokens': 0
        })
        
        for usage in filtered_usages:
            project_key = usage.project.id
            if projects_data[project_key]['project_id'] is None:
                projects_data[project_key]['project_id'] = usage.project.id
                projects_data[project_key]['project_name'] = usage.project.name
            
            projects_data[project_key]['total_cost'] += usage.cost
            projects_data[project_key]['total_tokens'] += usage.total_tokens
        
        # Calculate cost_per_token and convert to list
        results = []
        for project_data in projects_data.values():
            if project_data['total_tokens'] > 0:
                cost_per_token = project_data['total_cost'] / project_data['total_tokens']
            else:
                cost_per_token = 0.0
            
            results.append({
                'project_id': project_data['project_id'],
                'project_name': project_data['project_name'],
                'total_cost': project_data['total_cost'],
                'total_tokens': project_data['total_tokens'],
                'cost_per_token': cost_per_token
            })
        
        # Sort results
        sort_key_map = {
            'cost': lambda x: x['total_cost'],
            'name': lambda x: x['project_name'] or '',
            'tokens': lambda x: x['total_tokens']
        }
        
        reverse = order == 'desc'
        if sort_by in sort_key_map:
            results.sort(key=sort_key_map[sort_by], reverse=reverse)
        
        return results
    
    def compare_projects(self, project_ids: List[int]) -> List[Dict[str, Any]]:
        """Compare costs across multiple projects.
        
        Args:
            project_ids: List of project IDs to compare.
        
        Returns:
            List of comparison dicts including cost_vs_other delta.
        """
        # Get costs for the specified projects
        all_costs = self.get_costs_by_project()
        
        # Filter to only requested projects
        project_costs = {
            cost['project_id']: cost
            for cost in all_costs
            if cost['project_id'] in project_ids
        }
        
        # Build result list with cost_vs_other
        results = []
        if project_costs:
            first_project_cost = next(iter(project_costs.values()))['total_cost']
            
            for project_id in project_ids:
                if project_id in project_costs:
                    cost_data = project_costs[project_id]
                    cost_vs_other = cost_data['total_cost'] - first_project_cost
                    result = cost_data.copy()
                    result['cost_vs_other'] = cost_vs_other
                    results.append(result)
        
        return results
