"""Tests for CostPerProjectAnalyzer implementation."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project
from token_miser.services.cost_analyzer import CostPerProjectAnalyzer


def test_analyzer_initialization():
    """Test that CostPerProjectAnalyzer can be instantiated."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    assert analyzer.team_id == 1


def test_get_costs_by_project_returns_dict_list():
    """Test that method returns list of dicts."""
    analyzer = CostPerProjectAnalyzer(team_id=1)
    result = analyzer.get_costs_by_project()
    assert isinstance(result, list)


def test_analyzer_handles_empty_projects():
    """Test that analyzer gracefully handles teams with no usage data."""
    analyzer = CostPerProjectAnalyzer(team_id=999)
    result = analyzer.get_costs_by_project()
    assert result == []


def test_compare_projects_returns_list():
    """Test that compare_projects returns expected structure."""
    p1 = Project(id=1, name="P1", team_id=1)
    p2 = Project(id=2, name="P2", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    result = analyzer.compare_projects(project_ids=[p1.id, p2.id])
    
    assert isinstance(result, list)
    assert len(result) == 0  # No usage data yet


def test_get_costs_by_project_with_data():
    """Test cost calculation with actual usage data."""
    p1 = Project(id=1, name="Project A", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    # Add some usage data
    usage1 = TokenUsage(
        project=p1,
        tokens_input=100,
        tokens_output=50,
        cost=0.01,
        model="gpt-4",
        timestamp=datetime.now()
    )
    usage2 = TokenUsage(
        project=p1,
        tokens_input=200,
        tokens_output=100,
        cost=0.02,
        model="gpt-4",
        timestamp=datetime.now()
    )
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.get_costs_by_project()
    
    assert len(result) == 1
    assert result[0]['project_id'] == 1
    assert result[0]['project_name'] == "Project A"
    assert result[0]['total_cost'] == 0.03
    assert result[0]['total_tokens'] == 450  # (100+50) + (200+100)
    assert result[0]['cost_per_token'] == pytest.approx(0.03 / 450)


def test_get_costs_by_project_filter_by_project_id():
    """Test filtering to a single project."""
    p1 = Project(id=1, name="Project A", team_id=1)
    p2 = Project(id=2, name="Project B", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.01, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 200, 100, 0.02, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.get_costs_by_project(project_id=1)
    
    assert len(result) == 1
    assert result[0]['project_id'] == 1


def test_get_costs_by_project_sort_by_cost():
    """Test sorting by cost."""
    p1 = Project(id=1, name="Project A", team_id=1)
    p2 = Project(id=2, name="Project B", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.05, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 200, 100, 0.01, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    # Descending (default)
    result = analyzer.get_costs_by_project(sort_by="cost", order="desc")
    assert result[0]['project_id'] == 1
    assert result[1]['project_id'] == 2
    
    # Ascending
    result = analyzer.get_costs_by_project(sort_by="cost", order="asc")
    assert result[0]['project_id'] == 2
    assert result[1]['project_id'] == 1


def test_get_costs_by_project_sort_by_name():
    """Test sorting by project name."""
    p1 = Project(id=1, name="Zebra", team_id=1)
    p2 = Project(id=2, name="Apple", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.01, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 200, 100, 0.01, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.get_costs_by_project(sort_by="name", order="asc")
    assert result[0]['project_name'] == "Apple"
    assert result[1]['project_name'] == "Zebra"


def test_get_costs_by_project_sort_by_tokens():
    """Test sorting by tokens."""
    p1 = Project(id=1, name="Project A", team_id=1)
    p2 = Project(id=2, name="Project B", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.01, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 500, 500, 0.02, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.get_costs_by_project(sort_by="tokens", order="desc")
    assert result[0]['project_id'] == 2
    assert result[1]['project_id'] == 1


def test_get_costs_by_project_date_filtering():
    """Test filtering by date range."""
    p1 = Project(id=1, name="Project A", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    now = datetime.now()
    old_date = now - timedelta(days=10)
    future_date = now + timedelta(days=10)
    
    usage1 = TokenUsage(p1, 100, 50, 0.01, "gpt-4", old_date)
    usage2 = TokenUsage(p1, 200, 100, 0.02, "gpt-4", now)
    usage3 = TokenUsage(p1, 300, 150, 0.03, "gpt-4", future_date)
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    analyzer.add_usage(usage3)
    
    # Filter to recent only
    start = now - timedelta(days=1)
    result = analyzer.get_costs_by_project(start_date=start, end_date=now)
    
    assert len(result) == 1
    assert result[0]['total_cost'] == pytest.approx(0.02)


def test_compare_projects_with_data():
    """Test project comparison."""
    p1 = Project(id=1, name="Project A", team_id=1)
    p2 = Project(id=2, name="Project B", team_id=1)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.10, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 200, 100, 0.05, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.compare_projects(project_ids=[p1.id, p2.id])
    
    assert len(result) == 2
    assert result[0]['project_id'] == 1
    assert result[0]['cost_vs_other'] == pytest.approx(0.0)  # First project is baseline
    assert result[1]['project_id'] == 2
    assert result[1]['cost_vs_other'] == pytest.approx(-0.05)  # 0.05 - 0.10


def test_analyzer_filters_by_team():
    """Test that analyzer only sees usage from its team."""
    p1 = Project(id=1, name="Project A", team_id=1)
    p2 = Project(id=2, name="Project B", team_id=2)
    
    analyzer = CostPerProjectAnalyzer(team_id=1)
    
    usage1 = TokenUsage(p1, 100, 50, 0.01, "gpt-4", datetime.now())
    usage2 = TokenUsage(p2, 200, 100, 0.02, "gpt-4", datetime.now())
    
    analyzer.add_usage(usage1)
    analyzer.add_usage(usage2)
    
    result = analyzer.get_costs_by_project()
    
    assert len(result) == 1
    assert result[0]['project_id'] == 1
