"""GUI Event Bridge for thread-safe backend-frontend communication.

This module provides a bridge between the asyncio-based backend services
and the wxPython GUI main thread, ensuring thread-safe event delivery and
state synchronization.
"""

import queue
import threading
from typing import Any, Dict, Optional, TYPE_CHECKING
from datetime import datetime

import wx

from src.logger import get_app_logger
from src.services.event_system import Event, EventType

if TYPE_CHECKING:
    from src.wxui.main_frame import MainFrame


class GuiEventBridge:
    """
    Manages thread-safe communication between asyncio backend and wxPython main thread.
    
    Responsibilities:
    - Queue backend events for processing on wx main thread
    - Dispatch events to appropriate panels using wx.CallAfter
    - Maintain local state cache for quick access
    - Handle connection loss and reconnection
    - Throttle high-frequency updates to prevent UI lag
    """
    
    def __init__(self, main_frame: 'MainFrame'):
        """
        Initialize GUI Event Bridge.
        
        Args:
            main_frame: Reference to MainFrame for GUI updates
        """
        self._main_frame = main_frame
        self._event_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._state_cache: Dict[str, Any] = {}
        self._connected = False
        self._processing_timer: Optional[wx.Timer] = None
        self._lock = threading.Lock()
        
        # Event throttling
        self._last_event_time: Dict[str, datetime] = {}
        self._throttle_interval = 0.1  # 100ms minimum between same event types
        
        # Statistics
        self._stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_dropped': 0,
            'queue_overflows': 0
        }
        
        self.logger = get_app_logger()
        self.logger.info("GUI Event Bridge initialized")
    
    def start(self) -> None:
        """Start event processing."""
        if self._processing_timer is not None:
            self.logger.warning("GUI Event Bridge already started")
            return
        
        self._processing_timer = wx.Timer(self._main_frame)
        self._main_frame.Bind(wx.EVT_TIMER, self._on_timer, self._processing_timer)
        self._processing_timer.Start(100)  # Process events every 100ms
        
        self._connected = True
        self.logger.info("GUI Event Bridge started")
        
        # Notify main frame of connection
        wx.CallAfter(self._main_frame.on_backend_connected)
    
    def stop(self) -> None:
        """Stop event processing and cleanup."""
        if self._processing_timer:
            self._processing_timer.Stop()
            self._processing_timer = None
        
        self._connected = False
        
        # Clear event queue
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info(f"GUI Event Bridge stopped. Stats: {self._stats}")
    
    def on_backend_event(self, event: Event) -> None:
        """
        Receive event from backend (called from any thread).
        
        Args:
            event: Event from backend services
        """
        self._stats['events_received'] += 1
        
        # Check if we should throttle this event
        if self._should_throttle(event):
            self._stats['events_dropped'] += 1
            return
        
        try:
            self._event_queue.put_nowait(event)
            self._last_event_time[event.type.value] = datetime.now()
        except queue.Full:
            self._stats['queue_overflows'] += 1
            self._stats['events_dropped'] += 1
            self.logger.warning(f"Event queue full, dropping event: {event.type.value}")
    
    def _should_throttle(self, event: Event) -> bool:
        """
        Check if event should be throttled.
        
        Args:
            event: Event to check
            
        Returns:
            True if event should be dropped, False otherwise
        """
        event_key = event.type.value
        last_time = self._last_event_time.get(event_key)
        
        if last_time is None:
            return False
        
        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed < self._throttle_interval
    
    def _on_timer(self, event: wx.TimerEvent) -> None:
        """Timer callback to process events on wx main thread."""
        self._process_events()
    
    def _process_events(self) -> None:
        """Process queued events on wx main thread."""
        # Process up to 10 events per cycle to avoid blocking UI
        for _ in range(10):
            if self._event_queue.empty():
                break
            
            try:
                event = self._event_queue.get_nowait()
                self._dispatch_event(event)
                self._stats['events_processed'] += 1
            except queue.Empty:
                break
            except Exception as e:
                self.logger.error(f"Error processing event: {e}", exc_info=True)
    
    def _dispatch_event(self, event: Event) -> None:
        """
        Dispatch event to appropriate handler.
        
        Args:
            event: Event to dispatch
        """
        try:
            if event.type == EventType.ACTION_DETECTED:
                self._handle_action_detected(event)
            elif event.type == EventType.PATTERN_DETECTED:
                self._handle_pattern_detected(event)
            elif event.type == EventType.SERVICE_ERROR:
                self._handle_service_error(event)
            elif event.type == EventType.SERVICE_STARTED:
                self._handle_service_started(event)
            elif event.type == EventType.SERVICE_STOPPED:
                self._handle_service_stopped(event)
            elif event.type == EventType.SESSION_CREATED:
                self._handle_session_created(event)
            elif event.type == EventType.SESSION_COMPLETED:
                self._handle_session_completed(event)
            elif event.type == EventType.SCREENSHOT_CAPTURED:
                self._handle_screenshot_captured(event)
            elif event.type == EventType.CAPTURE_PAUSED:
                self._handle_capture_paused(event)
            elif event.type == EventType.CAPTURE_RESUMED:
                self._handle_capture_resumed(event)
            else:
                self.logger.debug(f"Unhandled event type: {event.type.value}")
        except Exception as e:
            self.logger.error(f"Error dispatching event {event.type.value}: {e}", exc_info=True)
    
    def _handle_action_detected(self, event: Event) -> None:
        """Handle action detected event."""
        # Create action-like object for GUI display
        class ActionDisplay:
            def __init__(self, data):
                self.id = data.get('action_id', '')
                self.timestamp = datetime.fromisoformat(data.get('timestamp')) if isinstance(data.get('timestamp'), str) else data.get('timestamp', datetime.now())
                action_type = data.get('action_type', 'unknown')
                self.type = type('ActionType', (), {'value': action_type})()
                self.application = data.get('application', 'Unknown')
                self.description = data.get('description', '')
                self.confidence = data.get('confidence', 0.0)
        
        action = ActionDisplay(event.data)
        self._main_frame.add_action_to_feed(action)
    
    def _handle_pattern_detected(self, event: Event) -> None:
        """Handle pattern detected event."""
        self._main_frame.add_pattern_to_dashboard(event.data)
    
    def _handle_service_error(self, event: Event) -> None:
        """Handle service error event."""
        service_name = event.data.get('service_name', 'Unknown')
        error_msg = event.data.get('error', 'Unknown error')
        self._main_frame.show_error(
            f"Service Error: {service_name}",
            error_msg,
            event.data.get('details')
        )
    
    def _handle_service_started(self, event: Event) -> None:
        """Handle service started event."""
        service_name = event.data.get('service_name', 'Unknown')
        self._main_frame.update_service_health(service_name, 'healthy', 'Service started')
    
    def _handle_service_stopped(self, event: Event) -> None:
        """Handle service stopped event."""
        service_name = event.data.get('service_name', 'Unknown')
        self._main_frame.update_service_health(service_name, 'stopped', 'Service stopped')
    
    def _handle_session_created(self, event: Event) -> None:
        """Handle session created event."""
        # Update state cache
        self.update_cached_state('current_session_id', event.data.get('session_id'))
    
    def _handle_session_completed(self, event: Event) -> None:
        """Handle session completed event."""
        # Clear current session from cache
        self.update_cached_state('current_session_id', None)
    
    def _handle_screenshot_captured(self, event: Event) -> None:
        """Handle screenshot captured event."""
        # Update screenshot count in cache
        count = self.get_cached_state('screenshot_count', 0)
        self.update_cached_state('screenshot_count', count + 1)
    
    def _handle_capture_paused(self, event: Event) -> None:
        """Handle capture paused event."""
        self.update_cached_state('is_paused', True)
        self._main_frame.update_recording_state(
            self.get_cached_state('is_recording', False),
            True
        )
    
    def _handle_capture_resumed(self, event: Event) -> None:
        """Handle capture resumed event."""
        self.update_cached_state('is_paused', False)
        self._main_frame.update_recording_state(
            self.get_cached_state('is_recording', False),
            False
        )
    
    def get_cached_state(self, key: str, default: Any = None) -> Any:
        """
        Get cached state value.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            return self._state_cache.get(key, default)
    
    def update_cached_state(self, key: str, value: Any) -> None:
        """
        Update cached state value.
        
        Args:
            key: State key
            value: New value
        """
        with self._lock:
            self._state_cache[key] = value
    
    def is_connected(self) -> bool:
        """
        Check if connected to backend.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get event processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self._stats.copy()
