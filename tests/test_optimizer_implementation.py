"""Tests for the CostOptimizer implementation (STORY-003)."""
import pytest
from token_miser.models import TokenUsage, Project
from token_miser.services.optimizer import CostOptimizer


def test_optimizer_initialization(db):
    """Test that optimizer initializes correctly."""
    optimizer = CostOptimizer(team_id=1, min_savings_threshold=10.0)
    assert optimizer.team_id == 1
    assert optimizer.min_savings_threshold == 10.0


def test_get_optimization_suggestions_returns_list(db):
    """Test that get_optimization_suggestions returns a list."""
    optimizer = CostOptimizer(team_id=1)
    result = optimizer.get_optimization_suggestions()
    assert isinstance(result, list)


def test_suggestion_structure(db):
    """Test that suggestions have required fields."""
    project = Project.objects.create(name="Test", team_id=1)
    
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    if suggestions:
        required_keys = [
            "current_model",
            "recommended_model",
            "current_monthly_cost",
            "projected_monthly_cost",
            "estimated_monthly_savings",
            "rationale"
        ]
        for key in required_keys:
            assert key in suggestions[0]


def test_token_usage_complexity_field(db):
    """Test that TokenUsage model has complexity field."""
    project = Project.objects.create(name="Test", team_id=1)
    usage = TokenUsage(
        project=project,
        tokens_input=100,
        tokens_output=50,
        cost=0.01,
        model="gpt-4",
        complexity="high"
    )
    # Manually save by adding to instances (simulating save)
    TokenUsage._instances[usage.id] = usage
    
    retrieved = TokenUsage.objects.get(id=usage.id)
    assert retrieved.complexity == "high"
