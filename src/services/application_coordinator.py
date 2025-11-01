"""Central application coordinator for managing all services."""

import asyncio
import signal
import sys
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from src.config import get_config
from src.logger import get_app_logger
from src.services.screen_capture import ScreenCaptureService
from src.services.hotkey_manager import HotkeyManager
from src.services.audio_transcription import AudioTranscriptionService
from src.services.workflow_analyzer import WorkflowAnalyzer
from src.database.storage_manager import StorageManager
from src.services.event_system import (
    get_event_bus, Event, EventType, 
    create_screenshot_event, create_video_segment_event, 
    create_service_event, create_session_event
)
from src.models.session import Session, SessionStatus
from src.services.backend_event_bridge import BackendEventBridge
from src.services.command_dispatcher import CommandDispatcher

if TYPE_CHECKING:
    from src.interfaces.gui import GuiPort

class ApplicationCoordinator:
    """
    Central coordinator that manages all application services.
    
    Responsibilities:
    - Service lifecycle management (start/stop/restart)
    - Inter-service communication and event handling
    - Graceful shutdown and error recovery
    - Session management
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Service instances
        self.screen_capture: Optional[ScreenCaptureService] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.audio_transcription: Optional[AudioTranscriptionService] = None
        self.workflow_analyzer: Optional[WorkflowAnalyzer] = None
        self.storage_manager: Optional[StorageManager] = None
        self.automation_executor: Optional['AutomationExecutor'] = None
        
        # Communication layer
        self.backend_event_bridge: Optional[BackendEventBridge] = None
        self.command_dispatcher: Optional[CommandDispatcher] = None
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Application state
        self._running = False
        self._current_session: Optional[Session] = None
        self._services_started = False
        self._shutdown_event = asyncio.Event()
        
        # Optional GUI port (set by UI layer)
        self.gui_port: Optional['GuiPort'] = None
        
        # Service health monitoring
        self._service_health: Dict[str, bool] = {}
        self._restart_counts: Dict[str, int] = {}
        self._max_restarts = 3
        
        # Set up event subscriptions
        self._setup_event_subscriptions()
        
        self.logger.info("Application coordinator initialized")

    def set_gui_port(self, gui_port: 'GuiPort') -> None:
        """Connect a GUI adapter implementing GuiPort for UI updates/callbacks."""
        self.gui_port = gui_port
        
        # Register GUI client with backend event bridge if available
        if self.backend_event_bridge:
            self.backend_event_bridge.register_gui_client(gui_port)
    
    async def start(self) -> None:
        """Start all application services."""
        if self._running:
            self.logger.warning("Application coordinator already running")
            return
        
        self.logger.info("Starting AGI Assistant application")
        self._running = True
        
        try:
            # Initialize storage first
            await self._initialize_storage()
            
            # Create new session
            await self._create_new_session()
            
            # Initialize services
            await self._initialize_services()
            
            # Start services
            await self._start_services()
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("Application started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop all application services gracefully."""
        if not self._running:
            return
        
        self.logger.info("Stopping AGI Assistant application")
        self._running = False
        
        try:
            # Stop services
            await self._stop_services()
            
            # Complete current session
            await self._complete_current_session()
            
            # Close storage
            if self.storage_manager:
                await self.storage_manager.close()
            
            # Signal shutdown complete
            self._shutdown_event.set()
            
            self.logger.info("Application stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    async def wait_for_shutdown(self) -> None:
        """Wait for application shutdown."""
        await self._shutdown_event.wait()
    
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
    
    def get_current_session(self) -> Optional[Session]:
        """Get current active session."""
        return self._current_session
    
    def get_service_health(self) -> Dict[str, bool]:
        """Get health status of all services."""
        return self._service_health.copy()
    
    async def handle_gui_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle command from GUI.
        
        Args:
            command: Command name
            params: Command parameters
            
        Returns:
            Dictionary with command result
        """
        if not self.command_dispatcher:
            return {
                'success': False,
                'error': 'Command dispatcher not initialized'
            }
        
        return await self.command_dispatcher.dispatch(command, params)
    
    async def get_workflow_analysis(self, minutes: int = 5) -> Dict[str, Any]:
        """Get recent workflow analysis results."""
        if self.workflow_analyzer:
            return await self.workflow_analyzer.analyze_recent_activity(minutes)
        else:
            return {"error": "Workflow analyzer not available"}
    
    async def pause_capture(self) -> None:
        """Pause screen capture."""
        if self.screen_capture:
            self.screen_capture.pause()
            
            # Publish pause event
            event = Event(
                type=EventType.CAPTURE_PAUSED,
                timestamp=datetime.now(),
                source="application_coordinator",
                data={"session_id": self._current_session.id if self._current_session else None}
            )
            await self.event_bus.publish(event)
            
            self.logger.info("Capture paused by user")
    
    async def resume_capture(self) -> None:
        """Resume screen capture."""
        if self.screen_capture:
            self.screen_capture.resume()
            
            # Publish resume event
            event = Event(
                type=EventType.CAPTURE_RESUMED,
                timestamp=datetime.now(),
                source="application_coordinator",
                data={"session_id": self._current_session.id if self._current_session else None}
            )
            await self.event_bus.publish(event)
            
            self.logger.info("Capture resumed by user")
    
    async def toggle_capture(self) -> None:
        """Toggle capture pause/resume state."""
        if self.screen_capture:
            status = self.screen_capture.get_current_status()
            if status.is_paused:
                await self.resume_capture()
            else:
                await self.pause_capture()
    
    async def trigger_emergency_stop(self) -> None:
        """
        Trigger emergency stop for all automations.
        
        This is called by the emergency stop hotkey (Ctrl+Shift+Esc)
        or the emergency stop button in the UI.
        """
        self.logger.warning("Emergency stop triggered via coordinator")
        
        if self.automation_executor:
            await self.automation_executor.trigger_emergency_stop()
            self.logger.info("Emergency stop executed successfully")
        else:
            self.logger.warning("Automation executor not available for emergency stop")
    
    async def _initialize_storage(self) -> None:
        """Initialize storage manager."""
        self.logger.info("Initializing storage manager")
        
        self.storage_manager = StorageManager()
        await self.storage_manager.initialize()
        
        self._service_health['storage'] = True
        self.logger.info("Storage manager initialized")
    
    async def _create_new_session(self) -> None:
        """Create a new capture session."""
        self.logger.info("Creating new session")
        
        session = Session.create_new()
        await self.storage_manager.save_session(session)
        
        self._current_session = session
        
        # Publish session created event
        event = create_session_event(
            EventType.SESSION_CREATED,
            source="application_coordinator",
            session_id=session.id,
            start_time=session.start_time.isoformat()
        )
        await self.event_bus.publish(event)
        
        self.logger.info(f"New session created: {session.id}")
    
    async def _initialize_services(self) -> None:
        """Initialize all services."""
        self.logger.info("Initializing services")
        
        # Initialize communication layer first
        self.backend_event_bridge = BackendEventBridge(self)
        self.command_dispatcher = CommandDispatcher(self)
        
        # Register GUI client if already set
        if self.gui_port and self.backend_event_bridge:
            self.backend_event_bridge.register_gui_client(self.gui_port)
        
        # Initialize screen capture service
        self.screen_capture = ScreenCaptureService()
        
        # Initialize audio transcription service
        self.audio_transcription = AudioTranscriptionService()
        
        # Initialize workflow analyzer
        self.workflow_analyzer = WorkflowAnalyzer()
        
        # Initialize hotkey manager
        self.hotkey_manager = HotkeyManager()
        self.hotkey_manager.set_pause_callback(self.toggle_capture)
        
        # Initialize automation executor
        from src.services.automation_executor import AutomationExecutor
        self.automation_executor = AutomationExecutor()
        await self.automation_executor.initialize(self.storage_manager)
        
        # Set emergency stop callback for hotkey
        self.hotkey_manager.set_emergency_stop_callback(self.trigger_emergency_stop)
        
        self.logger.info("Services initialized")
    
    async def _start_services(self) -> None:
        """Start all services."""
        self.logger.info("Starting services")
        
        try:
            # Start communication layer first
            if self.backend_event_bridge:
                await self.backend_event_bridge.start()
                self._service_health['backend_event_bridge'] = True
                self.logger.info("Backend event bridge started")
            
            # Start screen capture
            if self.screen_capture:
                await self.screen_capture.start()
                self._service_health['screen_capture'] = True
                self.logger.info("Screen capture service started")
            
            # Start audio transcription
            if self.audio_transcription:
                await self.audio_transcription.start()
                self._service_health['audio_transcription'] = True
                self.logger.info("Audio transcription service started")
            
            # Start workflow analyzer
            if self.workflow_analyzer:
                try:
                    await self.workflow_analyzer.initialize()
                    await self.workflow_analyzer.start()
                    self._service_health['workflow_analyzer'] = True
                    self.logger.info("Workflow analyzer started")
                except Exception as e:
                    self.logger.warning(f"Workflow analyzer failed to start: {e}")
                    self._service_health['workflow_analyzer'] = False
            
            # Start hotkey manager
            if self.hotkey_manager:
                self.hotkey_manager.start()
                self._service_health['hotkey_manager'] = True
                self.logger.info("Hotkey manager started")
            
            # Start automation executor
            if self.automation_executor:
                await self.automation_executor.start()
                self._service_health['automation_executor'] = True
                self.logger.info("Automation executor started")
            
            self._services_started = True
            
            # Start service monitoring
            asyncio.create_task(self._monitor_services())
            
            # Start GUI update task
            asyncio.create_task(self._update_gui_periodically())
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            self._service_health = {k: False for k in self._service_health}
            raise
    
    async def _stop_services(self) -> None:
        """Stop all services."""
        self.logger.info("Stopping services")
        
        # Stop screen capture
        if self.screen_capture:
            try:
                await self.screen_capture.stop()
                self.logger.info("Screen capture service stopped")
            except Exception as e:
                self.logger.error(f"Error stopping screen capture: {e}")
        
        # Stop audio transcription
        if self.audio_transcription:
            try:
                await self.audio_transcription.stop()
                self.logger.info("Audio transcription service stopped")
            except Exception as e:
                self.logger.error(f"Error stopping audio transcription: {e}")
        
        # Stop workflow analyzer
        if self.workflow_analyzer:
            try:
                await self.workflow_analyzer.stop()
                self.logger.info("Workflow analyzer stopped")
            except Exception as e:
                self.logger.error(f"Error stopping workflow analyzer: {e}")
        
        # Stop hotkey manager
        if self.hotkey_manager:
            try:
                self.hotkey_manager.stop()
                self.logger.info("Hotkey manager stopped")
            except Exception as e:
                self.logger.error(f"Error stopping hotkey manager: {e}")
        
        # Stop automation executor
        if self.automation_executor:
            try:
                await self.automation_executor.stop()
                self.logger.info("Automation executor stopped")
            except Exception as e:
                self.logger.error(f"Error stopping automation executor: {e}")
        
        # Stop communication layer last
        if self.backend_event_bridge:
            try:
                await self.backend_event_bridge.stop()
                self.logger.info("Backend event bridge stopped")
            except Exception as e:
                self.logger.error(f"Error stopping backend event bridge: {e}")
        
        self._services_started = False
        self._service_health = {}
    
    async def _complete_current_session(self) -> None:
        """Complete and save current session."""
        if self._current_session and self.storage_manager:
            try:
                # Update session end time and status
                self._current_session.end_time = datetime.now()
                self._current_session.status = SessionStatus.COMPLETED
                
                # Calculate final statistics
                if self.screen_capture:
                    status = self.screen_capture.get_current_status()
                    self._current_session.capture_count = status.frames_captured
                
                # Save final session state
                await self.storage_manager.save_session(self._current_session)
                
                # Publish session completed event
                event = create_session_event(
                    EventType.SESSION_COMPLETED,
                    source="application_coordinator",
                    session_id=self._current_session.id,
                    end_time=self._current_session.end_time.isoformat(),
                    capture_count=self._current_session.capture_count
                )
                await self.event_bus.publish(event)
                
                self.logger.info(f"Session completed: {self._current_session.id}")
                
            except Exception as e:
                self.logger.error(f"Error completing session: {e}")
    
    async def _monitor_services(self) -> None:
        """Monitor service health and restart if needed."""
        while self._running and self._services_started:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Check screen capture health
                if self.screen_capture and not self.screen_capture._running:
                    self.logger.warning("Screen capture service appears to have stopped")
                    await self._restart_service('screen_capture')
                
                # Add more health checks as needed
                
            except Exception as e:
                self.logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _update_gui_periodically(self) -> None:
        """Periodically update GUI with latest data."""
        while self._running and self._services_started:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                if not self.gui_port or not self.storage_manager:
                    continue
                
                # Update session info
                if self._current_session:
                    self.gui_port.update_session_info(self._current_session)
                
                # Update patterns (refresh every 30 seconds)
                if hasattr(self, '_gui_update_counter'):
                    self._gui_update_counter += 1
                else:
                    self._gui_update_counter = 0
                
                if self._gui_update_counter % 6 == 0:  # Every 30 seconds
                    try:
                        # Refresh patterns list
                        patterns = await self.storage_manager.get_all_patterns()
                        if patterns:
                            self.gui_port.set_patterns(patterns[:50])  # Limit to 50 most recent
                        
                        # Refresh recent actions for current session
                        if self._current_session:
                            actions = await self.storage_manager.get_actions_by_session(
                                self._current_session.id
                            )
                            if actions:
                                # Add most recent actions (avoid duplicates by checking existing list)
                                self.gui_port.add_actions_to_feed(actions[-10:])  # Last 10 actions
                    except Exception as e:
                        self.logger.debug(f"Could not update GUI data: {e}")
                
            except Exception as e:
                self.logger.debug(f"Error in GUI update task: {e}")
                await asyncio.sleep(5)
    
    async def _restart_service(self, service_name: str) -> None:
        """Restart a specific service."""
        restart_count = self._restart_counts.get(service_name, 0)
        
        if restart_count >= self._max_restarts:
            self.logger.error(f"Max restarts exceeded for {service_name}, giving up")
            self._service_health[service_name] = False
            return
        
        self.logger.info(f"Attempting to restart {service_name} (attempt {restart_count + 1})")
        
        try:
            if service_name == 'screen_capture' and self.screen_capture:
                await self.screen_capture.stop()
                await asyncio.sleep(2)
                await self.screen_capture.start()
                self._service_health[service_name] = True
                
            elif service_name == 'hotkey_manager' and self.hotkey_manager:
                self.hotkey_manager.stop()
                await asyncio.sleep(1)
                self.hotkey_manager.start()
                self._service_health[service_name] = True
            
            self._restart_counts[service_name] = restart_count + 1
            self.logger.info(f"Successfully restarted {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to restart {service_name}: {e}")
            self._service_health[service_name] = False
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for coordination."""
        # Subscribe to capture events
        capture_queue = self.event_bus.get_queue('capture_events')
        if capture_queue:
            capture_queue.subscribe(self._handle_capture_event)
        
        # Subscribe to audio events
        audio_queue = self.event_bus.get_queue('audio_events')
        if audio_queue:
            audio_queue.subscribe(self._handle_audio_event)
        
        # Subscribe to analysis events
        analysis_queue = self.event_bus.get_queue('analysis_events')
        if analysis_queue:
            analysis_queue.subscribe(self._handle_analysis_event)
        
        # Subscribe to storage events
        storage_queue = self.event_bus.get_queue('storage_events')
        if storage_queue:
            storage_queue.subscribe(self._handle_storage_event)
        
        # Subscribe to system events
        system_queue = self.event_bus.get_queue('system_events')
        if system_queue:
            system_queue.subscribe(self._handle_system_event)
    
    async def _handle_capture_event(self, event: Event) -> None:
        """Handle capture-related events."""
        try:
            if event.type == EventType.SCREENSHOT_CAPTURED:
                await self._on_screenshot_captured(event)
            elif event.type == EventType.VIDEO_SEGMENT_COMPLETE:
                await self._on_video_segment_complete(event)
            elif event.type == EventType.CAPTURE_PAUSED:
                self.logger.info("Capture paused")
            elif event.type == EventType.CAPTURE_RESUMED:
                self.logger.info("Capture resumed")
                
        except Exception as e:
            self.logger.error(f"Error handling capture event: {e}")
    
    async def _handle_audio_event(self, event: Event) -> None:
        """Handle audio-related events."""
        try:
            if event.type == EventType.AUDIO_CAPTURE_STARTED:
                self.logger.info("Audio capture started")
            elif event.type == EventType.AUDIO_CAPTURE_STOPPED:
                chunks_captured = event.data.get('chunks_captured', 0)
                chunks_with_speech = event.data.get('chunks_with_speech', 0)
                self.logger.info(f"Audio capture stopped - {chunks_captured} chunks, {chunks_with_speech} with speech")
            elif event.type == EventType.AUDIO_TRANSCRIBED:
                transcription = event.data.get('transcription', '')
                self.logger.debug(f"Audio transcribed: {transcription}")
                
        except Exception as e:
            self.logger.error(f"Error handling audio event: {e}")
    
    async def _handle_analysis_event(self, event: Event) -> None:
        """Handle workflow analysis events."""
        try:
            if event.type == EventType.ACTION_DETECTED:
                action_type = event.data.get('action_type', 'unknown')
                self.logger.debug(f"Action detected: {action_type}")
                
                # Update GUI if available
                if self.gui_port:
                    try:
                        # Create action-like object from event data for GUI display
                        # Event data contains: action_id, action_type, description, confidence, automation_feasible, application
                        action_data = {
                            'id': event.data.get('action_id', ''),
                            'timestamp': event.timestamp,
                            'type': event.data.get('action_type', 'unknown'),
                            'application': event.data.get('application', 'Unknown'),
                            'description': event.data.get('description', ''),
                            'confidence': event.data.get('confidence', 0.0),
                        }
                        # Use a simple object-like structure
                        class ActionDisplay:
                            def __init__(self, data):
                                self.id = data.get('id', '')
                                self.timestamp = data.get('timestamp')
                                self.type = type('ActionType', (), {'value': data.get('type', 'unknown')})()
                                self.application = data.get('application', 'Unknown')
                                self.description = data.get('description', '')
                                self.confidence = data.get('confidence', 0.0)
                        
                        action_display = ActionDisplay(action_data)
                        self.gui_port.add_action_to_feed(action_display)
                    except Exception as e:
                        self.logger.debug(f"Could not update GUI with action: {e}")
                        
            elif event.type == EventType.PATTERN_DETECTED:
                pattern_type = event.data.get('pattern_type', 'unknown')
                self.logger.info(f"Pattern detected: {pattern_type}")
                
                # Update GUI if available
                if self.gui_port:
                    try:
                        # Refresh all patterns (simpler than trying to get single pattern)
                        if self.storage_manager:
                            patterns = await self.storage_manager.get_all_patterns()
                            if patterns:
                                self.gui_port.set_patterns(patterns[:50])  # Limit to 50
                    except Exception as e:
                        self.logger.debug(f"Could not update GUI with pattern: {e}")
                        
            elif event.type == EventType.WORKFLOW_SUGGESTION_GENERATED:
                suggestions_count = event.data.get('suggestions_count', 0)
                self.logger.info(f"Generated {suggestions_count} workflow suggestions")
                
        except Exception as e:
            self.logger.error(f"Error handling analysis event: {e}")
    
    async def _handle_storage_event(self, event: Event) -> None:
        """Handle storage-related events."""
        try:
            if event.type == EventType.SESSION_CREATED:
                self.logger.info(f"Session created: {event.data.get('session_id')}")
            elif event.type == EventType.SESSION_COMPLETED:
                self.logger.info(f"Session completed: {event.data.get('session_id')}")
                
        except Exception as e:
            self.logger.error(f"Error handling storage event: {e}")
    
    async def _handle_system_event(self, event: Event) -> None:
        """Handle system-related events."""
        try:
            if event.type == EventType.SERVICE_ERROR:
                service_name = event.data.get('service_name')
                self.logger.warning(f"Service error reported: {service_name}")
                await self._restart_service(service_name)
                
        except Exception as e:
            self.logger.error(f"Error handling system event: {e}")
    
    async def _on_screenshot_captured(self, event: Event) -> None:
        """Handle screenshot captured event."""
        try:
            # Update session statistics
            if self._current_session:
                self._current_session.capture_count += 1
                
                # Save session periodically (every 10 captures)
                if self._current_session.capture_count % 10 == 0:
                    await self.storage_manager.save_session(self._current_session)
            
            # Event is already published to event bus by screen capture service
            self.logger.debug(f"Screenshot processed: {event.data.get('filename')}")
            
        except Exception as e:
            self.logger.error(f"Error handling screenshot: {e}")
    
    async def _on_video_segment_complete(self, event: Event) -> None:
        """Handle video segment completion event."""
        try:
            # Event is already published to event bus by screen capture service
            segment_name = event.data.get('segment_name')
            duration = event.data.get('duration_seconds', 0)
            self.logger.info(f"Video segment processed: {segment_name} ({duration:.1f}s)")
            
        except Exception as e:
            self.logger.error(f"Error handling video segment: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != 'win32':
            # Unix-style signal handling
            loop = asyncio.get_event_loop()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        else:
            # Windows signal handling
            signal.signal(signal.SIGINT, lambda sig, frame: asyncio.create_task(self.stop()))
            signal.signal(signal.SIGTERM, lambda sig, frame: asyncio.create_task(self.stop()))