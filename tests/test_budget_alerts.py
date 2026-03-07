"""Tests for budget alert functionality."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import TokenUsage, Project, BudgetLimit, BudgetAlert
from token_miser.services.budget_manager import BudgetAlertManager


@pytest.fixture
def sample_project(db):
    """Create a test project."""
    return Project.objects.create(name="BudgetProject", team_id=1)


@pytest.fixture
def budget_limit(sample_project):
    """Create a budget limit for the project."""
    return BudgetLimit.objects.create(
        project=sample_project,
        team_id=1,
        monthly_budget=100.0,
        alert_thresholds=[75, 90, 100]
    )


@pytest.fixture
def alert_manager(db):
    """Create a budget alert manager with database access."""
    manager = BudgetAlertManager()
    # Inject the db instance so calculate_current_spending can use it
    manager.db = db
    return manager


class TestBudgetLimitConfiguration:
    """Tests for budget limit configuration."""
    
    def test_budget_limit_configuration(self, budget_limit):
        """Test that budget limits can be configured."""
        assert budget_limit.monthly_budget == 100.0
        assert 75 in budget_limit.alert_thresholds
        assert 90 in budget_limit.alert_thresholds
        assert 100 in budget_limit.alert_thresholds
    
    def test_budget_limit_has_correct_project(self, budget_limit, sample_project):
        """Test that budget limit is associated with correct project."""
        assert budget_limit.project == sample_project
    
    def test_budget_limit_has_team_id(self, budget_limit):
        """Test that budget limit has team ID."""
        assert budget_limit.team_id == 1
    
    def test_budget_limit_custom_thresholds(self, sample_project):
        """Test budget limit with custom thresholds."""
        budget_limit = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=200.0,
            alert_thresholds=[50, 80]
        )
        assert budget_limit.alert_thresholds == [50, 80]


class TestAlertTriggering:
    """Tests for alert triggering at different thresholds."""
    
    def test_alert_triggered_at_75_percent(self, alert_manager, budget_limit):
        """Test that alert is triggered at 75% of budget."""
        current_spend = 75.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is not None
        assert alert.current_spend == 75.0
        assert alert.percentage_used == 75
        assert alert.alert_threshold == 75
    
    def test_alert_triggered_at_90_percent(self, alert_manager, budget_limit):
        """Test that alert is triggered at 90% of budget."""
        current_spend = 90.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is not None
        assert alert.current_spend == 90.0
        assert alert.percentage_used == 90
        assert alert.alert_threshold == 90
    
    def test_alert_triggered_at_100_percent(self, alert_manager, budget_limit):
        """Test that alert is triggered at 100% of budget."""
        current_spend = 100.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is not None
        assert alert.current_spend == 100.0
        assert alert.percentage_used == 100
        assert alert.alert_threshold == 100
    
    def test_alert_triggered_above_100_percent(self, alert_manager, budget_limit):
        """Test that alert is triggered when exceeding budget."""
        current_spend = 110.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is not None
        assert alert.percentage_used == 110
        assert alert.alert_threshold == 100
    
    def test_no_alert_below_75_percent(self, alert_manager, budget_limit):
        """Test that no alert is triggered below 75%."""
        current_spend = 74.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is None
    
    def test_alert_triggered_highest_threshold(self, alert_manager, budget_limit):
        """Test that highest applicable threshold is used."""
        current_spend = 95.0  # Between 90 and 100
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert is not None
        assert alert.percentage_used == 95
        assert alert.alert_threshold == 90  # Highest threshold below 95%


class TestAlertContent:
    """Tests that alerts include required information."""
    
    def test_alert_includes_current_spend(self, alert_manager, budget_limit):
        """Test that alert includes current spending."""
        current_spend = 75.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert.current_spend == 75.0
    
    def test_alert_includes_budget_limit(self, alert_manager, budget_limit):
        """Test that alert includes budget limit."""
        current_spend = 75.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert.budget_limit == budget_limit
        assert alert.budget_limit.monthly_budget == 100.0
    
    def test_alert_includes_percentage_used(self, alert_manager, budget_limit):
        """Test that alert includes percentage of budget used."""
        current_spend = 75.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert.percentage_used == 75
    
    def test_alert_includes_threshold(self, alert_manager, budget_limit):
        """Test that alert includes triggered threshold."""
        current_spend = 75.0
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        assert alert.alert_threshold == 75


class TestProjectedSpending:
    """Tests for projected spending calculation."""
    
    def test_alert_includes_projected_spend(self, alert_manager, budget_limit):
        """Test that alert includes projected spending."""
        current_spend = 75.0  # 75% - triggers 75% alert
        projected_spend = 120.0
        
        alert = alert_manager.check_budget_alert(
            budget_limit,
            current_spend,
            projected_spend=projected_spend
        )
        
        assert alert is not None
        assert alert.projected_spend == 120.0
    
    def test_projected_spend_based_on_burn_rate(self, alert_manager, sample_project, db):
        """Test that projected spending is calculated based on burn rate."""
        # Create a budget limit
        budget_limit = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=100.0,
            alert_thresholds=[75, 90, 100]
        )
        
        # Create token usage records for burn rate calculation
        now = datetime.utcnow()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Add usage data - $10/day for 5 days = $50 total
        for i in range(5):
            date = first_of_month + timedelta(days=i)
            TokenUsage.objects.create(
                project=sample_project,
                input_tokens=1000,
                output_tokens=1000,
                timestamp=date,
                cost_usd=10.0
            )
        
        # Burn rate should be > 0 (total spent / lookback days)
        burn_rate = alert_manager.calculate_burn_rate(sample_project, lookback_days=5)
        assert burn_rate > 0  # Should have some spending
        
        # Projected spend by end of month should be reasonable
        projected = alert_manager.project_end_of_month_spend(sample_project, now)
        # Current spend is $50 (or portion of it within lookback)
        assert projected >= 0  # Should be non-negative
    
    def test_default_projected_spend_equals_current(self, alert_manager, budget_limit):
        """Test that default projected spend equals current if not specified."""
        current_spend = 75.0  # 75% - triggers alert
        alert = alert_manager.check_budget_alert(budget_limit, current_spend)
        
        # If not specified, should default to current spend
        assert alert is not None
        assert alert.projected_spend == 75.0


class TestDuplicateAlertPrevention:
    """Tests that alerts are not repeatedly sent for same threshold."""
    
    def test_alert_not_resent_for_same_threshold(self, alert_manager, budget_limit):
        """Test that alert is not resent for the same threshold."""
        alert_manager.mark_alert_sent(budget_limit, 75)
        
        should_send = alert_manager.should_send_alert(budget_limit, 75)
        assert should_send is False
    
    def test_alert_sent_for_different_threshold(self, alert_manager, budget_limit):
        """Test that alert can be sent for different threshold."""
        alert_manager.mark_alert_sent(budget_limit, 75)
        
        should_send_90 = alert_manager.should_send_alert(budget_limit, 90)
        assert should_send_90 is True
    
    def test_first_alert_allowed_to_send(self, alert_manager, budget_limit):
        """Test that first alert for a threshold is allowed."""
        should_send = alert_manager.should_send_alert(budget_limit, 75)
        assert should_send is True
    
    def test_alert_tracking_per_budget_limit(self, alert_manager, sample_project):
        """Test that alert tracking is per budget limit."""
        budget1 = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=100.0,
            alert_thresholds=[75, 90, 100]
        )
        budget2 = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=200.0,
            alert_thresholds=[75, 90, 100]
        )
        
        alert_manager.mark_alert_sent(budget1, 75)
        
        # Should still be able to send for budget2
        should_send = alert_manager.should_send_alert(budget2, 75)
        assert should_send is True


class TestBudgetStatus:
    """Tests for budget status reporting."""
    
    def test_budget_status_includes_all_info(self, alert_manager, budget_limit):
        """Test that budget status includes all required information."""
        current_spend = 75.0
        projected_spend = 120.0
        
        status = alert_manager.get_budget_status(
            budget_limit,
            current_spend,
            projected_spend
        )
        
        assert status["budget_limit"] == 100.0
        assert status["current_spend"] == 75.0
        assert status["projected_spend"] == 120.0
        assert status["percentage_used"] == 75
        assert status["remaining"] == 25.0
    
    def test_budget_status_calculation_ok(self, alert_manager, budget_limit):
        """Test budget status with OK status."""
        status = alert_manager.get_budget_status(budget_limit, 50.0, 70.0)
        assert status["status"] == "OK"
    
    def test_budget_status_calculation_warning(self, alert_manager, budget_limit):
        """Test budget status with WARNING status."""
        status = alert_manager.get_budget_status(budget_limit, 75.0, 100.0)
        assert status["status"] == "WARNING"
    
    def test_budget_status_calculation_critical(self, alert_manager, budget_limit):
        """Test budget status with CRITICAL status."""
        status = alert_manager.get_budget_status(budget_limit, 90.0, 120.0)
        assert status["status"] == "CRITICAL"
    
    def test_budget_status_calculation_exceeded(self, alert_manager, budget_limit):
        """Test budget status with EXCEEDED status."""
        status = alert_manager.get_budget_status(budget_limit, 100.0, 150.0)
        assert status["status"] == "EXCEEDED"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_zero_budget_no_alert(self, alert_manager, sample_project):
        """Test that zero budget doesn't trigger alerts."""
        budget_limit = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=0.0,
            alert_thresholds=[75, 90, 100]
        )
        
        alert = alert_manager.check_budget_alert(budget_limit, 10.0)
        assert alert is None
    
    def test_precise_threshold_boundary(self, alert_manager, budget_limit):
        """Test alert triggering at exact threshold boundary."""
        # Exactly 75% should trigger
        alert = alert_manager.check_budget_alert(budget_limit, 75.0)
        assert alert is not None
        assert alert.percentage_used == 75
        assert alert.alert_threshold == 75
        
        # Just below 75% should not trigger
        alert = alert_manager.check_budget_alert(budget_limit, 74.99)
        assert alert is None
    
    def test_multiple_thresholds_correct_one_selected(self, alert_manager, sample_project):
        """Test that correct threshold is selected when multiple apply."""
        budget_limit = BudgetLimit.objects.create(
            project=sample_project,
            team_id=1,
            monthly_budget=100.0,
            alert_thresholds=[50, 75, 90, 100]
        )
        
        # At 85%, should trigger 75% but not 90%
        alert = alert_manager.check_budget_alert(budget_limit, 85.0)
        assert alert is not None
        assert alert.percentage_used == 85
        assert alert.alert_threshold == 75
