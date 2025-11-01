"""Safety Manager for Automation Execution.

This module provides comprehensive safety features for automation execution including:
- Emergency stop mechanism
- Action timeout detection
- Rate limiting
- Bounds checking
- Action validation
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import deque
import pyautogui

from src.config import get_config
from src.logger import get_app_logger


class SafetyManager:
    """
    Safety manager for automation execution.
    
    Features:
    - Emergency stop mechanism with <1s response time
    - Action timeout detection
    - Rate limiting to prevent runaway automations
    - Bounds checking for coordinates
    - Action parameter validation
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Emergency stop flag
        self.emergency_stop_triggered = False
        
        # Action timeouts (in seconds) for each action type
        self.action_timeouts: Dict[str, float] = {
            'click': 5.0,
            'type_text': 10.0,
            'press_key': 5.0,
            'hotkey': 5.0,
            'move_to': 5.0,
            'drag_to': 10.0,
            'scroll': 5.0,
            'wait': 300.0,  # Max 5 minutes for wait
            'browser_navigate': 30.0,
            'browser_click': 10.0,
            'browser_type': 10.0,
            'browser_fill': 10.0,
            'browser_select': 10.0,
            'browser_check': 10.0,
            'browser_uncheck': 10.0,
            'browser_press_key': 5.0,
            'browser_get_text': 10.0,
            'browser_screenshot': 15.0,
            'browser_wait_for': 60.0,
            'browser_fill_form': 30.0,
            'browser_submit_form': 30.0,
            'browser_extract_table': 30.0,
            'excel_open': 30.0,
            'excel_create': 10.0,
            'excel_close': 10.0,
            'excel_save': 20.0,
            'excel_read_cell': 5.0,
            'excel_write_cell': 5.0,
            'excel_write_range': 30.0,
            'excel_insert_formula': 10.0,
            'file_copy': 60.0,
            'file_move': 60.0,
            'file_rename': 10.0,
            'file_delete': 10.0,
            'folder_create': 10.0,
            'folder_delete': 30.0,
            'window_find': 10.0,
            'window_focus': 5.0,
            'window_minimize': 5.0,
            'window_maximize': 5.0,
        }
        
        # Rate limiting
        self.max_actions_per_minute = 60
        self._action_timestamps: deque = deque(maxlen=self.max_actions_per_minute)
        
        # Screen dimensions for bounds checking
        self._screen_width, self._screen_height = pyautogui.size()
        
        self.logger.info("Safety manager initialized")
    
    async def check_emergency_stop(self) -> bool:
        """
        Check if emergency stop has been triggered.
        
        Returns:
            True if emergency stop is active, False otherwise
        """
        return self.emergency_stop_triggered
    
    async def trigger_emergency_stop(self) -> None:
        """
        Trigger emergency stop for all automations.
        
        This will immediately halt all running automations.
        Response time: <1 second
        """
        if not self.emergency_stop_triggered:
            self.emergency_stop_triggered = True
            self.logger.warning("EMERGENCY STOP TRIGGERED - All automations will halt")
        else:
            self.logger.info("Emergency stop already triggered")
    
    async def reset_emergency_stop(self) -> None:
        """
        Reset emergency stop flag.
        
        This allows automations to run again after emergency stop.
        """
        if self.emergency_stop_triggered:
            self.emergency_stop_triggered = False
            self.logger.info("Emergency stop reset - Automations can resume")
        else:
            self.logger.info("Emergency stop was not active")
    
    async def check_timeout(self, action_type: str, start_time: datetime) -> bool:
        """
        Check if an action has exceeded its timeout.
        
        Args:
            action_type: Type of action being executed
            start_time: When the action started
            
        Returns:
            True if action has timed out, False otherwise
        """
        timeout = self.action_timeouts.get(action_type, 30.0)  # Default 30s
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if elapsed > timeout:
            self.logger.warning(
                f"Action timeout detected: {action_type} exceeded {timeout}s "
                f"(elapsed: {elapsed:.1f}s)"
            )
            return True
        
        return False
    
    async def check_rate_limit(self) -> bool:
        """
        Check if rate limit has been exceeded.
        
        Uses a sliding window to track actions per minute.
        
        Returns:
            True if rate limit exceeded, False otherwise
        """
        now = datetime.now()
        
        # Remove timestamps older than 1 minute
        cutoff = now - timedelta(minutes=1)
        while self._action_timestamps and self._action_timestamps[0] < cutoff:
            self._action_timestamps.popleft()
        
        # Check if we've exceeded the limit
        if len(self._action_timestamps) >= self.max_actions_per_minute:
            self.logger.warning(
                f"Rate limit exceeded: {len(self._action_timestamps)} actions "
                f"in last minute (max: {self.max_actions_per_minute})"
            )
            return True
        
        # Record this action
        self._action_timestamps.append(now)
        return False
    
    async def validate_action(self, action: Dict[str, Any]) -> bool:
        """
        Validate action before execution.
        
        Checks:
        - Required parameters are present
        - Coordinates are within screen bounds
        - Action type is recognized
        
        Args:
            action: Action data dictionary
            
        Returns:
            True if action is valid, False otherwise
        """
        action_type = action.get('type')
        
        if not action_type:
            self.logger.error("Action validation failed: missing 'type' field")
            return False
        
        # Validate coordinates for desktop actions
        if action_type in ['click', 'move_to', 'drag_to']:
            x = action.get('x')
            y = action.get('y')
            
            if x is None or y is None:
                self.logger.error(
                    f"Action validation failed: {action_type} missing coordinates"
                )
                return False
            
            # Bounds checking
            if not self._check_bounds(x, y):
                self.logger.error(
                    f"Action validation failed: coordinates ({x}, {y}) out of bounds "
                    f"(screen: {self._screen_width}x{self._screen_height})"
                )
                return False
        
        # Validate text for type actions
        if action_type in ['type_text', 'browser_type', 'browser_fill']:
            text = action.get('text')
            if text is None:
                self.logger.error(
                    f"Action validation failed: {action_type} missing 'text' parameter"
                )
                return False
        
        # Validate key for key press actions
        if action_type in ['press_key', 'browser_press_key']:
            key = action.get('key')
            if not key:
                self.logger.error(
                    f"Action validation failed: {action_type} missing 'key' parameter"
                )
                return False
        
        # Validate keys for hotkey actions
        if action_type == 'hotkey':
            keys = action.get('keys')
            if not keys or not isinstance(keys, list) or len(keys) == 0:
                self.logger.error(
                    f"Action validation failed: hotkey missing or invalid 'keys' parameter"
                )
                return False
        
        # Validate selector for browser actions
        if action_type in ['browser_click', 'browser_type', 'browser_fill', 
                          'browser_select', 'browser_check', 'browser_uncheck',
                          'browser_get_text', 'browser_wait_for']:
            selector = action.get('selector')
            if not selector:
                self.logger.error(
                    f"Action validation failed: {action_type} missing 'selector' parameter"
                )
                return False
        
        # Validate URL for browser navigation
        if action_type == 'browser_navigate':
            url = action.get('url')
            if not url:
                self.logger.error(
                    f"Action validation failed: browser_navigate missing 'url' parameter"
                )
                return False
        
        # Validate file paths for file operations
        if action_type in ['file_copy', 'file_move']:
            source = action.get('source')
            destination = action.get('destination')
            if not source or not destination:
                self.logger.error(
                    f"Action validation failed: {action_type} missing file paths"
                )
                return False
        
        # Validate Excel parameters
        if action_type in ['excel_write_cell', 'excel_read_cell', 'excel_insert_formula']:
            cell = action.get('cell')
            if not cell:
                self.logger.error(
                    f"Action validation failed: {action_type} missing 'cell' parameter"
                )
                return False
        
        return True
    
    def _check_bounds(self, x: int, y: int) -> bool:
        """
        Check if coordinates are within screen bounds.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if within bounds, False otherwise
        """
        return 0 <= x < self._screen_width and 0 <= y < self._screen_height
    
    def get_timeout(self, action_type: str) -> float:
        """
        Get timeout for specific action type.
        
        Args:
            action_type: Type of action
            
        Returns:
            Timeout in seconds
        """
        return self.action_timeouts.get(action_type, 30.0)
    
    def set_timeout(self, action_type: str, timeout: float) -> None:
        """
        Set custom timeout for action type.
        
        Args:
            action_type: Type of action
            timeout: Timeout in seconds
        """
        self.action_timeouts[action_type] = timeout
        self.logger.info(f"Set timeout for {action_type}: {timeout}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get safety manager statistics.
        
        Returns:
            Dictionary with safety statistics
        """
        return {
            'emergency_stop_active': self.emergency_stop_triggered,
            'max_actions_per_minute': self.max_actions_per_minute,
            'actions_in_last_minute': len(self._action_timestamps),
            'screen_dimensions': {
                'width': self._screen_width,
                'height': self._screen_height
            },
            'configured_timeouts': len(self.action_timeouts)
        }
