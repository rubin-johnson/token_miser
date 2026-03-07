"""Pytest configuration and fixtures."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock


class MockDBObjectsManager:
    """Mock objects manager for models."""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, **kwargs):
        """Create and store a model instance."""
        # This method is called on the class, so we need to create the instance
        # We'll inject the model class during fixture setup
        pass


class MockDB:
    """Mock database for testing."""
    
    def __init__(self):
        self.projects = {}
        self.token_usages = {}
        self.budget_limits = {}
        self.budget_alerts = {}
        self.next_id = 1
    
    def store(self, instance):
        """Store a model instance and assign it an ID."""
        instance.id = self.next_id
        self.next_id += 1
        
        # Store based on type
        class_name = instance.__class__.__name__
        if class_name == "Project":
            self.projects[instance.id] = instance
        elif class_name == "TokenUsage":
            self.token_usages[instance.id] = instance
        elif class_name == "BudgetLimit":
            self.budget_limits[instance.id] = instance
        elif class_name == "BudgetAlert":
            self.budget_alerts[instance.id] = instance
        
        return instance
    
    def get_token_usages(self, project, start_date, end_date):
        """Get token usages for a project in a date range."""
        usages = []
        for usage in self.token_usages.values():
            if (usage.project == project and
                start_date <= usage.timestamp <= end_date):
                usages.append(usage)
        return usages


@pytest.fixture
def db():
    """Provide a mock database."""
    from token_miser import models
    
    mock_db = MockDB()
    
    # Create custom create methods for each model
    def make_create(model_class):
        def create(**kwargs):
            instance = model_class(**kwargs)
            return mock_db.store(instance)
        return create
    
    # Create mock objects managers and attach to models
    models.Project.objects = Mock()
    models.Project.objects.create = make_create(models.Project)
    
    models.TokenUsage.objects = Mock()
    models.TokenUsage.objects.create = make_create(models.TokenUsage)
    
    models.BudgetLimit.objects = Mock()
    models.BudgetLimit.objects.create = make_create(models.BudgetLimit)
    
    models.BudgetAlert.objects = Mock()
    models.BudgetAlert.objects.create = make_create(models.BudgetAlert)
    
    yield mock_db
    
    # Cleanup
    models.Project.objects = None
    models.TokenUsage.objects = None
    models.BudgetLimit.objects = None
    models.BudgetAlert.objects = None
