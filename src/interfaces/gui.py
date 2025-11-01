"""GUI abstraction layer for decoupling services from the UI toolkit.

Defines a minimal interface that a concrete GUI implementation (e.g., wxPython)
must provide so that the application coordinator and services can interact with
the UI without depending on a specific framework.
"""

from __future__ import annotations

from typing import Protocol, Callable, Sequence, Any, Optional, Dict, List
from datetime import datetime


class GuiPort(Protocol):
    """Enhanced interface the GUI must implement for comprehensive backend-frontend communication."""

    # Recording state
    def get_recording_state(self) -> dict: ...
    def update_recording_state(self, is_recording: bool, is_paused: bool) -> None: ...

    # Session information
    def update_session_info(self, session: Any) -> None: ...

    # Activity feed
    def add_action_to_feed(self, action: Any) -> None: ...
    def add_actions_to_feed(self, actions: Sequence[Any]) -> None: ...

    # Workflow dashboard
    def add_pattern_to_dashboard(self, pattern: Any) -> None: ...
    def add_suggestion_to_dashboard(self, suggestion: Any) -> None: ...
    def set_patterns(self, patterns: Sequence[Any]) -> None: ...
    def set_suggestions(self, suggestions: Sequence[Any]) -> None: ...

    # Connection management
    def on_backend_connected(self) -> None:
        """Called when backend connection is established."""
        ...
    
    def on_backend_disconnected(self, reason: str) -> None:
        """Called when backend connection is lost."""
        ...
    
    def on_backend_reconnecting(self) -> None:
        """Called when attempting to reconnect to backend."""
        ...

    # Service health
    def update_service_health(self, service_name: str, status: str, details: str) -> None:
        """Update health status of a specific service."""
        ...
    
    def update_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update performance metrics display."""
        ...

    # Error handling
    def show_error(self, title: str, message: str, details: Optional[str] = None) -> None:
        """Display error dialog to user."""
        ...
    
    def show_warning(self, title: str, message: str) -> None:
        """Display warning dialog to user."""
        ...
    
    def show_info(self, title: str, message: str) -> None:
        """Display information dialog to user."""
        ...

    # Progress tracking
    def show_progress(self, title: str, message: str, progress: float) -> None:
        """Show progress dialog with percentage (0.0 to 1.0)."""
        ...
    
    def hide_progress(self) -> None:
        """Hide progress dialog."""
        ...

    # Storage management
    def update_storage_stats(self, stats: Dict[str, Any]) -> None:
        """Update storage statistics display."""
        ...
    
    def on_cleanup_progress(self, files_deleted: int, space_freed: int) -> None:
        """Update cleanup progress."""
        ...

    # Session management
    def update_sessions_list(self, sessions: List[Any]) -> None:
        """Update list of recording sessions."""
        ...
    
    def on_session_deleted(self, session_id: str) -> None:
        """Handle session deletion notification."""
        ...

    # Workflow execution
    def on_workflow_started(self, workflow_id: str) -> None:
        """Called when workflow execution starts."""
        ...
    
    def on_workflow_progress(self, workflow_id: str, step: str, progress: float) -> None:
        """Update workflow execution progress."""
        ...
    
    def on_workflow_completed(self, workflow_id: str, result: Dict[str, Any]) -> None:
        """Called when workflow execution completes successfully."""
        ...
    
    def on_workflow_failed(self, workflow_id: str, error: str) -> None:
        """Called when workflow execution fails."""
        ...

    # Logging
    def add_log_message(self, level: str, source: str, message: str, timestamp: datetime) -> None:
        """Add log message to debug panel."""
        ...

    # Event callbacks set by coordinator
    on_start_recording: Optional[Callable[[], None]]
    on_stop_recording: Optional[Callable[[], None]]
    on_pause: Optional[Callable[[], None]]
    on_resume: Optional[Callable[[], None]]


