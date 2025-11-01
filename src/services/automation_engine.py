"""Automation suggestion engine for generating workflow automation recommendations."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from src.config import get_config
from src.logger import get_app_logger
from src.models.pattern import Pattern
from src.models.workflow import WorkflowSuggestion
from src.database.storage_manager import StorageManager
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class AutomationSuggestionEngine:
    """
    Automation suggestion engine that generates actionable workflow automation recommendations.
    
    Features:
    - Human-readable workflow descriptions
    - Automation feasibility assessment
    - Time-saved estimates
    - Implementation step generation
    - Suggestion ranking and prioritization
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Suggestion settings
        self.min_automation_feasibility = 0.6  # Minimum feasibility to suggest
        self.min_frequency = 3  # Minimum pattern frequency
        self.max_suggestions = 10  # Maximum suggestions to generate
        
        # Storage
        self.storage_manager: Optional[StorageManager] = None
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._suggestions_generated = 0
        self._patterns_analyzed = 0
        
        self.logger.info("Automation suggestion engine initialized")
    
    async def initialize(self) -> None:
        """Initialize automation suggestion engine."""
        self.logger.info("Initializing automation suggestion engine...")
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            self.logger.info("Automation suggestion engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize automation suggestion engine: {e}")
            raise
    
    async def generate_suggestions_from_patterns(self, patterns: List[Pattern]) -> List[WorkflowSuggestion]:
        """
        Generate automation suggestions from detected patterns.
        
        Args:
            patterns: List of detected workflow patterns
            
        Returns:
            List of automation suggestions
        """
        try:
            if not patterns:
                return []
            
            self._patterns_analyzed += len(patterns)
            
            # Filter patterns suitable for automation
            suitable_patterns = self._filter_suitable_patterns(patterns)
            
            if not suitable_patterns:
                self.logger.info("No patterns suitable for automation found")
                return []
            
            # Generate suggestions
            suggestions = []
            
            for pattern in suitable_patterns:
                suggestion = await self._create_suggestion_from_pattern(pattern)
                if suggestion:
                    suggestions.append(suggestion)
            
            # Rank suggestions by priority
            suggestions = self._rank_suggestions(suggestions)
            
            # Limit to max suggestions
            suggestions = suggestions[:self.max_suggestions]
            
            self._suggestions_generated += len(suggestions)
            
            # Save suggestions to database
            if self.storage_manager:
                for suggestion in suggestions:
                    await self.storage_manager.save_workflow_suggestion(suggestion)
            
            # Publish suggestion events
            for suggestion in suggestions:
                await self._publish_suggestion_event(suggestion)
            
            self.logger.info(f"Generated {len(suggestions)} automation suggestions from {len(patterns)} patterns")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def generate_suggestions_from_timerange(self, start_time: datetime, 
                                                end_time: datetime) -> List[WorkflowSuggestion]:
        """
        Generate automation suggestions from patterns in a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of automation suggestions
        """
        try:
            if not self.storage_manager:
                return []
            
            # Get patterns from database
            patterns = await self.storage_manager.get_patterns_by_time_range(start_time, end_time)
            
            if not patterns:
                return []
            
            # Generate suggestions
            suggestions = await self.generate_suggestions_from_patterns(patterns)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating suggestions from timerange: {e}")
            return []
    
    def _filter_suitable_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Filter patterns that are suitable for automation."""
        suitable = []
        
        for pattern in patterns:
            # Check minimum feasibility
            if pattern.automation_feasibility < self.min_automation_feasibility:
                continue
            
            # Check minimum frequency
            if pattern.frequency < self.min_frequency:
                continue
            
            # Check pattern has enough actions
            if len(pattern.actions_involved) < 2:
                continue
            
            suitable.append(pattern)
        
        return suitable
    
    async def _create_suggestion_from_pattern(self, pattern: Pattern) -> Optional[WorkflowSuggestion]:
        """Create an automation suggestion from a pattern."""
        try:
            # Generate title
            title = self._generate_suggestion_title(pattern)
            
            # Generate description
            description = self._generate_suggestion_description(pattern)
            
            # Determine automation type
            automation_type = self._determine_automation_type(pattern)
            
            # Calculate complexity
            complexity = self._calculate_complexity(pattern)
            
            # Estimate time saved
            time_saved_estimate = self._estimate_time_saved(pattern)
            
            # Generate implementation steps
            implementation_steps = self._generate_implementation_steps(pattern, automation_type)
            
            # Calculate confidence
            confidence = self._calculate_suggestion_confidence(pattern)
            
            # Create suggestion
            suggestion = WorkflowSuggestion(
                title=title,
                description=description,
                automation_type=automation_type,
                complexity=complexity,
                confidence=confidence,
                time_saved_estimate=time_saved_estimate,
                implementation_steps=implementation_steps
            )
            
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Error creating suggestion from pattern: {e}")
            return None
    
    def _generate_suggestion_title(self, pattern: Pattern) -> str:
        """Generate a concise title for the automation suggestion."""
        # Extract key action types
        action_types = []
        for action_sig in pattern.actions_involved:
            action_type = action_sig.split('|')[0]
            if action_type not in action_types:
                action_types.append(action_type)
        
        # Create title based on pattern
        if len(action_types) == 1:
            action_name = self._action_type_to_name(action_types[0])
            return f"Automate Repetitive {action_name}"
        elif 'type' in action_types and 'click' in action_types:
            return "Automate Data Entry Workflow"
        elif 'copy' in action_types and 'paste' in action_types:
            return "Automate Copy-Paste Operations"
        elif 'open_file' in action_types or 'save_file' in action_types:
            return "Automate File Management"
        else:
            return f"Automate {len(pattern.actions_involved)}-Step Workflow"
    
    def _generate_suggestion_description(self, pattern: Pattern) -> str:
        """Generate a detailed description of the automation suggestion."""
        frequency = pattern.frequency
        actions_count = len(pattern.actions_involved)
        
        description = f"Detected repetitive workflow: {pattern.description}. "
        description += f"This {actions_count}-step sequence has been performed {frequency} times. "
        
        # Add automation benefits
        if pattern.automation_feasibility > 0.8:
            description += "This workflow is highly suitable for automation and could save significant time. "
        elif pattern.automation_feasibility > 0.6:
            description += "This workflow can be automated with some setup effort. "
        
        # Add time savings
        time_per_execution = self._estimate_time_per_execution(pattern)
        total_time_saved = time_per_execution * frequency
        
        if total_time_saved > 60:  # More than 1 minute
            minutes = int(total_time_saved / 60)
            description += f"Automation could have saved approximately {minutes} minute(s) so far. "
        
        description += "Consider implementing automation for this repetitive task."
        
        return description
    
    def _determine_automation_type(self, pattern: Pattern) -> str:
        """Determine the best automation type for the pattern."""
        action_types = [action_sig.split('|')[0] for action_sig in pattern.actions_involved]
        
        # Check for specific patterns
        if 'type' in action_types and any(t in action_types for t in ['click', 'navigate']):
            return "script"  # Form filling or data entry
        elif 'copy' in action_types and 'paste' in action_types:
            return "macro"  # Copy-paste operations
        elif any(t in action_types for t in ['hotkey', 'save_file', 'open_file']):
            return "shortcut"  # Keyboard shortcuts
        elif len(set(action_types)) == 1:
            return "macro"  # Repetitive single action
        else:
            return "script"  # Complex multi-step workflow
    
    def _calculate_complexity(self, pattern: Pattern) -> str:
        """Calculate the complexity of implementing automation for this pattern."""
        actions_count = len(pattern.actions_involved)
        unique_actions = len(set(action_sig.split('|')[0] for action_sig in pattern.actions_involved))
        
        # Check for complex actions
        complex_actions = {'drag_drop', 'navigate', 'scroll'}
        has_complex_actions = any(
            action_sig.split('|')[0] in complex_actions 
            for action_sig in pattern.actions_involved
        )
        
        # Determine complexity
        if actions_count <= 3 and unique_actions <= 2 and not has_complex_actions:
            return "low"
        elif actions_count <= 6 and unique_actions <= 4:
            return "medium"
        else:
            return "high"
    
    def _estimate_time_saved(self, pattern: Pattern) -> str:
        """Estimate time saved by automating this pattern."""
        time_per_execution = self._estimate_time_per_execution(pattern)
        frequency = pattern.frequency
        
        # Calculate potential savings
        total_seconds = time_per_execution * frequency
        
        if total_seconds < 60:
            return f"{int(total_seconds)} seconds per occurrence"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            return f"{minutes} minute(s) per occurrence"
        else:
            hours = int(total_seconds / 3600)
            return f"{hours} hour(s) per occurrence"
    
    def _estimate_time_per_execution(self, pattern: Pattern) -> float:
        """Estimate time in seconds for one execution of the pattern."""
        base_time_per_action = {
            'click': 2.0,
            'double_click': 2.5,
            'type': 5.0,  # Depends on text length
            'hotkey': 1.5,
            'navigate': 3.0,
            'scroll': 2.0,
            'copy': 1.5,
            'paste': 1.5,
            'save_file': 3.0,
            'open_file': 4.0,
            'drag_drop': 4.0
        }
        
        total_time = 0.0
        
        for action_sig in pattern.actions_involved:
            action_type = action_sig.split('|')[0]
            base_time = base_time_per_action.get(action_type, 2.0)
            
            # Add thinking/transition time
            total_time += base_time + 1.0
        
        return total_time
    
    def _generate_implementation_steps(self, pattern: Pattern, automation_type: str) -> List[str]:
        """Generate implementation steps for the automation."""
        steps = []
        
        if automation_type == "macro":
            steps = [
                "Record the sequence of actions using a macro tool",
                "Test the macro with sample data",
                "Set up keyboard shortcut to trigger the macro",
                "Document the macro for future reference"
            ]
        elif automation_type == "script":
            steps = [
                "Analyze the workflow to identify variable elements",
                "Write automation script using appropriate tools (Python, AutoHotkey, etc.)",
                "Add error handling and validation",
                "Test script with different scenarios",
                "Create user interface for script parameters if needed"
            ]
        elif automation_type == "shortcut":
            steps = [
                "Identify existing keyboard shortcuts for the actions",
                "Create custom shortcut combinations",
                "Test shortcuts in the target application",
                "Document shortcuts for team use"
            ]
        else:
            steps = [
                "Break down the workflow into automatable components",
                "Choose appropriate automation tools",
                "Implement step-by-step automation",
                "Test and refine the automation"
            ]
        
        return steps
    
    def _calculate_suggestion_confidence(self, pattern: Pattern) -> float:
        """Calculate confidence score for the suggestion."""
        # Base confidence from pattern confidence
        confidence = pattern.confidence * 0.4
        
        # Add confidence from automation feasibility
        confidence += pattern.automation_feasibility * 0.3
        
        # Add confidence from frequency
        frequency_score = min(1.0, pattern.frequency / 10.0)
        confidence += frequency_score * 0.3
        
        return min(1.0, confidence)
    
    def _rank_suggestions(self, suggestions: List[WorkflowSuggestion]) -> List[WorkflowSuggestion]:
        """Rank suggestions by priority."""
        def priority_score(suggestion: WorkflowSuggestion) -> float:
            score = 0.0
            
            # Higher confidence = higher priority
            score += suggestion.confidence * 0.4
            
            # Lower complexity = higher priority
            complexity_scores = {"low": 1.0, "medium": 0.7, "high": 0.4}
            score += complexity_scores.get(suggestion.complexity, 0.5) * 0.3
            
            # Time saved consideration
            if "hour" in suggestion.time_saved_estimate:
                score += 0.3
            elif "minute" in suggestion.time_saved_estimate:
                score += 0.2
            else:
                score += 0.1
            
            return score
        
        suggestions.sort(key=priority_score, reverse=True)
        return suggestions
    
    def _action_type_to_name(self, action_type: str) -> str:
        """Convert action type to human-readable name."""
        names = {
            'click': 'Clicking',
            'type': 'Typing',
            'copy': 'Copying',
            'paste': 'Pasting',
            'save_file': 'File Saving',
            'open_file': 'File Opening'
        }
        return names.get(action_type, action_type.replace('_', ' ').title())
    
    async def _publish_suggestion_event(self, suggestion: WorkflowSuggestion) -> None:
        """Publish workflow suggestion event."""
        try:
            event = Event(
                type=EventType.WORKFLOW_SUGGESTION_GENERATED,
                timestamp=datetime.now(),
                source="automation_engine",
                data={
                    "suggestion_id": suggestion.id,
                    "title": suggestion.title,
                    "automation_type": suggestion.automation_type,
                    "complexity": suggestion.complexity,
                    "confidence": suggestion.confidence,
                    "time_saved_estimate": suggestion.time_saved_estimate
                }
            )
            
            await self.event_bus.publish(event)
            
        except Exception as e:
            self.logger.error(f"Error publishing suggestion event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get automation suggestion engine statistics."""
        return {
            "suggestions_generated": self._suggestions_generated,
            "patterns_analyzed": self._patterns_analyzed,
            "min_automation_feasibility": self.min_automation_feasibility,
            "min_frequency": self.min_frequency,
            "max_suggestions": self.max_suggestions
        }