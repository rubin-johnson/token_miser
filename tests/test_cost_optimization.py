"""Tests for cost optimization suggestions."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project
from token_miser.services.optimizer import CostOptimizer


@pytest.fixture
def sample_project(db):
    """Create a test project."""
    return Project.objects.create(name="OptimizeProject", team_id=1)


@pytest.fixture
def model_pricing():
    """Return model pricing info (cost per 1K tokens)."""
    return {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }


@pytest.fixture
def usage_data(sample_project):
    """Create sample usage data with GPT-4 being used for simple tasks."""
    now = datetime.utcnow()
    
    # 90% of GPT-4 usage is for simple completions (low complexity)
    for i in range(90):
        timestamp = now - timedelta(days=30) + timedelta(hours=i)
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=100,
            tokens_output=50,
            cost=0.0045,  # GPT-4 cost
            model="gpt-4",
            timestamp=timestamp,
            complexity="low"
        )
    
    # 10% of GPT-4 usage is for complex reasoning
    for i in range(10):
        timestamp = now - timedelta(days=30) + timedelta(hours=90+i)
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=500,
            tokens_output=200,
            cost=0.0225,  # GPT-4 cost
            model="gpt-4",
            timestamp=timestamp,
            complexity="high"
        )


def test_optimization_suggestions_generated(sample_project, usage_data):
    """Test that optimization suggestions are generated."""
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    assert len(suggestions) > 0
    assert suggestions[0]["current_model"] == "gpt-4"


def test_suggestion_includes_cost_savings(sample_project, usage_data):
    """Test that suggestions include estimated cost savings."""
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    assert "estimated_monthly_savings" in suggestions[0]
    assert suggestions[0]["estimated_monthly_savings"] > 0
    assert "current_monthly_cost" in suggestions[0]
    assert "projected_monthly_cost" in suggestions[0]


def test_suggestion_includes_rationale(sample_project, usage_data):
    """Test that suggestions include rationale."""
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    assert "rationale" in suggestions[0]
    assert "%" in suggestions[0]["rationale"]


def test_downgrade_model_recommendation(sample_project, usage_data):
    """Test that GPT-4 is recommended to downgrade to GPT-3.5-turbo."""
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    assert suggestions[0]["recommended_model"] == "gpt-3.5-turbo"
    assert suggestions[0]["current_model"] == "gpt-4"


def test_suggestions_ranked_by_savings(sample_project):
    """Test that suggestions are ranked by potential savings (highest first)."""
    project2 = Project.objects.create(name="Project2", team_id=1)
    now = datetime.utcnow()
    
    # Heavy GPT-4 usage in project1 (high savings potential)
    for i in range(100):
        timestamp = now - timedelta(days=30) + timedelta(hours=i)
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=1000,
            tokens_output=500,
            cost=0.045,
            model="gpt-4",
            timestamp=timestamp
        )
    
    # Light GPT-4 usage in project2 (low savings potential)
    TokenUsage.objects.create(
        project=project2,
        tokens_input=100,
        tokens_output=50,
        cost=0.0045,
        model="gpt-4",
        timestamp=now
    )
    
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    # First suggestion should have higher savings
    assert suggestions[0]["estimated_monthly_savings"] > suggestions[1]["estimated_monthly_savings"]


def test_minimum_savings_threshold(sample_project, usage_data):
    """Test that suggestions respect minimum savings threshold."""
    optimizer = CostOptimizer(team_id=1, min_savings_threshold=100.0)
    suggestions = optimizer.get_optimization_suggestions()
    
    # If usage data results in savings < $100, no suggestion should be returned
    for suggestion in suggestions:
        assert suggestion["estimated_monthly_savings"] >= 100.0


def test_no_suggestion_for_already_optimized(sample_project):
    """Test that no suggestion is made if model is already optimal."""
    now = datetime.utcnow()
    
    # Use GPT-3.5-turbo (already cost-effective)
    for i in range(100):
        timestamp = now - timedelta(days=30) + timedelta(hours=i)
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=1000,
            tokens_output=500,
            cost=0.001,
            model="gpt-3.5-turbo",
            timestamp=timestamp
        )
    
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions(project_id=sample_project.id)
    
    # Should be empty or not recommend further downgrade
    assert len([s for s in suggestions if s["current_model"] == "gpt-3.5-turbo"]) == 0


def test_optimization_considers_usage_patterns(sample_project):
    """Test that optimization respects usage complexity."""
    now = datetime.utcnow()
    
    # All high-complexity GPT-4 usage (should NOT downgrade)
    for i in range(50):
        timestamp = now - timedelta(days=30) + timedelta(hours=i)
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=1000,
            tokens_output=500,
            cost=0.045,
            model="gpt-4",
            timestamp=timestamp,
            complexity="high"
        )
    
    optimizer = CostOptimizer(team_id=1)
    suggestions = optimizer.get_optimization_suggestions()
    
    # Should not recommend downgrade for high-complexity usage
    gpt4_suggestions = [s for s in suggestions if s["current_model"] == "gpt-4"]
    if gpt4_suggestions:
        assert "high-complexity" in gpt4_suggestions[0]["rationale"] or "complex" in gpt4_suggestions[0]["rationale"]


def test_optimizer_initialization():
    """Test that optimizer can be initialized."""
    optimizer = CostOptimizer(team_id=1, min_savings_threshold=10.0)
    assert optimizer.team_id == 1
    assert optimizer.min_savings_threshold == 10.0
