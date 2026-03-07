"""Tests for cost per project analysis."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project
from token_miser.services.cost_analyzer import CostPerProjectAnalyzer


@pytest.fixture
def sample_projects(db):
    """Create test projects."""
    p1 = Project.objects.create(name="ProjectA", team_id=1)
    p2 = Project.objects.create(name="ProjectB", team_id=1)
    p3 = Project.objects.create(name="ProjectC", team_id=1)
    return [p1, p2, p3]


@pytest.fixture
def sample_token_usage(sample_projects):
    """Create sample token usage data."""
    now = datetime.utcnow()
    usage_data = [
        # ProjectA: 1000 tokens at $0.001 per token = $1.00
        TokenUsage.objects.create(
            project=sample_projects[0],
            tokens_input=500,
            tokens_output=500,
            cost=1.00,
            model="gpt-4",
            timestamp=now
        ),
        # ProjectB: 2000 tokens at $0.001 per token = $2.00
        TokenUsage.objects.create(
            project=sample_projects[1],
            tokens_input=1000,
            tokens_output=1000,
            cost=2.00,
            model="gpt-4",
            timestamp=now
        ),
        # ProjectC: 500 tokens at $0.001 per token = $0.50
        TokenUsage.objects.create(
            project=sample_projects[2],
            tokens_input=250,
            tokens_output=250,
            cost=0.50,
            model="gpt-3.5-turbo",
            timestamp=now
        ),
    ]
    return usage_data


def test_get_costs_by_project(sample_projects, sample_token_usage):
    """Test that costs are correctly grouped by project."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_by_project = analyzer.get_costs_by_project()
    
    assert len(costs_by_project) == 3
    assert costs_by_project[0]["project_id"] == sample_projects[0].id
    assert costs_by_project[0]["project_name"] == "ProjectA"
    assert costs_by_project[0]["total_cost"] == 1.00
    assert costs_by_project[1]["total_cost"] == 2.00
    assert costs_by_project[2]["total_cost"] == 0.50


def test_get_costs_by_project_with_total_tokens(sample_projects, sample_token_usage):
    """Test that total tokens are included in project cost breakdown."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_by_project = analyzer.get_costs_by_project()
    
    assert costs_by_project[0]["total_tokens"] == 1000
    assert costs_by_project[1]["total_tokens"] == 2000
    assert costs_by_project[2]["total_tokens"] == 500


def test_filter_by_project(sample_projects, sample_token_usage):
    """Test filtering costs by a single project."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs = analyzer.get_costs_by_project(project_id=sample_projects[0].id)
    
    assert len(costs) == 1
    assert costs[0]["project_id"] == sample_projects[0].id
    assert costs[0]["total_cost"] == 1.00


def test_sort_costs_by_project_descending(sample_projects, sample_token_usage):
    """Test sorting projects by cost (highest to lowest)."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_by_project = analyzer.get_costs_by_project(sort_by="cost", order="desc")
    
    assert costs_by_project[0]["project_name"] == "ProjectB"
    assert costs_by_project[0]["total_cost"] == 2.00
    assert costs_by_project[1]["project_name"] == "ProjectA"
    assert costs_by_project[2]["project_name"] == "ProjectC"


def test_sort_costs_by_project_ascending(sample_projects, sample_token_usage):
    """Test sorting projects by cost (lowest to highest)."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_by_project = analyzer.get_costs_by_project(sort_by="cost", order="asc")
    
    assert costs_by_project[0]["project_name"] == "ProjectC"
    assert costs_by_project[1]["project_name"] == "ProjectA"
    assert costs_by_project[2]["project_name"] == "ProjectB"


def test_per_unit_cost_calculation(sample_projects, sample_token_usage):
    """Test that per-token cost is correctly calculated."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_by_project = analyzer.get_costs_by_project()
    
    # ProjectA: $1.00 / 1000 tokens = $0.001 per token
    assert costs_by_project[0]["cost_per_token"] == pytest.approx(0.001, rel=1e-4)
    # ProjectB: $2.00 / 2000 tokens = $0.001 per token
    assert costs_by_project[1]["cost_per_token"] == pytest.approx(0.001, rel=1e-4)
    # ProjectC: $0.50 / 500 tokens = $0.001 per token
    assert costs_by_project[2]["cost_per_token"] == pytest.approx(0.001, rel=1e-4)


def test_compare_projects(sample_projects, sample_token_usage):
    """Test comparing costs between two projects."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    comparison = analyzer.compare_projects(
        project_ids=[sample_projects[0].id, sample_projects[1].id]
    )
    
    assert len(comparison) == 2
    assert comparison[0]["project_name"] == "ProjectA"
    assert comparison[0]["total_cost"] == 1.00
    assert comparison[1]["project_name"] == "ProjectB"
    assert comparison[1]["total_cost"] == 2.00
    assert comparison[1]["cost_vs_other"] == 2.00 - 1.00


def test_costs_by_project_date_range(sample_projects):
    """Test filtering costs by date range."""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Create usage data at different times
    TokenUsage.objects.create(
        project=sample_projects[0],
        tokens_input=100,
        tokens_output=100,
        cost=0.20,
        model="gpt-4",
        timestamp=now
    )
    TokenUsage.objects.create(
        project=sample_projects[0],
        tokens_input=100,
        tokens_output=100,
        cost=0.20,
        model="gpt-4",
        timestamp=yesterday
    )
    TokenUsage.objects.create(
        project=sample_projects[0],
        tokens_input=100,
        tokens_output=100,
        cost=0.20,
        model="gpt-4",
        timestamp=week_ago
    )
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    costs_recent = analyzer.get_costs_by_project(
        start_date=yesterday,
        end_date=now
    )
    
    assert costs_recent[0]["total_cost"] == pytest.approx(0.40, rel=1e-4)
