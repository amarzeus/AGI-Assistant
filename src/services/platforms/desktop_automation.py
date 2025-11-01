"""Desktop automation platform using PyAutoGUI."""

import asyncio
import time
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("Warning: PyAutoGUI not installed. Desktop automation will not work.")

from src.logger import get_app_logger


class DesktopAutomationPlatform:
    """
    Desktop automation platform for mouse and keyboard control.
    
    Features:
    - Mouse control (click, move, drag)
    - Keyboard control (type, hotkeys)
    - Screen bounds checking
    - Configurable delays
    - Safety features (failsafe)
    """
    
    def __init__(self):
        self.logger = get_app_logger()
        
        if not PYAUTOGUI_AVAILABLE:
            self.logger.error("PyAutoGUI not available")
            self.enabled = False
            return
        
        self.enabled = True
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1  # Default pause between actions
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Settings
        self.default_duration = 0.25  # Smooth mouse movement duration
        self.typing_interval = 0.05  # Delay between keystrokes
        
        self.logger.info(f"Desktop automation platform initialized (screen: {self.screen_width}x{self.screen_height})")
    
    def _validate_coordinates(self, x: int, y: int) -> bool:
        """Validate that coordinates are within screen bounds."""
        if not (0 <= x < self.screen_width and 0 <= y < self.screen_height):
            self.logger.warning(f"Coordinates out of bounds: ({x}, {y})")
            return False
        return True
    
    async def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks (1 for single, 2 for double)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            self.logger.error("Desktop automation not enabled")
            return False
        
        try:
            # Validate coordinates
            if not self._validate_coordinates(x, y):
                return False
            
            self.logger.debug(f"Clicking at ({x}, {y}) with {button} button, {clicks} clicks")
            
            # Perform click in thread pool to avoid blocking
            await asyncio.to_thread(
                pyautogui.click,
                x=x,
                y=y,
                clicks=clicks,
                button=button
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Click failed: {e}")
            return False
    
    async def move_to(self, x: int, y: int, duration: Optional[float] = None) -> bool:
        """
        Move mouse to specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration in seconds (None for instant)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            if not self._validate_coordinates(x, y):
                return False
            
            if duration is None:
                duration = self.default_duration
            
            self.logger.debug(f"Moving mouse to ({x}, {y}) over {duration}s")
            
            await asyncio.to_thread(
                pyautogui.moveTo,
                x=x,
                y=y,
                duration=duration
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Move failed: {e}")
            return False
    
    async def drag_to(self, x: int, y: int, duration: Optional[float] = None, button: str = 'left') -> bool:
        """
        Drag mouse to specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Drag duration in seconds
            button: Mouse button to hold
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            if not self._validate_coordinates(x, y):
                return False
            
            if duration is None:
                duration = self.default_duration
            
            self.logger.debug(f"Dragging to ({x}, {y}) over {duration}s")
            
            await asyncio.to_thread(
                pyautogui.dragTo,
                x=x,
                y=y,
                duration=duration,
                button=button
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Drag failed: {e}")
            return False
    
    async def type_text(self, text: str, interval: Optional[float] = None) -> bool:
        """
        Type text with configurable delay between characters.
        
        Args:
            text: Text to type
            interval: Delay between keystrokes in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            if interval is None:
                interval = self.typing_interval
            
            self.logger.debug(f"Typing text: {text[:50]}... (interval: {interval}s)")
            
            await asyncio.to_thread(
                pyautogui.write,
                text,
                interval=interval
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Type text failed: {e}")
            return False
    
    async def press_key(self, key: str, presses: int = 1) -> bool:
        """
        Press a key one or more times.
        
        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape', 'a', 'ctrl')
            presses: Number of times to press
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            self.logger.debug(f"Pressing key: {key} ({presses} times)")
            
            await asyncio.to_thread(
                pyautogui.press,
                key,
                presses=presses
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Press key failed: {e}")
            return False
    
    async def hotkey(self, *keys: str) -> bool:
        """
        Press a hotkey combination.
        
        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            keys_str = '+'.join(keys)
            self.logger.debug(f"Pressing hotkey: {keys_str}")
            
            await asyncio.to_thread(
                pyautogui.hotkey,
                *keys
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Hotkey failed: {e}")
            return False
    
    async def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        Scroll the mouse wheel.
        
        Args:
            clicks: Number of clicks (positive for up, negative for down)
            x: X coordinate to scroll at (None for current position)
            y: Y coordinate to scroll at (None for current position)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            self.logger.debug(f"Scrolling {clicks} clicks at ({x}, {y})")
            
            await asyncio.to_thread(
                pyautogui.scroll,
                clicks,
                x=x,
                y=y
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return False
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if not self.enabled:
            return (0, 0)
        
        return pyautogui.position()
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen size."""
        return (self.screen_width, self.screen_height)
    
    async def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Any]:
        """
        Take a screenshot.
        
        Args:
            region: (x, y, width, height) or None for full screen
            
        Returns:
            PIL Image object or None
        """
        if not self.enabled:
            return None
        
        try:
            self.logger.debug(f"Taking screenshot (region: {region})")
            
            screenshot = await asyncio.to_thread(
                pyautogui.screenshot,
                region=region
            )
            
            return screenshot
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None
    
    def set_pause(self, seconds: float) -> None:
        """Set pause duration between PyAutoGUI actions."""
        if self.enabled:
            pyautogui.PAUSE = seconds
            self.logger.debug(f"Set pause to {seconds}s")
    
    def set_failsafe(self, enabled: bool) -> None:
        """Enable/disable failsafe (move mouse to corner to abort)."""
        if self.enabled:
            pyautogui.FAILSAFE = enabled
            self.logger.debug(f"Failsafe {'enabled' if enabled else 'disabled'}")
