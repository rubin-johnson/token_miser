"""Pytest configuration and fixtures."""
import pytest
from datetime import datetime, timedelta
from token_miser.models import Project, TokenUsage, BudgetLimit, BudgetAlert, AnomalyAlert


@pytest.fixture
def db():
    """Provide a mock database (using models with in-memory storage)."""
    # Reset the in-memory storage for clean test state
    Project._instances = {}
    Project._id_counter = 1
    TokenUsage._instances = {}
    TokenUsage._id_counter = 1
    BudgetLimit._instances = {}
    BudgetLimit._id_counter = 1
    BudgetAlert._instances = {}
    BudgetAlert._id_counter = 1
    AnomalyAlert._instances = {}
    AnomalyAlert._id_counter = 1
    
    yield None
    
    # Cleanup after test
    Project._instances = {}
    Project._id_counter = 1
    TokenUsage._instances = {}
    TokenUsage._id_counter = 1
    BudgetLimit._instances = {}
    BudgetLimit._id_counter = 1
    BudgetAlert._instances = {}
    BudgetAlert._id_counter = 1
    AnomalyAlert._instances = {}
    AnomalyAlert._id_counter = 1
