"""Action detection and classification service that analyzes user interactions."""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.services.llm_service import LLMService
from src.models.action import Action, ActionType
from src.models.transcription import Transcription
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class ActionDetector:
    """
    Action detection service that analyzes user interactions by combining:
    - Screen capture data (screenshots)
    - Audio transcription data
    - Computer vision processing
    - LLM-based action interpretation
    
    Generates structured Action objects with confidence scores and automation feasibility.
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Services
        self.storage_manager: Optional[StorageManager] = None
        self.llm_service: Optional[LLMService] = None
        self.vision_processor = None  # Will be imported dynamically if available
        
        # Detection settings
        self.correlation_window_seconds = 10  # Correlate data within 10 seconds
        self.min_confidence_threshold = 0.3  # Minimum confidence for action detection
        self.batch_processing_size = 5  # Process actions in batches
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._actions_detected = 0
        self._high_confidence_actions = 0
        self._automation_feasible_actions = 0
        
        self.logger.info("Action detector initialized")
    
    async def initialize(self) -> None:
        """Initialize action detector and dependencies."""
        self.logger.info("Initializing action detector...")
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            # Initialize LLM service
            self.llm_service = LLMService()
            try:
                await self.llm_service.initialize()
                self.logger.info("LLM service available for action analysis")
            except Exception as e:
                self.logger.warning(f"LLM service not available: {e}")
                self.llm_service = None
            
            # Initialize vision processor (optional)
            try:
                from src.services.vision_processor import VisionProcessor
                self.vision_processor = VisionProcessor()
                if self.vision_processor.is_available():
                    self.logger.info("Vision processor available for screenshot analysis")
                else:
                    self.logger.warning("Vision processor not fully available")
            except ImportError as e:
                self.logger.warning(f"Vision processor not available: {e}")
                self.vision_processor = None
            
            self.logger.info("Action detector initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize action detector: {e}")
            raise
    
    async def detect_action_from_data(self, screenshot_path: Optional[Path], 
                                    transcription: Optional[Transcription],
                                    context: Optional[Dict[str, Any]] = None) -> Optional[Action]:
        """
        Detect and classify a user action from screenshot and transcription data.
        
        Args:
            screenshot_path: Path to screenshot file
            transcription: Audio transcription object
            context: Additional context information
            
        Returns:
            Action object or None if detection fails
        """
        try:
            if not screenshot_path and not transcription:
                self.logger.warning("No data provided for action detection")
                return None
            
            # Prepare analysis context
            analysis_context = self._prepare_analysis_context(screenshot_path, transcription, context)
            
            # Process screenshot if available
            vision_data = None
            if screenshot_path and self.vision_processor:
                try:
                    vision_data = await self.vision_processor.process_screenshot(screenshot_path)
                except Exception as e:
                    self.logger.warning(f"Vision processing failed: {e}")
            
            # Analyze action using LLM if available
            llm_analysis = None
            if self.llm_service and self.llm_service.is_available():
                try:
                    llm_analysis = await self.llm_service.analyze_action(
                        str(screenshot_path) if screenshot_path else "no_screenshot",
                        transcription.text if transcription else "",
                        analysis_context
                    )
                except Exception as e:
                    self.logger.warning(f"LLM analysis failed: {e}")
            
            # Combine analysis results
            action = await self._synthesize_action(
                screenshot_path, transcription, vision_data, llm_analysis, analysis_context
            )
            
            if action and action.confidence >= self.min_confidence_threshold:
                # Save action to database
                if self.storage_manager:
                    await self.storage_manager.save_action(action)
                
                # Update statistics
                self._actions_detected += 1
                if action.confidence >= 0.7:
                    self._high_confidence_actions += 1
                if action.automation_feasible:
                    self._automation_feasible_actions += 1
                
                # Publish action detected event
                event = Event(
                    type=EventType.ACTION_DETECTED,
                    timestamp=action.timestamp,
                    source="action_detector",
                    data={
                        "action_id": action.id,
                        "action_type": action.action_type.value,
                        "description": action.description,
                        "confidence": action.confidence,
                        "automation_feasible": action.automation_feasible,
                        "application": action.application
                    }
                )
                await self.event_bus.publish(event)
                
                self.logger.debug(f"Action detected: {action.action_type.value} - {action.description}")
                return action
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting action: {e}")
            return None
    
    async def detect_actions_from_timerange(self, start_time: datetime, 
                                          end_time: datetime) -> List[Action]:
        """
        Detect actions from all data within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of detected actions
        """
        try:
            if not self.storage_manager:
                return []
            
            # Get transcriptions in time range
            transcriptions = await self.storage_manager.get_transcriptions_by_time_range(start_time, end_time)
            
            # Get screenshots in time range (placeholder - would need screenshot metadata in DB)
            screenshots = await self._get_screenshots_in_timerange(start_time, end_time)
            
            # Correlate and analyze data
            actions = []
            
            # Process transcriptions
            for transcription in transcriptions:
                # Find correlated screenshot
                screenshot_path = self._find_correlated_screenshot(transcription, screenshots)
                
                # Detect action
                action = await self.detect_action_from_data(screenshot_path, transcription)
                if action:
                    actions.append(action)
            
            # Process screenshots without transcriptions
            for screenshot_path in screenshots:
                if not self._screenshot_has_transcription(screenshot_path, transcriptions):
                    action = await self.detect_action_from_data(screenshot_path, None)
                    if action:
                        actions.append(action)
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error detecting actions from timerange: {e}")
            return []
    
    async def analyze_action_sequence(self, actions: List[Action]) -> Dict[str, Any]:
        """
        Analyze a sequence of actions for patterns and insights.
        
        Args:
            actions: List of actions to analyze
            
        Returns:
            Analysis results dictionary
        """
        try:
            if not actions:
                return {"error": "No actions to analyze"}
            
            # Sort actions by timestamp
            sorted_actions = sorted(actions, key=lambda a: a.timestamp)
            
            # Calculate basic statistics
            stats = self._calculate_action_statistics(sorted_actions)
            
            # Detect action patterns
            patterns = self._detect_action_patterns(sorted_actions)
            
            # Calculate automation potential
            automation_analysis = self._analyze_automation_potential(sorted_actions)
            
            return {
                "total_actions": len(sorted_actions),
                "time_span": {
                    "start": sorted_actions[0].timestamp.isoformat(),
                    "end": sorted_actions[-1].timestamp.isoformat(),
                    "duration_minutes": (sorted_actions[-1].timestamp - sorted_actions[0].timestamp).total_seconds() / 60
                },
                "statistics": stats,
                "patterns": patterns,
                "automation_analysis": automation_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing action sequence: {e}")
            return {"error": str(e)}
    
    def _prepare_analysis_context(self, screenshot_path: Optional[Path], 
                                transcription: Optional[Transcription],
                                context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare context for action analysis."""
        analysis_context = {
            "timestamp": datetime.now().isoformat(),
            "has_screenshot": screenshot_path is not None,
            "has_transcription": transcription is not None,
            "window_title": "Unknown",
            "application": "Unknown"
        }
        
        if transcription:
            analysis_context.update({
                "transcription_confidence": transcription.confidence,
                "transcription_duration": transcription.duration,
                "language": transcription.language
            })
        
        if context:
            analysis_context.update(context)
        
        return analysis_context
    
    async def _synthesize_action(self, screenshot_path: Optional[Path],
                                transcription: Optional[Transcription],
                                vision_data: Optional[Dict[str, Any]],
                                llm_analysis: Optional[Dict[str, Any]],
                                context: Dict[str, Any]) -> Optional[Action]:
        """Synthesize action from multiple analysis sources."""
        try:
            # Determine timestamp
            if transcription:
                timestamp = transcription.timestamp
            else:
                timestamp = datetime.now()
            
            # Start with default values
            action_type = ActionType.UNKNOWN
            description = "Unknown action"
            confidence = 0.0
            automation_feasible = False
            automation_complexity = "high"
            application = "Unknown"
            target_element = None
            
            # Use LLM analysis if available (highest priority)
            if llm_analysis:
                action_type = self._parse_action_type(llm_analysis.get("action_type", "other"))
                description = llm_analysis.get("description", description)
                confidence = float(llm_analysis.get("confidence", 0.0))
                automation_feasible = llm_analysis.get("automation_feasible", False)
                automation_complexity = llm_analysis.get("automation_complexity", "high")
                application = llm_analysis.get("application", application)
                target_element = llm_analysis.get("target_element")
            
            # Enhance with vision data if available
            if vision_data and "processing_results" in vision_data:
                # Use vision confidence to adjust overall confidence
                vision_confidence = vision_data.get("confidence", 0.0)
                if vision_confidence > 0:
                    confidence = (confidence + vision_confidence) / 2
                
                # Extract application info from vision data
                window_info = vision_data.get("processing_results", {}).get("window_info", {})
                if window_info.get("application_type", "unknown") != "unknown":
                    application = window_info["application_type"]
                
                # Use OCR text to enhance description if no transcription
                if not transcription:
                    text_data = vision_data.get("processing_results", {}).get("text_extraction", {})
                    if text_data.get("text_found"):
                        ocr_text = text_data.get("full_text", "")[:100]  # First 100 chars
                        if ocr_text:
                            description = f"Interaction with text: {ocr_text}"
                            confidence = max(confidence, 0.4)  # Base confidence for OCR-based detection
            
            # Use transcription data if no LLM analysis
            if not llm_analysis and transcription:
                # Simple heuristic-based action detection from transcription
                text = transcription.text.lower()
                
                if any(word in text for word in ["click", "clicked", "clicking"]):
                    action_type = ActionType.CLICK
                    description = f"Click action: {transcription.text}"
                    confidence = transcription.confidence * 0.8  # Reduce confidence for heuristic
                elif any(word in text for word in ["type", "typing", "enter", "input"]):
                    action_type = ActionType.TYPE
                    description = f"Type action: {transcription.text}"
                    confidence = transcription.confidence * 0.8
                elif any(word in text for word in ["open", "opening", "launch"]):
                    if any(word in text for word in ["file", "document"]):
                        action_type = ActionType.OPEN_FILE
                    else:
                        action_type = ActionType.OPEN_APP
                    description = f"Open action: {transcription.text}"
                    confidence = transcription.confidence * 0.7
                elif any(word in text for word in ["save", "saving"]):
                    action_type = ActionType.SAVE_FILE
                    description = f"Save action: {transcription.text}"
                    confidence = transcription.confidence * 0.7
                else:
                    description = f"Action: {transcription.text}"
                    confidence = transcription.confidence * 0.5
            
            # Create action object
            import uuid
            
            # Get or create a session ID
            session_id = await self._get_or_create_session()
            
            action = Action(
                id=str(uuid.uuid4()),
                session_id=session_id,
                type=action_type,
                timestamp=timestamp,
                application=application,
                window_title="Unknown",  # This should come from window detection
                target_element=target_element or "Unknown",
                input_data=transcription.text if transcription else None,
                screenshot_path=str(screenshot_path) if screenshot_path else "",
                confidence=confidence,
                metadata={
                    "automation_feasible": automation_feasible,
                    "automation_complexity": automation_complexity,
                    "transcription_id": transcription.id if transcription else None,
                    "description": description
                }
            )
            
            return action
            
        except Exception as e:
            self.logger.error(f"Error synthesizing action: {e}")
            return None
    
    def _parse_action_type(self, action_type_str: str) -> ActionType:
        """Parse action type string to ActionType enum."""
        action_type_map = {
            "click": ActionType.CLICK,
            "double_click": ActionType.DOUBLE_CLICK,
            "right_click": ActionType.RIGHT_CLICK,
            "type": ActionType.TYPE,
            "hotkey": ActionType.HOTKEY,
            "navigate": ActionType.NAVIGATE,
            "scroll": ActionType.SCROLL,
            "drag_drop": ActionType.DRAG_DROP,
            "copy": ActionType.COPY,
            "paste": ActionType.PASTE,
            "save": ActionType.SAVE_FILE,
            "save_file": ActionType.SAVE_FILE,
            "open": ActionType.OPEN_FILE,
            "open_file": ActionType.OPEN_FILE,
            "open_app": ActionType.OPEN_APP,
            "close": ActionType.CLOSE_APP,
            "close_app": ActionType.CLOSE_APP,
            "other": ActionType.UNKNOWN,
            "unknown": ActionType.UNKNOWN
        }
        
        return action_type_map.get(action_type_str.lower(), ActionType.UNKNOWN)
    
    async def _get_screenshots_in_timerange(self, start_time: datetime, 
                                          end_time: datetime) -> List[Path]:
        """Get screenshots in time range (placeholder implementation)."""
        # This would query the database or file system for screenshots
        # For now, return empty list as screenshots aren't stored in DB yet
        return []
    
    def _find_correlated_screenshot(self, transcription: Transcription, 
                                  screenshots: List[Path]) -> Optional[Path]:
        """Find screenshot that correlates with transcription by timestamp."""
        if not screenshots:
            return None
        
        # Find screenshot closest in time to transcription
        best_screenshot = None
        min_time_diff = float('inf')
        
        for screenshot_path in screenshots:
            # Extract timestamp from filename (assuming format: screenshot_YYYYMMDD_HHMMSS_microseconds.png)
            try:
                filename = screenshot_path.stem
                if filename.startswith("screenshot_"):
                    timestamp_str = filename[11:]  # Remove "screenshot_" prefix
                    # Parse timestamp (simplified)
                    screenshot_time = datetime.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
                    
                    time_diff = abs((transcription.timestamp - screenshot_time).total_seconds())
                    
                    if time_diff < min_time_diff and time_diff <= self.correlation_window_seconds:
                        min_time_diff = time_diff
                        best_screenshot = screenshot_path
            except Exception:
                continue
        
        return best_screenshot
    
    def _screenshot_has_transcription(self, screenshot_path: Path, 
                                    transcriptions: List[Transcription]) -> bool:
        """Check if screenshot already has a correlated transcription."""
        # Extract timestamp from screenshot filename
        try:
            filename = screenshot_path.stem
            if filename.startswith("screenshot_"):
                timestamp_str = filename[11:]
                screenshot_time = datetime.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
                
                # Check if any transcription is within correlation window
                for transcription in transcriptions:
                    time_diff = abs((transcription.timestamp - screenshot_time).total_seconds())
                    if time_diff <= self.correlation_window_seconds:
                        return True
        except Exception:
            pass
        
        return False
    
    def _calculate_action_statistics(self, actions: List[Action]) -> Dict[str, Any]:
        """Calculate statistics for action sequence."""
        if not actions:
            return {}
        
        # Count by action type
        type_counts = {}
        for action in actions:
            action_type = action.action_type.value
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
        
        # Count by application
        app_counts = {}
        for action in actions:
            app = action.application or "Unknown"
            app_counts[app] = app_counts.get(app, 0) + 1
        
        # Calculate confidence statistics
        confidences = [action.confidence for action in actions]
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence_count = sum(1 for c in confidences if c >= 0.7)
        
        # Calculate automation statistics
        automation_feasible_count = sum(1 for action in actions if action.automation_feasible)
        
        return {
            "action_types": type_counts,
            "applications": app_counts,
            "confidence_stats": {
                "average": avg_confidence,
                "high_confidence_count": high_confidence_count,
                "high_confidence_percentage": (high_confidence_count / len(actions)) * 100
            },
            "automation_stats": {
                "feasible_count": automation_feasible_count,
                "feasible_percentage": (automation_feasible_count / len(actions)) * 100
            }
        }
    
    def _detect_action_patterns(self, actions: List[Action]) -> List[Dict[str, Any]]:
        """Detect patterns in action sequence."""
        patterns = []
        
        if len(actions) < 3:
            return patterns
        
        # Look for repetitive sequences
        for i in range(len(actions) - 2):
            sequence = actions[i:i+3]
            
            # Check if this sequence repeats
            sequence_types = [action.action_type.value for action in sequence]
            
            # Look for the same sequence later
            for j in range(i + 3, len(actions) - 2):
                later_sequence = actions[j:j+3]
                later_types = [action.action_type.value for action in later_sequence]
                
                if sequence_types == later_types:
                    patterns.append({
                        "type": "repetitive_sequence",
                        "sequence": sequence_types,
                        "first_occurrence": i,
                        "second_occurrence": j,
                        "confidence": 0.8
                    })
                    break
        
        return patterns
    
    def _analyze_automation_potential(self, actions: List[Action]) -> Dict[str, Any]:
        """Analyze automation potential for action sequence."""
        if not actions:
            return {}
        
        # Count automatable actions
        automatable_actions = [action for action in actions if action.automation_feasible]
        
        # Analyze complexity
        complexity_counts = {"low": 0, "medium": 0, "high": 0}
        for action in automatable_actions:
            complexity = action.automation_complexity or "high"
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        # Calculate potential time savings (rough estimate)
        estimated_time_per_action = 5  # seconds
        total_time_seconds = len(automatable_actions) * estimated_time_per_action
        
        return {
            "total_actions": len(actions),
            "automatable_actions": len(automatable_actions),
            "automation_percentage": (len(automatable_actions) / len(actions)) * 100,
            "complexity_distribution": complexity_counts,
            "estimated_time_savings": {
                "seconds": total_time_seconds,
                "minutes": total_time_seconds / 60,
                "description": f"Approximately {total_time_seconds // 60} minutes per execution"
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get action detector statistics."""
        return {
            "actions_detected": self._actions_detected,
            "high_confidence_actions": self._high_confidence_actions,
            "automation_feasible_actions": self._automation_feasible_actions,
            "llm_available": self.llm_service.is_available() if self.llm_service else False,
            "vision_available": self.vision_processor.is_available() if self.vision_processor else False,
            "min_confidence_threshold": self.min_confidence_threshold,
            "correlation_window_seconds": self.correlation_window_seconds
        }
    
    async def _get_or_create_session(self) -> str:
        """Get or create a session ID for actions."""
        try:
            if not hasattr(self, '_current_session_id') or not self._current_session_id:
                # Create a test session
                from src.models.session import Session
                session = Session.create_new()
                
                if self.storage_manager:
                    await self.storage_manager.save_session(session)
                
                self._current_session_id = session.id
                self.logger.debug(f"Created session for action detection: {session.id}")
            
            return self._current_session_id
            
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            # Return a fallback session ID
            return "test_session"
    
    def is_available(self) -> bool:
        """Check if action detector is available."""
        return (self.storage_manager is not None and 
                (self.llm_service is not None or self.vision_processor is not None))