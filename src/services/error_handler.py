"""Error Handler Service.

Provides comprehensive error handling and recovery:
- Error classification
- Retry logic with exponential backoff
- Error recovery mechanisms
- Global exception handling
- GUI error notifications
"""

import asyncio
import traceback
from typing import Optional, Callable, Any, Dict, TYPE_CHECKING
from enum import Enum
from datetime import datetime

from src.config import get_config
from src.logger import get_app_logger

if TYPE_CHECKING:
    from src.interfaces.gui import GuiPort


class ErrorSeverity(Enum):
    """Error severity levels."""
    RECOVERABLE = "recoverable"
    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"
    CRITICAL = "critical"


class RecoverableError(Exception):
    """Error that can be recovered with retry."""
    pass


class UserError(Exception):
    """Error caused by user input."""
    pass


class SystemError(Exception):
    """System-level error."""
    pass


class CriticalError(Exception):
    """Critical error requiring immediate attention."""
    pass


class ConnectionError(Exception):
    """Connection error between backend and frontend."""
    pass


class ServiceError(Exception):
    """Service-specific error."""
    pass


class ValidationError(Exception):
    """Input validation error."""
    pass


class StorageError(Exception):
    """Storage/database error."""
    pass


class ErrorHandler:
    """Service for handling errors and recovery with GUI integration."""
    
    def __init__(self, gui_port: Optional['GuiPort'] = None):
        """
        Initialize Error Handler.
        
        Args:
            gui_port: Optional GUI port for error notifications
        """
        self.config = get_config()
        self.logger = get_app_logger()
        self._gui_port = gui_port
        self._error_counts: Dict[str, int] = {}
        self._max_retries = 3
        
    def set_gui_port(self, gui_port: 'GuiPort') -> None:
        """Set GUI port for error notifications."""
        self._gui_port = gui_port
        
    async def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ) -> Any:
        """Retry function with exponential backoff."""
        import random
        
        for attempt in range(max_retries):
            try:
                return await func() if asyncio.iscoroutinefunction(func) else func()
            except RecoverableError as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Max retries reached: {e}")
                    raise
                
                delay = base_delay * (backoff_multiplier ** attempt)
                if jitter:
                    delay *= (0.5 + random.random())
                
                self.logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        raise RecoverableError("Max retries exceeded")
    
    def classify_error(self, error: Exception) -> ErrorSeverity:
        """Classify error by severity."""
        if isinstance(error, RecoverableError):
            return ErrorSeverity.RECOVERABLE
        elif isinstance(error, (UserError, ValidationError)):
            return ErrorSeverity.USER_ERROR
        elif isinstance(error, CriticalError):
            return ErrorSeverity.CRITICAL
        else:
            return ErrorSeverity.SYSTEM_ERROR
    
    async def handle_error(self, error: Exception, context: str = "") -> bool:
        """
        Handle error based on severity and determine if operation should be retried.
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            
        Returns:
            True if operation should be retried, False otherwise
        """
        error_key = f"{context}:{type(error).__name__}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        
        severity = self.classify_error(error)
        
        self.logger.error(
            f"Error in {context}: {error}\n"
            f"Severity: {severity.value}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        # Handle based on error type
        if isinstance(error, ConnectionError):
            return await self._handle_connection_error(error, context)
        elif isinstance(error, ServiceError):
            return await self._handle_service_error(error, context)
        elif isinstance(error, ValidationError):
            return await self._handle_validation_error(error, context)
        elif isinstance(error, StorageError):
            return await self._handle_storage_error(error, context)
        elif severity == ErrorSeverity.CRITICAL:
            await self._handle_critical_error(error, context)
            return False
        else:
            return await self._handle_unknown_error(error, context)
    
    async def _handle_connection_error(self, error: Exception, context: str) -> bool:
        """Handle connection errors."""
        if self._error_counts.get(f"{context}:ConnectionError", 0) < self._max_retries:
            if self._gui_port:
                self._gui_port.show_warning(
                    "Connection Issue",
                    "Attempting to reconnect to backend..."
                )
            await asyncio.sleep(2)  # Wait before retry
            return True  # Retry
        else:
            if self._gui_port:
                self._gui_port.show_error(
                    "Connection Failed",
                    "Unable to connect to backend services. Please restart the application.",
                    str(error)
                )
            return False  # Don't retry
    
    async def _handle_service_error(self, error: Exception, context: str) -> bool:
        """Handle service errors."""
        if self._gui_port:
            self._gui_port.show_error(
                "Service Error",
                f"A service error occurred: {context}",
                str(error)
            )
        return False  # Don't retry service errors
    
    async def _handle_validation_error(self, error: Exception, context: str) -> bool:
        """Handle validation errors."""
        if self._gui_port:
            self._gui_port.show_error(
                "Validation Error",
                "Invalid input provided",
                str(error)
            )
        return False  # Don't retry validation errors
    
    async def _handle_storage_error(self, error: Exception, context: str) -> bool:
        """Handle storage errors."""
        if self._gui_port:
            self._gui_port.show_error(
                "Storage Error",
                "A database or storage error occurred",
                str(error)
            )
        return False  # Don't retry storage errors
    
    async def _handle_critical_error(self, error: Exception, context: str) -> None:
        """Handle critical errors."""
        self.logger.critical(f"CRITICAL ERROR in {context}: {error}")
        if self._gui_port:
            self._gui_port.show_error(
                "Critical Error",
                "A critical error occurred. The application may need to be restarted.",
                str(error)
            )
    
    async def _handle_unknown_error(self, error: Exception, context: str) -> bool:
        """Handle unknown errors."""
        if self._gui_port:
            self._gui_port.show_error(
                "Unexpected Error",
                f"An unexpected error occurred: {context}",
                str(error)
            )
        return False  # Don't retry unknown errors


async def execute_with_retry(
    operation: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    error_handler: Optional[ErrorHandler] = None
) -> Any:
    """
    Execute operation with exponential backoff retry.
    
    Args:
        operation: Async or sync callable to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        error_handler: Optional error handler for error processing
        
    Returns:
        Result of operation
        
    Raises:
        Last exception if all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation()
            else:
                return operation()
        except Exception as e:
            last_error = e
            
            if error_handler:
                should_retry = await error_handler.handle_error(e, operation.__name__)
                if not should_retry:
                    break
            
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                await asyncio.sleep(wait_time)
            else:
                break
    
    raise last_error
