"""Workflow analyzer service that processes captured data to detect patterns and generate suggestions."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.services.llm_service import LLMService
from src.services.action_detector import ActionDetector
from src.models.action import Action
from src.models.pattern import Pattern
from src.models.workflow import WorkflowSuggestion
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class WorkflowAnalyzer:
    """
    Workflow analyzer that processes captured screen and audio data to:
    - Detect user actions using LLM analysis
    - Identify repetitive patterns
    - Generate automation suggestions
    - Store analysis results in database
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Services
        self.storage_manager: Optional[StorageManager] = None
        self.llm_service: Optional[LLMService] = None
        self.action_detector: Optional[ActionDetector] = None
        
        # Analysis state
        self._running = False
        self._analysis_task: Optional[asyncio.Task] = None
        self._last_analysis_time: Optional[datetime] = None
        
        # Analysis settings
        self.analysis_interval = 30  # Analyze every 30 seconds
        self.action_batch_size = 10  # Process 10 actions at a time
        self.pattern_window_size = 50  # Look at last 50 actions for patterns
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._actions_analyzed = 0
        self._patterns_detected = 0
        self._suggestions_generated = 0
        
        self.logger.info("Workflow analyzer initialized")
    
    async def initialize(self) -> None:
        """Initialize workflow analyzer and dependencies."""
        self.logger.info("Initializing workflow analyzer...")
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            # Initialize LLM service
            self.llm_service = LLMService()
            await self.llm_service.initialize()
            
            # Initialize action detector
            self.action_detector = ActionDetector()
            await self.action_detector.initialize()
            
            self.logger.info("Workflow analyzer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow analyzer: {e}")
            raise
    
    async def start(self) -> None:
        """Start workflow analysis."""
        if self._running:
            self.logger.warning("Workflow analyzer already running")
            return
        
        if not self.llm_service or not self.llm_service.is_available():
            self.logger.warning("LLM service not available, workflow analysis disabled")
            return
        
        self.logger.info("Starting workflow analyzer")
        self._running = True
        self._last_analysis_time = datetime.now()
        
        # Start analysis loop
        self._analysis_task = asyncio.create_task(self._analysis_loop())
        
        # Publish service started event
        event = Event(
            type=EventType.SERVICE_STARTED,
            timestamp=datetime.now(),
            source="workflow_analyzer",
            data={"service_name": "workflow_analyzer"}
        )
        await self.event_bus.publish(event)
        
        self.logger.info("Workflow analyzer started")
    
    async def stop(self) -> None:
        """Stop workflow analysis."""
        if not self._running:
            return
        
        self.logger.info("Stopping workflow analyzer")
        self._running = False
        
        # Stop analysis task
        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass
        
        # Publish service stopped event
        event = Event(
            type=EventType.SERVICE_STOPPED,
            timestamp=datetime.now(),
            source="workflow_analyzer",
            data={
                "service_name": "workflow_analyzer",
                "actions_analyzed": self._actions_analyzed,
                "patterns_detected": self._patterns_detected,
                "suggestions_generated": self._suggestions_generated
            }
        )
        await self.event_bus.publish(event)
        
        self.logger.info("Workflow analyzer stopped")
    
    async def analyze_recent_activity(self, minutes: int = 5) -> Dict[str, Any]:
        """
        Analyze recent activity and return results.
        
        Args:
            minutes: Number of minutes of recent activity to analyze
            
        Returns:
            Dictionary with analysis results
        """
        try:
            if not self.storage_manager or not self.llm_service:
                return {"error": "Services not initialized"}
            
            # Get recent data
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes)
            
            # Get screenshots and transcriptions
            screenshots = await self._get_recent_screenshots(start_time, end_time)
            transcriptions = await self.storage_manager.get_transcriptions_by_time_range(start_time, end_time)
            
            # Analyze actions
            actions = await self._analyze_actions_from_data(screenshots, transcriptions)
            
            # Detect patterns
            patterns = []
            if len(actions) >= 3:
                patterns = await self.llm_service.detect_workflow_patterns(actions)
            
            # Generate suggestions
            suggestions = []
            if patterns:
                suggestions = await self.llm_service.generate_automation_suggestions(patterns)
            
            return {
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_minutes": minutes
                },
                "data_captured": {
                    "screenshots": len(screenshots),
                    "transcriptions": len(transcriptions)
                },
                "analysis_results": {
                    "actions_detected": len(actions),
                    "patterns_found": len(patterns),
                    "suggestions_generated": len(suggestions)
                },
                "actions": actions,
                "patterns": patterns,
                "suggestions": suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing recent activity: {e}")
            return {"error": str(e)}
    
    async def _analysis_loop(self) -> None:
        """Main analysis loop."""
        self.logger.info("Workflow analysis loop started")
        
        try:
            while self._running:
                try:
                    # Wait for analysis interval
                    await asyncio.sleep(self.analysis_interval)
                    
                    if not self._running:
                        break
                    
                    # Perform analysis
                    await self._perform_analysis()
                    
                except Exception as e:
                    self.logger.error(f"Error in analysis loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            self.logger.error(f"Fatal error in analysis loop: {e}")
        
        self.logger.info("Workflow analysis loop finished")
    
    async def _perform_analysis(self) -> None:
        """Perform workflow analysis on recent data."""
        try:
            current_time = datetime.now()
            
            # Analyze data from last analysis time
            if self._last_analysis_time:
                start_time = self._last_analysis_time
            else:
                start_time = current_time - timedelta(minutes=5)  # Default to last 5 minutes
            
            # Get recent data
            screenshots = await self._get_recent_screenshots(start_time, current_time)
            transcriptions = await self.storage_manager.get_transcriptions_by_time_range(start_time, current_time)
            
            if not screenshots and not transcriptions:
                self.logger.debug("No new data to analyze")
                self._last_analysis_time = current_time
                return
            
            self.logger.info(f"Analyzing {len(screenshots)} screenshots and {len(transcriptions)} transcriptions")
            
            # Analyze actions
            new_actions = await self._analyze_actions_from_data(screenshots, transcriptions)
            
            if new_actions:
                # Save actions to database
                for action in new_actions:
                    await self.storage_manager.save_action(action)
                
                self._actions_analyzed += len(new_actions)
                
                # Get recent actions for pattern detection
                all_recent_actions = await self._get_recent_actions_for_analysis()
                
                # Detect patterns
                if len(all_recent_actions) >= 3:
                    patterns = await self.llm_service.detect_workflow_patterns(
                        all_recent_actions, self.pattern_window_size
                    )
                    
                    if patterns:
                        # Save patterns to database
                        for pattern_data in patterns:
                            pattern = self._create_pattern_from_data(pattern_data)
                            await self.storage_manager.save_pattern(pattern)
                        
                        self._patterns_detected += len(patterns)
                        
                        # Generate suggestions
                        suggestions = await self.llm_service.generate_automation_suggestions(patterns)
                        
                        if suggestions:
                            # Save suggestions to database
                            for suggestion_data in suggestions:
                                suggestion = self._create_suggestion_from_data(suggestion_data)
                                await self.storage_manager.save_workflow_suggestion(suggestion)
                            
                            self._suggestions_generated += len(suggestions)
                            
                            # Publish workflow suggestion event
                            event = Event(
                                type=EventType.WORKFLOW_SUGGESTION_GENERATED,
                                timestamp=current_time,
                                source="workflow_analyzer",
                                data={
                                    "suggestions_count": len(suggestions),
                                    "patterns_analyzed": len(patterns),
                                    "actions_processed": len(new_actions)
                                }
                            )
                            await self.event_bus.publish(event)
                            
                            self.logger.info(f"Generated {len(suggestions)} workflow suggestions")
            
            self._last_analysis_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error performing analysis: {e}")
    
    async def _get_recent_screenshots(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get recent screenshots from the file system."""
        try:
            # This is a simplified version - in a real implementation,
            # you'd query the database or file system for screenshots
            # For now, return empty list as screenshots aren't stored in DB yet
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting recent screenshots: {e}")
            return []
    
    async def _analyze_actions_from_data(self, screenshots: List[Dict[str, Any]], 
                                       transcriptions: List) -> List[Dict[str, Any]]:
        """Analyze actions from screenshots and transcriptions using action detector."""
        actions = []
        
        try:
            if not self.action_detector:
                self.logger.warning("Action detector not available")
                return []
            
            # Use action detector to analyze transcriptions
            for transcription in transcriptions:
                # Find closest screenshot (placeholder)
                screenshot_path = None  # Would be determined by correlation logic
                
                # Detect action
                action = await self.action_detector.detect_action_from_data(
                    screenshot_path, transcription
                )
                
                if action:
                    # Convert Action object to dict for LLM processing
                    action_data = {
                        "action_type": action.action_type.value,
                        "description": action.description,
                        "timestamp": action.timestamp.isoformat(),
                        "confidence": action.confidence,
                        "application": action.application,
                        "automation_feasible": action.automation_feasible,
                        "automation_complexity": action.automation_complexity,
                        "transcription_id": action.transcription_id
                    }
                    actions.append(action_data)
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error analyzing actions from data: {e}")
            return []
    
    async def _get_recent_actions_for_analysis(self) -> List[Dict[str, Any]]:
        """Get recent actions from database for pattern analysis."""
        try:
            # Get recent actions from database
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)  # Last hour
            
            actions = await self.storage_manager.get_actions_by_time_range(start_time, end_time)
            
            # Convert to dict format for LLM analysis
            action_dicts = []
            for action in actions:
                action_dict = action.to_dict()
                action_dicts.append(action_dict)
            
            return action_dicts
            
        except Exception as e:
            self.logger.error(f"Error getting recent actions: {e}")
            return []
    
    def _create_pattern_from_data(self, pattern_data: Dict[str, Any]) -> Pattern:
        """Create Pattern model from LLM analysis data."""
        return Pattern(
            pattern_type=pattern_data.get("pattern_type", "unknown"),
            description=pattern_data.get("description", ""),
            actions_involved=pattern_data.get("actions_involved", []),
            frequency=int(pattern_data.get("frequency", 1)),
            confidence=float(pattern_data.get("confidence", 0.0)),
            automation_potential=pattern_data.get("automation_potential", "low"),
            first_occurrence=datetime.now(),
            last_occurrence=datetime.now()
        )
    
    def _create_suggestion_from_data(self, suggestion_data: Dict[str, Any]) -> WorkflowSuggestion:
        """Create WorkflowSuggestion model from LLM analysis data."""
        return WorkflowSuggestion(
            title=suggestion_data.get("title", "Automation Suggestion"),
            description=suggestion_data.get("description", ""),
            automation_type=suggestion_data.get("automation_type", "macro"),
            complexity=suggestion_data.get("complexity", "medium"),
            confidence=float(suggestion_data.get("confidence", 0.0)),
            time_saved_estimate=suggestion_data.get("time_saved_estimate", "Unknown"),
            implementation_steps=suggestion_data.get("implementation_steps", [])
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow analyzer statistics."""
        return {
            "running": self._running,
            "llm_available": self.llm_service.is_available() if self.llm_service else False,
            "actions_analyzed": self._actions_analyzed,
            "patterns_detected": self._patterns_detected,
            "suggestions_generated": self._suggestions_generated,
            "last_analysis_time": self._last_analysis_time.isoformat() if self._last_analysis_time else None,
            "analysis_interval": self.analysis_interval
        }
    
    def is_running(self) -> bool:
        """Check if workflow analyzer is running."""
        return self._running