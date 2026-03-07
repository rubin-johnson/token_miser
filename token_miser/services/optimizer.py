"""Cost optimization services for Token Miser."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict
from token_miser.models import TokenUsage, Project


class CostOptimizer:
    """Analyzes token usage to suggest cost optimizations."""
    
    # Model hierarchy for downgrades (from expensive to cheaper)
    MODEL_HIERARCHY = {
        "gpt-4": "gpt-3.5-turbo",
        "gpt-4-turbo": "gpt-3.5-turbo",
        "gpt-3.5-turbo": None,  # Already optimal
    }
    
    # Model pricing (cost per 1K tokens)
    MODEL_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }
    
    def __init__(self, team_id: int, min_savings_threshold: float = 0.0):
        """Initialize the optimizer.
        
        Args:
            team_id: The team ID to optimize for
            min_savings_threshold: Minimum monthly savings required to suggest (default: $0)
        """
        self.team_id = team_id
        self.min_savings_threshold = min_savings_threshold
    
    def get_optimization_suggestions(
        self,
        project_id: Optional[int] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get optimization suggestions for a team or project.
        
        Args:
            project_id: Optional project ID to filter by
            days: Number of days of historical data to analyze
            
        Returns:
            List of suggestion dicts, sorted by savings (highest first)
        """
        suggestions = []
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Get all projects for this team
        all_projects = Project.objects.filter(team_id=self.team_id)
        
        # Filter by specific project if provided
        if project_id is not None:
            all_projects = [p for p in all_projects if p.id == project_id]
        
        # Analyze each project
        for project in all_projects:
            # Get token usage for this project in the date range
            usages = [
                u for u in TokenUsage.objects.filter(project=project)
                if start_date <= u.timestamp <= now
            ]
            
            if not usages:
                continue
            
            # Group by model
            usage_by_model = defaultdict(list)
            for usage in usages:
                if usage.model:
                    usage_by_model[usage.model].append(usage)
            
            # Analyze each model for downgrade potential
            for model, model_usages in usage_by_model.items():
                # Check if model can be downgraded
                if model not in self.MODEL_HIERARCHY or self.MODEL_HIERARCHY[model] is None:
                    continue
                
                recommended_model = self.MODEL_HIERARCHY[model]
                
                # Calculate metrics
                low_complexity_count = sum(
                    1 for u in model_usages
                    if not u.complexity or u.complexity == "low"
                )
                high_complexity_count = sum(
                    1 for u in model_usages
                    if u.complexity == "high"
                )
                total_count = len(model_usages)
                low_complexity_pct = (low_complexity_count / total_count * 100) if total_count > 0 else 0
                
                # If too much high-complexity work, don't recommend downgrade
                if low_complexity_pct < 50:
                    continue
                
                # Calculate current cost
                current_cost = sum(u.cost_usd for u in model_usages)
                
                # Calculate projected cost with recommended model
                # Estimate projected cost based on tokens
                total_input_tokens = sum(u.input_tokens for u in model_usages)
                total_output_tokens = sum(u.output_tokens for u in model_usages)
                
                current_pricing = self.MODEL_PRICING.get(model, {})
                recommended_pricing = self.MODEL_PRICING.get(recommended_model, {})
                
                current_input_cost = (total_input_tokens / 1000) * current_pricing.get("input", 0)
                current_output_cost = (total_output_tokens / 1000) * current_pricing.get("output", 0)
                projected_input_cost = (total_input_tokens / 1000) * recommended_pricing.get("input", 0)
                projected_output_cost = (total_output_tokens / 1000) * recommended_pricing.get("output", 0)
                
                projected_cost = projected_input_cost + projected_output_cost
                estimated_savings = current_cost - projected_cost
                
                # Only include if savings exceed threshold
                if estimated_savings < self.min_savings_threshold:
                    continue
                
                # Build rationale
                rationale = (
                    f"Model {model} used for {low_complexity_pct:.0f}% simple completions. "
                    f"Only {high_complexity_count} of {total_count} requests require advanced reasoning."
                )
                
                suggestions.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "current_model": model,
                    "recommended_model": recommended_model,
                    "current_monthly_cost": current_cost,
                    "projected_monthly_cost": projected_cost,
                    "estimated_monthly_savings": estimated_savings,
                    "low_complexity_percentage": low_complexity_pct,
                    "rationale": rationale,
                })
        
        # Sort by savings (highest first)
        suggestions.sort(
            key=lambda x: x["estimated_monthly_savings"],
            reverse=True
        )
        
        return suggestions
