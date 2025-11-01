"""Command Dispatcher for routing GUI commands to backend services.

This module provides a centralized command dispatcher that validates,
routes, and executes commands from the GUI to appropriate backend services.
"""

import asyncio
from typing import Any, Dict, Callable, Optional, TYPE_CHECKING
from datetime import datetime

from src.logger import get_app_logger

if TYPE_CHECKING:
    from src.services.application_coordinator import ApplicationCoordinator


class CommandDispatcher:
    """
    Routes GUI commands to appropriate backend services with validation.
    
    Responsibilities:
    - Validate command parameters
    - Route commands to appropriate service methods
    - Handle command execution errors
    - Return results to GUI
    """
    
    def __init__(self, coordinator: 'ApplicationCoordinator'):
        """
        Initialize Command Dispatcher.
        
        Args:
            coordinator: Reference to ApplicationCoordinator
        """
        self._coordinator = coordinator
        self._handlers: Dict[str, Callable] = {}
        self._register_handlers()
        
        self.logger = get_app_logger()
        self.logger.info("Command Dispatcher initialized")
    
    def _register_handlers(self) -> None:
        """Register command handlers."""
        self._handlers = {
            # Recording control
            'start_recording': self._handle_start_recording,
            'stop_recording': self._handle_stop_recording,
            'pause_recording': self._handle_pause_recording,
            'resume_recording': self._handle_resume_recording,
            
            # Workflow execution
            'execute_workflow': self._handle_execute_workflow,
            'stop_workflow': self._handle_stop_workflow,
            
            # Storage management
            'cleanup_storage': self._handle_cleanup_storage,
            'get_storage_stats': self._handle_get_storage_stats,
            'export_data': self._handle_export_data,
            
            # Session management
            'get_sessions': self._handle_get_sessions,
            'get_session_details': self._handle_get_session_details,
            'delete_session': self._handle_delete_session,
            'delete_all_sessions': self._handle_delete_all_sessions,
            
            # Settings management
            'update_settings': self._handle_update_settings,
            'get_settings': self._handle_get_settings,
            'reset_settings': self._handle_reset_settings,
            
            # Hotkey management
            'update_hotkeys': self._handle_update_hotkeys,
            'get_hotkeys': self._handle_get_hotkeys,
        }
    
    async def dispatch(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Dispatch command to handler.
        
        Args:
            command: Command name
            params: Command parameters
            
        Returns:
            Dictionary with 'success' boolean and 'result' or 'error'
        """
        if params is None:
            params = {}
        
        handler = self._handlers.get(command)
        if not handler:
            return {
                'success': False,
                'error': f'Unknown command: {command}'
            }
        
        try:
            # Log command execution
            self.logger.info(f"Executing command: {command}")
            
            # Execute handler
            result = await handler(params)
            
            return {
                'success': True,
                'result': result
            }
        except ValueError as e:
            # Validation error
            self.logger.warning(f"Validation error for command {command}: {e}")
            return {
                'success': False,
                'error': f'Validation error: {str(e)}'
            }
        except Exception as e:
            # Execution error
            self.logger.error(f"Error executing command {command}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Execution error: {str(e)}'
            }
    
    # Recording control handlers
    
    async def _handle_start_recording(self, params: Dict[str, Any]) -> Any:
        """Handle start recording command."""
        await self._coordinator.start()
        session = self._coordinator.get_current_session()
        return {
            'session_id': session.id if session else None,
            'start_time': session.start_time.isoformat() if session else None
        }
    
    async def _handle_stop_recording(self, params: Dict[str, Any]) -> Any:
        """Handle stop recording command."""
        session = self._coordinator.get_current_session()
        session_id = session.id if session else None
        
        await self._coordinator.stop()
        
        return {
            'session_id': session_id,
            'stopped': True
        }
    
    async def _handle_pause_recording(self, params: Dict[str, Any]) -> Any:
        """Handle pause recording command."""
        await self._coordinator.pause_capture()
        return {'paused': True}
    
    async def _handle_resume_recording(self, params: Dict[str, Any]) -> Any:
        """Handle resume recording command."""
        await self._coordinator.resume_capture()
        return {'resumed': True}
    
    # Workflow execution handlers
    
    async def _handle_execute_workflow(self, params: Dict[str, Any]) -> Any:
        """Handle execute workflow command."""
        workflow_id = params.get('workflow_id')
        if not workflow_id:
            raise ValueError("workflow_id is required")
        
        if not self._coordinator.automation_executor:
            raise RuntimeError("Automation executor not available")
        
        # Execute workflow
        result = await self._coordinator.automation_executor.execute_workflow(workflow_id)
        
        return {
            'workflow_id': workflow_id,
            'status': result.get('status', 'unknown'),
            'result': result
        }
    
    async def _handle_stop_workflow(self, params: Dict[str, Any]) -> Any:
        """Handle stop workflow command."""
        workflow_id = params.get('workflow_id')
        if not workflow_id:
            raise ValueError("workflow_id is required")
        
        if not self._coordinator.automation_executor:
            raise RuntimeError("Automation executor not available")
        
        await self._coordinator.automation_executor.stop_workflow(workflow_id)
        
        return {
            'workflow_id': workflow_id,
            'stopped': True
        }
    
    # Storage management handlers
    
    async def _handle_cleanup_storage(self, params: Dict[str, Any]) -> Any:
        """Handle cleanup storage command."""
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        # Get cleanup parameters
        days_old = params.get('days_old', 30)
        
        # Perform cleanup
        result = await self._coordinator.storage_manager.cleanup_old_data(days_old)
        
        return {
            'files_deleted': result.get('files_deleted', 0),
            'space_freed_mb': result.get('space_freed_bytes', 0) / 1024 / 1024
        }
    
    async def _handle_get_storage_stats(self, params: Dict[str, Any]) -> Any:
        """Handle get storage stats command."""
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        stats = self._coordinator.storage_manager.get_storage_usage()
        
        return {
            'total_used_gb': stats.get('total_size_gb', 0),
            'database_size_mb': stats.get('database_size_bytes', 0) / 1024 / 1024,
            'screenshot_count': stats.get('screenshot_count', 0),
            'video_segment_count': stats.get('video_segment_count', 0),
            'session_count': stats.get('session_count', 0)
        }
    
    async def _handle_export_data(self, params: Dict[str, Any]) -> Any:
        """Handle export data command."""
        export_path = params.get('export_path')
        if not export_path:
            raise ValueError("export_path is required")
        
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        # Export data
        result = await self._coordinator.storage_manager.export_workflows(export_path)
        
        return {
            'export_path': export_path,
            'workflows_exported': result.get('count', 0)
        }
    
    # Session management handlers
    
    async def _handle_get_sessions(self, params: Dict[str, Any]) -> Any:
        """Handle get sessions command."""
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        sessions = await self._coordinator.storage_manager.get_all_sessions()
        
        return {
            'sessions': [
                {
                    'id': s.id,
                    'start_time': s.start_time.isoformat(),
                    'end_time': s.end_time.isoformat() if s.end_time else None,
                    'status': s.status.value,
                    'capture_count': s.capture_count
                }
                for s in sessions
            ]
        }
    
    async def _handle_get_session_details(self, params: Dict[str, Any]) -> Any:
        """Handle get session details command."""
        session_id = params.get('session_id')
        if not session_id:
            raise ValueError("session_id is required")
        
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        session = await self._coordinator.storage_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        return {
            'id': session.id,
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'status': session.status.value,
            'capture_count': session.capture_count,
            'detected_actions': session.detected_actions,
            'detected_patterns': session.detected_patterns
        }
    
    async def _handle_delete_session(self, params: Dict[str, Any]) -> Any:
        """Handle delete session command."""
        session_id = params.get('session_id')
        if not session_id:
            raise ValueError("session_id is required")
        
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        await self._coordinator.storage_manager.delete_session(session_id)
        
        return {
            'session_id': session_id,
            'deleted': True
        }
    
    async def _handle_delete_all_sessions(self, params: Dict[str, Any]) -> Any:
        """Handle delete all sessions command."""
        if not self._coordinator.storage_manager:
            raise RuntimeError("Storage manager not available")
        
        count = await self._coordinator.storage_manager.delete_all_sessions()
        
        return {
            'sessions_deleted': count
        }
    
    # Settings management handlers
    
    async def _handle_update_settings(self, params: Dict[str, Any]) -> Any:
        """Handle update settings command."""
        settings = params.get('settings')
        if not settings:
            raise ValueError("settings is required")
        
        # Validate settings
        self._validate_settings(settings)
        
        # Update configuration
        from src.config import get_config
        config = get_config()
        
        # Update screen capture settings
        if 'screenshot_interval' in settings:
            config.screen_capture.screenshot_interval = settings['screenshot_interval']
        
        # Update audio settings
        if 'audio_enabled' in settings:
            config.audio.enabled = settings['audio_enabled']
        if 'sample_rate' in settings:
            config.audio.sample_rate = settings['sample_rate']
        
        # Update storage settings
        if 'max_storage_gb' in settings:
            config.storage.max_storage_gb = settings['max_storage_gb']
        
        # Save configuration
        config.save()
        
        return {
            'updated': True,
            'settings': settings
        }
    
    def _validate_settings(self, settings: Dict[str, Any]) -> None:
        """Validate settings parameters."""
        if 'screenshot_interval' in settings:
            interval = settings['screenshot_interval']
            if not isinstance(interval, (int, float)) or interval < 1 or interval > 60:
                raise ValueError("screenshot_interval must be between 1 and 60 seconds")
        
        if 'sample_rate' in settings:
            rate = settings['sample_rate']
            if not isinstance(rate, int) or rate < 8000 or rate > 48000:
                raise ValueError("sample_rate must be between 8000 and 48000 Hz")
        
        if 'max_storage_gb' in settings:
            storage = settings['max_storage_gb']
            if not isinstance(storage, (int, float)) or storage < 1 or storage > 1000:
                raise ValueError("max_storage_gb must be between 1 and 1000 GB")
    
    async def _handle_get_settings(self, params: Dict[str, Any]) -> Any:
        """Handle get settings command."""
        from src.config import get_config
        config = get_config()
        
        return {
            'screenshot_interval': config.screen_capture.screenshot_interval,
            'audio_enabled': config.audio.enabled,
            'sample_rate': config.audio.sample_rate,
            'max_storage_gb': config.storage.max_storage_gb
        }
    
    async def _handle_reset_settings(self, params: Dict[str, Any]) -> Any:
        """Handle reset settings command."""
        from src.config import get_config
        config = get_config()
        
        # Reset to defaults
        config.reset_to_defaults()
        config.save()
        
        return {
            'reset': True
        }
    
    # Hotkey management handlers
    
    async def _handle_update_hotkeys(self, params: Dict[str, Any]) -> Any:
        """Handle update hotkeys command."""
        hotkeys = params.get('hotkeys')
        if not hotkeys:
            raise ValueError("hotkeys is required")
        
        if not self._coordinator.hotkey_manager:
            raise RuntimeError("Hotkey manager not available")
        
        # Update hotkeys
        for action, hotkey in hotkeys.items():
            self._coordinator.hotkey_manager.register_hotkey(action, hotkey)
        
        return {
            'updated': True,
            'hotkeys': hotkeys
        }
    
    async def _handle_get_hotkeys(self, params: Dict[str, Any]) -> Any:
        """Handle get hotkeys command."""
        if not self._coordinator.hotkey_manager:
            raise RuntimeError("Hotkey manager not available")
        
        hotkeys = self._coordinator.hotkey_manager.get_registered_hotkeys()
        
        return {
            'hotkeys': hotkeys
        }
