"""Pytest configuration and fixtures."""
import pytest
from token_miser.models import Project, TokenUsage


@pytest.fixture
def db():
    """Provide a clean database state for each test.
    
    This fixture resets the in-memory object storage before each test.
    """
    # Reset in-memory storage
    Project._instances = {}
    Project._id_counter = 1
    TokenUsage._instances = {}
    TokenUsage._id_counter = 1
    
    yield
    
    # Clean up after test
    Project._instances = {}
    Project._id_counter = 1
    TokenUsage._instances = {}
    TokenUsage._id_counter = 1
