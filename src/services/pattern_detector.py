"""Pattern detection engine for identifying repetitive workflow sequences."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

from src.config import get_config
from src.logger import get_app_logger
from src.models.action import Action, ActionType
from src.models.pattern import Pattern
from src.database.storage_manager import StorageManager
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class PatternDetector:
    """
    Pattern detection engine that identifies repetitive workflow sequences.
    
    Features:
    - Sliding window algorithm for pattern detection
    - Frequency counting and occurrence tracking
    - Automation feasibility scoring
    - Pattern similarity matching
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Pattern detection settings
        self.window_size = 50  # Last 50 actions
        self.min_pattern_length = 2  # Minimum 2 actions for a pattern
        self.max_pattern_length = 10  # Maximum 10 actions for a pattern
        self.min_frequency = 2  # Pattern must occur at least 2 times
        self.similarity_threshold = 0.8  # 80% similarity for pattern matching
        
        # Storage
        self.storage_manager: Optional[StorageManager] = None
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._patterns_detected = 0
        self._total_actions_analyzed = 0
        
        self.logger.info("Pattern detector initialized")
    
    async def initialize(self) -> None:
        """Initialize pattern detector."""
        self.logger.info("Initializing pattern detector...")
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            self.logger.info("Pattern detector initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pattern detector: {e}")
            raise
    
    async def detect_patterns_in_actions(self, actions: List[Action]) -> List[Pattern]:
        """
        Detect patterns in a sequence of actions using sliding window algorithm.
        
        Args:
            actions: List of actions to analyze
            
        Returns:
            List of detected patterns
        """
        try:
            if len(actions) < self.min_pattern_length * self.min_frequency:
                return []
            
            self._total_actions_analyzed += len(actions)
            
            # Use sliding window to find patterns
            patterns = []
            
            # Extract action sequences of different lengths
            for pattern_length in range(self.min_pattern_length, min(self.max_pattern_length + 1, len(actions) // 2)):
                sequences = self._extract_sequences(actions, pattern_length)
                detected_patterns = self._find_repetitive_sequences(sequences, pattern_length)
                patterns.extend(detected_patterns)
            
            # Remove duplicate and overlapping patterns
            patterns = self._deduplicate_patterns(patterns)
            
            # Calculate automation feasibility
            for pattern in patterns:
                pattern.automation_feasibility = self._calculate_automation_feasibility(pattern)
            
            # Sort by frequency and feasibility
            patterns.sort(key=lambda p: (p.frequency, p.automation_feasibility), reverse=True)
            
            self._patterns_detected += len(patterns)
            
            # Publish pattern detection events
            for pattern in patterns:
                await self._publish_pattern_event(pattern)
            
            self.logger.info(f"Detected {len(patterns)} patterns from {len(actions)} actions")
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error detecting patterns: {e}")
            return []
    
    async def detect_patterns_from_timerange(self, start_time: datetime, 
                                           end_time: datetime) -> List[Pattern]:
        """
        Detect patterns from actions in a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of detected patterns
        """
        try:
            if not self.storage_manager:
                return []
            
            # Get actions from database
            actions = await self.storage_manager.get_actions_by_time_range(start_time, end_time)
            
            if not actions:
                return []
            
            # Detect patterns
            patterns = await self.detect_patterns_in_actions(actions)
            
            # Save patterns to database
            for pattern in patterns:
                await self.storage_manager.save_pattern(pattern)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error detecting patterns from timerange: {e}")
            return []
    
    def _extract_sequences(self, actions: List[Action], length: int) -> List[Tuple[str, ...]]:
        """Extract sequences of specified length from actions."""
        sequences = []
        
        for i in range(len(actions) - length + 1):
            sequence = tuple(
                self._action_to_signature(actions[i + j]) 
                for j in range(length)
            )
            sequences.append(sequence)
        
        return sequences
    
    def _action_to_signature(self, action: Action) -> str:
        """Convert action to a signature for pattern matching."""
        # Create a signature that captures the essence of the action
        # but is flexible enough to match similar actions
        
        signature_parts = [action.type.value]
        
        # Add application context
        if action.application and action.application != "Unknown":
            signature_parts.append(f"app:{action.application}")
        
        # Add target element if specific enough
        if action.target_element and action.target_element != "Unknown":
            # Generalize specific elements (e.g., "Button_123" -> "Button")
            element = self._generalize_element(action.target_element)
            signature_parts.append(f"target:{element}")
        
        # Add input data pattern for type actions
        if action.type == ActionType.TYPE and action.input_data:
            input_pattern = self._generalize_input(action.input_data)
            if input_pattern:
                signature_parts.append(f"input:{input_pattern}")
        
        return "|".join(signature_parts)
    
    def _generalize_element(self, element: str) -> str:
        """Generalize UI element names for pattern matching."""
        element = element.lower()
        
        # Common generalizations
        generalizations = {
            'button': ['btn', 'button'],
            'textfield': ['text', 'input', 'field', 'textbox'],
            'menu': ['menu', 'dropdown'],
            'link': ['link', 'hyperlink'],
            'icon': ['icon', 'image'],
        }
        
        for general, specifics in generalizations.items():
            if any(specific in element for specific in specifics):
                return general
        
        return element
    
    def _generalize_input(self, input_data: str) -> Optional[str]:
        """Generalize input data for pattern matching."""
        if not input_data or len(input_data) > 50:
            return None
        
        input_lower = input_data.lower().strip()
        
        # Detect common input patterns
        if input_lower.isdigit():
            return "number"
        elif '@' in input_lower and '.' in input_lower:
            return "email"
        elif any(word in input_lower for word in ['http', 'www', '.com']):
            return "url"
        elif len(input_lower) < 20 and input_lower.isalpha():
            return "text"
        
        return None
    
    def _find_repetitive_sequences(self, sequences: List[Tuple[str, ...]], 
                                 pattern_length: int) -> List[Pattern]:
        """Find sequences that repeat frequently."""
        # Count sequence occurrences
        sequence_counts = Counter(sequences)
        
        patterns = []
        
        for sequence, count in sequence_counts.items():
            if count >= self.min_frequency:
                # Create pattern
                pattern = Pattern(
                    pattern_type="repetitive_sequence",
                    description=self._create_pattern_description(sequence),
                    actions_involved=list(sequence),
                    frequency=count,
                    confidence=min(1.0, count / len(sequences) * 2),  # Higher frequency = higher confidence
                    automation_potential="medium",  # Will be calculated later
                    first_occurrence=datetime.now(),  # Placeholder
                    last_occurrence=datetime.now()   # Placeholder
                )
                
                patterns.append(pattern)
        
        return patterns
    
    def _create_pattern_description(self, sequence: Tuple[str, ...]) -> str:
        """Create human-readable description for a pattern."""
        descriptions = []
        
        for action_sig in sequence:
            parts = action_sig.split('|')
            action_type = parts[0]
            
            # Extract context
            app = None
            target = None
            input_type = None
            
            for part in parts[1:]:
                if part.startswith('app:'):
                    app = part[4:]
                elif part.startswith('target:'):
                    target = part[7:]
                elif part.startswith('input:'):
                    input_type = part[6:]
            
            # Create description
            desc = self._action_type_to_description(action_type)
            
            if target:
                desc += f" {target}"
            
            if input_type:
                desc += f" ({input_type})"
            
            if app:
                desc += f" in {app}"
            
            descriptions.append(desc)
        
        return " → ".join(descriptions)
    
    def _action_type_to_description(self, action_type: str) -> str:
        """Convert action type to human-readable description."""
        descriptions = {
            'click': 'Click',
            'double_click': 'Double-click',
            'right_click': 'Right-click',
            'type': 'Type',
            'hotkey': 'Press hotkey',
            'navigate': 'Navigate',
            'scroll': 'Scroll',
            'drag_drop': 'Drag and drop',
            'copy': 'Copy',
            'paste': 'Paste',
            'save_file': 'Save file',
            'open_file': 'Open file',
            'open_app': 'Open application',
            'close_app': 'Close application'
        }
        
        return descriptions.get(action_type, action_type.replace('_', ' ').title())
    
    def _deduplicate_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Remove duplicate and overlapping patterns."""
        if not patterns:
            return patterns
        
        # Sort by frequency (highest first)
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        
        unique_patterns = []
        
        for pattern in patterns:
            # Check if this pattern is too similar to existing ones
            is_duplicate = False
            
            for existing in unique_patterns:
                similarity = self._calculate_pattern_similarity(pattern, existing)
                if similarity > self.similarity_threshold:
                    is_duplicate = True
                    # Keep the one with higher frequency
                    if pattern.frequency > existing.frequency:
                        unique_patterns.remove(existing)
                        unique_patterns.append(pattern)
                    break
            
            if not is_duplicate:
                unique_patterns.append(pattern)
        
        return unique_patterns
    
    def _calculate_pattern_similarity(self, pattern1: Pattern, pattern2: Pattern) -> float:
        """Calculate similarity between two patterns."""
        actions1 = set(pattern1.actions_involved)
        actions2 = set(pattern2.actions_involved)
        
        if not actions1 or not actions2:
            return 0.0
        
        intersection = len(actions1.intersection(actions2))
        union = len(actions1.union(actions2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_automation_feasibility(self, pattern: Pattern) -> float:
        """Calculate how feasible it is to automate this pattern."""
        feasibility_score = 0.0
        
        # Base score from frequency
        frequency_score = min(1.0, pattern.frequency / 10.0)  # Max at 10 occurrences
        feasibility_score += frequency_score * 0.4
        
        # Score from action types
        automatable_actions = {
            'click', 'double_click', 'type', 'hotkey', 
            'copy', 'paste', 'save_file', 'open_file'
        }
        
        total_actions = len(pattern.actions_involved)
        automatable_count = 0
        
        for action_sig in pattern.actions_involved:
            action_type = action_sig.split('|')[0]
            if action_type in automatable_actions:
                automatable_count += 1
        
        automation_ratio = automatable_count / total_actions if total_actions > 0 else 0
        feasibility_score += automation_ratio * 0.4
        
        # Score from pattern complexity (simpler = more feasible)
        complexity_score = 1.0 - min(1.0, total_actions / 10.0)  # Penalize very long patterns
        feasibility_score += complexity_score * 0.2
        
        return min(1.0, feasibility_score)
    
    async def _publish_pattern_event(self, pattern: Pattern) -> None:
        """Publish pattern detection event."""
        try:
            event = Event(
                type=EventType.PATTERN_DETECTED,
                timestamp=datetime.now(),
                source="pattern_detector",
                data={
                    "pattern_id": pattern.id,
                    "pattern_type": pattern.pattern_type,
                    "description": pattern.description,
                    "frequency": pattern.frequency,
                    "confidence": pattern.confidence,
                    "automation_feasibility": pattern.automation_feasibility,
                    "actions_count": len(pattern.actions_involved)
                }
            )
            
            await self.event_bus.publish(event)
            
        except Exception as e:
            self.logger.error(f"Error publishing pattern event: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pattern detector statistics."""
        return {
            "patterns_detected": self._patterns_detected,
            "total_actions_analyzed": self._total_actions_analyzed,
            "window_size": self.window_size,
            "min_pattern_length": self.min_pattern_length,
            "max_pattern_length": self.max_pattern_length,
            "min_frequency": self.min_frequency,
            "similarity_threshold": self.similarity_threshold
        }