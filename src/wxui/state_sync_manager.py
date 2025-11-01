"""State Synchronization Manager for keeping GUI in sync with backend.

This module provides periodic state synchronization between the backend
and frontend, ensuring the GUI always reflects the current backend state.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from datetime import datetime

import wx

from src.logger import get_app_logger

if TYPE_CHECKING:
    from src.wxui.main_frame import MainFrame
    from src.services.application_coordinator import ApplicationCoordinator


class StateSyncManager:
    """
    Keeps GUI state synchronized with backend state.
    
    Responsibilities:
    - Poll backend for state updates
    - Detect state changes and update GUI
    - Handle state conflicts
    - Provide optimistic updates for better UX
    """
    
    def __init__(self, main_frame: 'MainFrame', coordinator: 'ApplicationCoordinator'):
        """
        Initialize State Sync Manager.
        
        Args:
            main_frame: Reference to MainFrame
            coordinator: Reference to ApplicationCoordinator
        """
        self._main_frame = main_frame
        self._coordinator = coordinator
        self._sync_interval = 1.0  # seconds
        self._sync_timer: Optional[wx.Timer] = None
        self._last_state: Dict[str, Any] = {}
        self._running = False
        
        self.logger = get_app_logger()
        self.logger.info("State Sync Manager initialized")
    
    def start(self) -> None:
        """Start state synchronization."""
        if self._running:
            self.logger.warning("State Sync Manager already running")
            return
        
        self._running = True
        
        # Create timer for periodic sync
        self._sync_timer = wx.Timer(self._main_frame)
        self._main_frame.Bind(wx.EVT_TIMER, self._on_timer, self._sync_timer)
        self._sync_timer.Start(int(self._sync_interval * 1000))  # Convert to milliseconds
        
        self.logger.info("State Sync Manager started")
    
    def stop(self) -> None:
        """Stop state synchronization."""
        if self._sync_timer:
            self._sync_timer.Stop()
            self._sync_timer = None
        
        self._running = False
        self.logger.info("State Sync Manager stopped")
    
    def _on_timer(self, event: wx.TimerEvent) -> None:
        """Timer callback for periodic synchronization."""
        self._sync_state()
    
    def _sync_state(self) -> None:
        """Synchronize state with backend."""
        try:
            # Get current backend state
            current_state = self._get_backend_state()
            
            # Detect changes
            changes = self._detect_changes(self._last_state, current_state)
            
            # Update GUI for each change
            for key, value in changes.items():
                self._update_gui_for_state(key, value)
            
            # Update last state
            self._last_state = current_state
        except Exception as e:
            self.logger.error(f"Error syncing state: {e}", exc_info=True)
    
    def _get_backend_state(self) -> Dict[str, Any]:
        """
        Get current backend state.
        
        Returns:
            Dictionary of current state
        """
        state = {}
        
        try:
            # Recording state
            state['is_recording'] = self._coordinator.is_running()
            
            # Session state
            session = self._coordinator.get_current_session()
            state['session_id'] = session.id if session else None
            state['session_start_time'] = session.start_time if session else None
            
            # Service health
            state['service_health'] = self._coordinator.get_service_health()
            
            # Capture state
            if self._coordinator.screen_capture:
                capture_status = self._coordinator.screen_capture.get_current_status()
                state['is_paused'] = capture_status.is_paused
                state['frames_captured'] = capture_status.frames_captured
        except Exception as e:
            self.logger.error(f"Error getting backend state: {e}")
        
        return state
    
    def _detect_changes(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect changes between old and new state.
        
        Args:
            old_state: Previous state
            new_state: Current state
            
        Returns:
            Dictionary of changed keys and their new values
        """
        changes = {}
        
        # Check for new or changed keys
        for key, value in new_state.items():
            if key not in old_state or old_state[key] != value:
                changes[key] = value
        
        # Check for removed keys
        for key in old_state:
            if key not in new_state:
                changes[key] = None
        
        return changes
    
    def _update_gui_for_state(self, key: str, value: Any) -> None:
        """
        Update GUI for state change.
        
        Args:
            key: State key that changed
            value: New value
        """
        try:
            if key == 'is_recording':
                is_paused = self._last_state.get('is_paused', False)
                wx.CallAfter(self._main_frame.update_recording_state, value, is_paused)
            
            elif key == 'is_paused':
                is_recording = self._last_state.get('is_recording', False)
                wx.CallAfter(self._main_frame.update_recording_state, is_recording, value)
            
            elif key == 'session_id':
                if value:
                    session = self._coordinator.get_current_session()
                    if session:
                        wx.CallAfter(self._main_frame.update_session_info, session)
            
            elif key == 'service_health':
                if isinstance(value, dict):
                    for service_name, is_healthy in value.items():
                        status = 'healthy' if is_healthy else 'failed'
                        details = 'Running' if is_healthy else 'Not responding'
                        wx.CallAfter(
                            self._main_frame.update_service_health,
                            service_name,
                            status,
                            details
                        )
            
            elif key == 'frames_captured':
                # Update capture count in dashboard
                pass  # Can add dashboard update here
        except Exception as e:
            self.logger.error(f"Error updating GUI for state {key}: {e}", exc_info=True)
    
    def force_sync(self) -> None:
        """Force immediate state synchronization."""
        self._sync_state()
    
    def get_last_state(self) -> Dict[str, Any]:
        """
        Get last synchronized state.
        
        Returns:
            Dictionary of last state
        """
        return self._last_state.copy()
