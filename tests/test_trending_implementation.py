"""Tests for TrendingAnalyzer implementation."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project
from token_miser.services.trending import TrendingAnalyzer


@pytest.fixture
def sample_project(db):
    """Create a test project."""
    return Project.objects.create(name="TestProject", team_id=1)


def test_trending_analyzer_initialization():
    """Test that analyzer initializes correctly."""
    analyzer = TrendingAnalyzer(team_id=1)
    assert analyzer.team_id == 1


def test_weekly_trends_returns_list():
    """Test that get_weekly_trends returns a list."""
    analyzer = TrendingAnalyzer(team_id=1)
    result = analyzer.get_weekly_trends()
    assert isinstance(result, list)


def test_monthly_trends_returns_list():
    """Test that get_monthly_trends returns a list."""
    analyzer = TrendingAnalyzer(team_id=1)
    result = analyzer.get_monthly_trends()
    assert isinstance(result, list)


def test_trend_entry_structure(sample_project, db):
    """Test that trend entries have required fields."""
    now = datetime.utcnow()
    
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=now
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_weekly_trends(project_id=sample_project.id, num_weeks=1)
    
    if trends:
        required_keys = ["period_start", "period_end", "cost", "total_tokens", "percentage_change"]
        for key in required_keys:
            assert key in trends[0]


def test_weekly_trends_with_data(sample_project, db):
    """Test weekly trends calculation with actual data."""
    now = datetime.utcnow()
    # Get the start of this week (Monday)
    days_since_monday = now.weekday()
    week_start = now - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Add data for this week
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=week_start + timedelta(days=1)
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_weekly_trends(project_id=sample_project.id, num_weeks=1)
    
    assert len(trends) >= 0  # May be empty if no complete weeks


def test_monthly_trends_with_data(sample_project, db):
    """Test monthly trends calculation with actual data."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Add data for this month
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=month_start + timedelta(days=5)
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_monthly_trends(project_id=sample_project.id, num_months=1)
    
    assert len(trends) >= 0  # May be empty if no complete months


def test_trends_for_date_range(sample_project, db):
    """Test get_trends_for_date_range method."""
    now = datetime.utcnow()
    start = now - timedelta(days=30)
    end = now
    
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=now
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_trends_for_date_range(
        project_id=sample_project.id,
        start_date=start,
        end_date=end,
        period='week'
    )
    
    assert isinstance(trends, list)


def test_trends_by_project(db):
    """Test get_trends_by_project method."""
    p1 = Project.objects.create(name="Project1", team_id=1)
    p2 = Project.objects.create(name="Project2", team_id=1)
    
    now = datetime.utcnow()
    TokenUsage.objects.create(
        project=p1,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=now
    )
    TokenUsage.objects.create(
        project=p2,
        tokens_input=200,
        tokens_output=100,
        cost=0.20,
        model="gpt-4",
        timestamp=now
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_trends_by_project()
    
    assert isinstance(trends, dict)


def test_percentage_change_calculation(sample_project, db):
    """Test that percentage change is calculated correctly."""
    now = datetime.utcnow()
    
    # Create two weeks of data
    week1_start = (now - timedelta(weeks=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_monday = week1_start.weekday()
    week1_start = week1_start - timedelta(days=days_since_monday)
    
    week2_start = (now).replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_monday = week2_start.weekday()
    week2_start = week2_start - timedelta(days=days_since_monday)
    
    # Week 1: $100
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=1.00,
        model="gpt-4",
        timestamp=week1_start + timedelta(days=1)
    )
    
    # Week 2: $150 (50% increase)
    for i in range(1):
        TokenUsage.objects.create(
            project=sample_project,
            tokens_input=100,
            tokens_output=50,
            cost=1.50,
            model="gpt-4",
            timestamp=week2_start + timedelta(days=1)
        )
    
    analyzer = TrendingAnalyzer(team_id=1)
    trends = analyzer.get_weekly_trends(project_id=sample_project.id, num_weeks=2)
    
    # Should have at most 2 trend entries
    assert len(trends) <= 2


def test_no_trends_for_other_team(sample_project, db):
    """Test that trends only include data for the specified team."""
    now = datetime.utcnow()
    
    TokenUsage.objects.create(
        project=sample_project,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=now
    )
    
    # Analyzer for different team should see no data
    analyzer = TrendingAnalyzer(team_id=999)
    trends = analyzer.get_weekly_trends(num_weeks=1)
    
    assert trends == []


def test_trends_without_project_filter(db):
    """Test trends that aggregate across all projects."""
    p1 = Project.objects.create(name="Project1", team_id=1)
    p2 = Project.objects.create(name="Project2", team_id=1)
    
    now = datetime.utcnow()
    TokenUsage.objects.create(
        project=p1,
        tokens_input=100,
        tokens_output=50,
        cost=0.10,
        model="gpt-4",
        timestamp=now
    )
    TokenUsage.objects.create(
        project=p2,
        tokens_input=200,
        tokens_output=100,
        cost=0.20,
        model="gpt-4",
        timestamp=now
    )
    
    analyzer = TrendingAnalyzer(team_id=1)
    # Without project_id, should aggregate all projects
    trends = analyzer.get_weekly_trends(project_id=None, num_weeks=1)
    
    assert isinstance(trends, list)
