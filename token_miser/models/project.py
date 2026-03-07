"""Project model for Token Miser."""


class Project:
    """Represents a project that uses tokens."""

    _id_counter = 1
    _instances = {}

    def __init__(self, name, team_id):
        """Initialize a project.
        
        Args:
            name: The project name
            team_id: The team ID
        """
        self.id = Project._id_counter
        Project._id_counter += 1
        self.name = name
        self.team_id = team_id
        Project._instances[self.id] = self

    @classmethod
    def objects(cls):
        """Return the objects manager."""
        return ProjectManager()

    def __repr__(self):
        return f"<Project {self.id}: {self.name}>"


class ProjectManager:
    """Manager for Project objects (mimics Django ORM)."""

    def create(self, name, team_id):
        """Create a new project.
        
        Args:
            name: The project name
            team_id: The team ID
            
        Returns:
            The created Project instance
        """
        return Project(name, team_id)

    def get(self, id):
        """Get a project by ID.
        
        Args:
            id: The project ID
            
        Returns:
            The Project instance
            
        Raises:
            KeyError: If project not found
        """
        return Project._instances[id]

    def all(self):
        """Get all projects.
        
        Returns:
            List of all Project instances
        """
        return list(Project._instances.values())

    def filter(self, **kwargs):
        """Filter projects by attributes.
        
        Args:
            **kwargs: Filter criteria (e.g., team_id=1)
            
        Returns:
            List of matching Project instances
        """
        results = []
        for project in Project._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(project, key) or getattr(project, key) != value:
                    match = False
                    break
            if match:
                results.append(project)
        return results


# Module-level objects manager
class Objects:
    """Module-level manager for projects."""

    @staticmethod
    def create(name, team_id):
        """Create a new project."""
        return Project(name, team_id)

    @staticmethod
    def get(id):
        """Get a project by ID."""
        return Project._instances[id]

    @staticmethod
    def all():
        """Get all projects."""
        return list(Project._instances.values())

    @staticmethod
    def filter(**kwargs):
        """Filter projects by attributes."""
        results = []
        for project in Project._instances.values():
            match = True
            for key, value in kwargs.items():
                if not hasattr(project, key) or getattr(project, key) != value:
                    match = False
                    break
            if match:
                results.append(project)
        return results


# Attach objects manager to class
Project.objects = Objects
