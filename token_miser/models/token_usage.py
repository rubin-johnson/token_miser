"""TokenUsage model for Token Miser."""
from datetime import datetime


class TokenUsage:
    """Represents a token usage event."""

    _id_counter = 1
    _instances = {}

    def __init__(self, project, tokens_input, tokens_output, cost, model, timestamp):
        """Initialize token usage.
        
        Args:
            project: The Project instance
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost: Cost in USD
            model: Model name
            timestamp: Datetime of the usage
        """
        self.id = TokenUsage._id_counter
        TokenUsage._id_counter += 1
        self.project = project
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.cost = cost
        self.model = model
        self.timestamp = timestamp
        TokenUsage._instances[self.id] = self

    @property
    def total_tokens(self):
        """Get total tokens (input + output)."""
        return self.tokens_input + self.tokens_output

    @classmethod
    def objects(cls):
        """Return the objects manager."""
        return TokenUsageManager()

    def __repr__(self):
        return f"<TokenUsage {self.id}: {self.total_tokens} tokens, ${self.cost}>"


class TokenUsageManager:
    """Manager for TokenUsage objects (mimics Django ORM)."""

    def create(self, project, tokens_input, tokens_output, cost, model, timestamp):
        """Create a new token usage record.
        
        Args:
            project: The Project instance
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost: Cost in USD
            model: Model name
            timestamp: Datetime of the usage
            
        Returns:
            The created TokenUsage instance
        """
        return TokenUsage(project, tokens_input, tokens_output, cost, model, timestamp)

    def get(self, id):
        """Get token usage by ID.
        
        Args:
            id: The token usage ID
            
        Returns:
            The TokenUsage instance
            
        Raises:
            KeyError: If not found
        """
        return TokenUsage._instances[id]

    def all(self):
        """Get all token usage records.
        
        Returns:
            List of all TokenUsage instances
        """
        return list(TokenUsage._instances.values())

    def filter(self, **kwargs):
        """Filter token usage by attributes.
        
        Args:
            **kwargs: Filter criteria (e.g., project=project_instance)
            
        Returns:
            List of matching TokenUsage instances
        """
        results = []
        for usage in TokenUsage._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(usage, key) or getattr(usage, key) != value:
                    match = False
                    break
            if match:
                results.append(usage)
        return results


# Module-level objects manager
class Objects:
    """Module-level manager for token usage."""

    @staticmethod
    def create(project, tokens_input, tokens_output, cost, model, timestamp):
        """Create a new token usage record."""
        return TokenUsage(project, tokens_input, tokens_output, cost, model, timestamp)

    @staticmethod
    def get(id):
        """Get token usage by ID."""
        return TokenUsage._instances[id]

    @staticmethod
    def all():
        """Get all token usage records."""
        return list(TokenUsage._instances.values())

    @staticmethod
    def filter(**kwargs):
        """Filter token usage by attributes."""
        results = []
        for usage in TokenUsage._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(usage, key) or getattr(usage, key) != value:
                    match = False
                    break
            if match:
                results.append(usage)
        return results


# Attach objects manager to class
TokenUsage.objects = Objects
