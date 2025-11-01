"""Global hotkey manager for capture controls."""

import asyncio
from typing import Callable, Optional
from pynput import keyboard

from src.config import get_config
from src.logger import get_app_logger


class HotkeyManager:
    """
    Manages global hotkeys for application control.
    
    Supports:
    - Pause/Resume capture (Ctrl+Shift+P)
    - Custom hotkey combinations
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._pause_callback: Optional[Callable] = None
        self._emergency_stop_callback: Optional[Callable] = None
        self._running = False
        
        # Parse pause shortcut
        self._pause_hotkey = self._parse_hotkey(self.config.privacy.pause_shortcut)
        
        # Emergency stop hotkey (Ctrl+Shift+Esc)
        self._emergency_stop_hotkey = self._parse_hotkey('ctrl+shift+esc')
        
        self.logger.info(f"Hotkey manager initialized with pause key: {self.config.privacy.pause_shortcut}")
        self.logger.info(f"Emergency stop hotkey: Ctrl+Shift+Esc")
    
    def set_pause_callback(self, callback: Callable) -> None:
        """Set callback for pause/resume hotkey."""
        self._pause_callback = callback
    
    def set_emergency_stop_callback(self, callback: Callable) -> None:
        """Set callback for emergency stop hotkey."""
        self._emergency_stop_callback = callback
    
    def start(self) -> None:
        """Start listening for global hotkeys."""
        if self._running:
            return
        
        try:
            hotkeys = {}
            
            if self._pause_hotkey and self._pause_callback:
                hotkeys[self._pause_hotkey] = self._on_pause_hotkey
            
            if self._emergency_stop_hotkey and self._emergency_stop_callback:
                hotkeys[self._emergency_stop_hotkey] = self._on_emergency_stop_hotkey
            
            if hotkeys:
                self._listener = keyboard.GlobalHotKeys(hotkeys)
                self._listener.start()
                self._running = True
                
                self.logger.info("Global hotkey listener started")
                self.logger.info(f"Registered hotkeys: {list(hotkeys.keys())}")
            else:
                self.logger.warning("No hotkeys configured")
                
        except Exception as e:
            self.logger.error(f"Failed to start hotkey listener: {e}")
    
    def stop(self) -> None:
        """Stop listening for global hotkeys."""
        if not self._running:
            return
        
        try:
            if self._listener:
                self._listener.stop()
                self._listener = None
            
            self._running = False
            self.logger.info("Global hotkey listener stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop hotkey listener: {e}")
    
    def _parse_hotkey(self, hotkey_str: str) -> Optional[str]:
        """Parse hotkey string into pynput format."""
        try:
            # Convert common formats to pynput format
            # e.g., "ctrl+shift+p" -> "<ctrl>+<shift>+p"
            
            parts = hotkey_str.lower().split('+')
            parsed_parts = []
            
            for part in parts:
                part = part.strip()
                
                # Map common key names
                if part in ['ctrl', 'control']:
                    parsed_parts.append('<ctrl>')
                elif part in ['shift']:
                    parsed_parts.append('<shift>')
                elif part in ['alt']:
                    parsed_parts.append('<alt>')
                elif part in ['cmd', 'super', 'win']:
                    parsed_parts.append('<cmd>')
                else:
                    # Regular key
                    parsed_parts.append(part)
            
            return '+'.join(parsed_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to parse hotkey '{hotkey_str}': {e}")
            return None
    
    def _on_pause_hotkey(self) -> None:
        """Handle pause/resume hotkey press."""
        try:
            if self._pause_callback:
                # Run callback in thread-safe way
                asyncio.create_task(self._call_pause_callback())
            
        except Exception as e:
            self.logger.error(f"Error handling pause hotkey: {e}")
    
    async def _call_pause_callback(self) -> None:
        """Call pause callback safely."""
        try:
            if asyncio.iscoroutinefunction(self._pause_callback):
                await self._pause_callback()
            else:
                self._pause_callback()
                
        except Exception as e:
            self.logger.error(f"Error in pause callback: {e}")
    
    def _on_emergency_stop_hotkey(self) -> None:
        """Handle emergency stop hotkey press."""
        try:
            self.logger.warning("Emergency stop hotkey pressed (Ctrl+Shift+Esc)")
            if self._emergency_stop_callback:
                # Run callback in thread-safe way
                asyncio.create_task(self._call_emergency_stop_callback())
            
        except Exception as e:
            self.logger.error(f"Error handling emergency stop hotkey: {e}")
    
    async def _call_emergency_stop_callback(self) -> None:
        """Call emergency stop callback safely."""
        try:
            if asyncio.iscoroutinefunction(self._emergency_stop_callback):
                await self._emergency_stop_callback()
            else:
                self._emergency_stop_callback()
                
        except Exception as e:
            self.logger.error(f"Error in emergency stop callback: {e}")