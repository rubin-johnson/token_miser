"""Django ORM models for token_miser."""
from datetime import datetime
from typing import Optional


class Project:
    """Represents a project in the system."""
    
    def __init__(self, id: int, name: str, team_id: int):
        self.id = id
        self.name = name
        self.team_id = team_id


class TokenUsage:
    """Represents token usage for a model invocation."""
    
    def __init__(
        self,
        project: Project,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        model: str,
        timestamp: datetime
    ):
        self.project = project
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.cost = cost
        self.model = model
        self.timestamp = timestamp
    
    @property
    def total_tokens(self) -> int:
        """Return total tokens (input + output)."""
        return self.tokens_input + self.tokens_output
