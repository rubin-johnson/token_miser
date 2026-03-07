"""Anomaly detector service for detecting token usage spikes."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from token_miser.models import TokenUsage, Project, AnomalyAlert


class AnomalyDetector:
    """Detects anomalies in token usage patterns."""

    def __init__(self, team_id: int, sensitivity: float = 1.5):
        """Initialize anomaly detector.
        
        Args:
            team_id: The team ID to analyze
            sensitivity: The sensitivity threshold (default 1.5)
                        current usage must exceed baseline * sensitivity to trigger alert
        """
        self.team_id = team_id
        self.sensitivity = sensitivity

    def _calculate_baseline(self, project_id: int) -> Optional[float]:
        """Calculate baseline token usage for a project.
        
        Calculates the average total tokens (input + output) per day over the last 7 days.
        
        Args:
            project_id: The project ID
            
        Returns:
            The average daily tokens over the last 7 days, or None if insufficient data
        """
        # Get usage from the last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Filter token usage for this project in the last 7 days
        usages = TokenUsage.objects.filter(project_id=project_id)
        recent_usages = [u for u in usages if u.timestamp >= seven_days_ago]
        
        if not recent_usages:
            return None
        
        # Group by day and calculate daily totals
        daily_totals = {}
        for usage in recent_usages:
            # Get the date (without time)
            date_key = usage.timestamp.date()
            if date_key not in daily_totals:
                daily_totals[date_key] = 0
            daily_totals[date_key] += usage.tokens_input + usage.tokens_output
        
        if not daily_totals:
            return None
        
        # Return average daily tokens
        total_tokens = sum(daily_totals.values())
        num_days = len(daily_totals)
        
        return total_tokens / num_days if num_days > 0 else None

    def detect_anomalies(self) -> List[Dict]:
        """Detect anomalies in token usage for the team's projects.
        
        For each project in the team:
        1. Calculate baseline from last 7 days
        2. Get current day's total tokens
        3. If current exceeds baseline * sensitivity, create AnomalyAlert and add to results
        
        Returns:
            List of detected anomalies with keys:
            - project_id
            - project_name
            - baseline_tokens
            - current_tokens
            - spike_magnitude
            - spike_percentage
            - timestamp
        """
        anomalies = []
        
        # Get all projects for this team
        all_projects = Project.objects.filter(team_id=self.team_id)
        
        # Get today's date
        today = datetime.utcnow().date()
        
        for project in all_projects:
            # Calculate baseline
            baseline = self._calculate_baseline(project.id)
            
            # Skip if no baseline data
            if baseline is None or baseline == 0:
                continue
            
            # Get current day's total tokens
            current_tokens = 0
            usages = TokenUsage.objects.filter(project_id=project.id)
            for usage in usages:
                if usage.timestamp.date() == today:
                    current_tokens += usage.tokens_input + usage.tokens_output
            
            # Check if spike detected
            if current_tokens > baseline * self.sensitivity:
                # Calculate spike metrics
                spike_magnitude = current_tokens / baseline
                spike_percentage = ((current_tokens - baseline) / baseline) * 100
                
                # Create AnomalyAlert record
                alert = AnomalyAlert.objects.create(
                    team_id=self.team_id,
                    project_id=project.id,
                    project_name=project.name,
                    baseline_tokens=int(baseline),
                    current_tokens=current_tokens,
                    spike_magnitude=spike_magnitude,
                    spike_percentage=spike_percentage,
                    status="active",
                    timestamp=datetime.utcnow(),
                )
                alert.save()
                
                # Add to results
                anomalies.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "baseline_tokens": int(baseline),
                    "current_tokens": current_tokens,
                    "spike_magnitude": spike_magnitude,
                    "spike_percentage": spike_percentage,
                    "timestamp": datetime.utcnow(),
                })
        
        return anomalies
