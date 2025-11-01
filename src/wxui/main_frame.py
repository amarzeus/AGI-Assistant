"""wxPython MainFrame implementing the GuiPort interface.

Provides native Windows look by using standard wx widgets and sizers.
"""

from __future__ import annotations

import sys
from typing import Optional, Sequence, Any, Callable
from datetime import datetime

import wx
import wx.adv

from src.wxui.panels.dashboard import DashboardPanel
from src.wxui.panels.storage import StoragePanel
from src.wxui.panels.activity import ActivityPanel
from src.wxui.panels.workflows import WorkflowsPanel
from src.wxui.panels.privacy import PrivacyPanel
from src.wxui.panels.settings import SettingsPanel
from src.wxui.panels.debug import DebugPanel

from src.interfaces.gui import GuiPort
from src.logger import get_app_logger
from src.wxui.gui_event_bridge import GuiEventBridge
from src.wxui.state_sync_manager import StateSyncManager


class SystemTray(wx.adv.TaskBarIcon):
    """System tray icon with basic menu actions."""

    def __init__(self, frame: 'MainFrame'):
        super().__init__()
        self._frame = frame
        self.SetIcon(self._frame.GetIcon(), "AGI Assistant")

    def CreatePopupMenu(self) -> wx.Menu:
        menu = wx.Menu()

        show_item = menu.Append(wx.ID_ANY, "Show Window")
        self.Bind(wx.EVT_MENU, lambda evt: (self._frame.Show(), self._frame.Raise()), show_item)

        hide_item = menu.Append(wx.ID_ANY, "Hide Window")
        self.Bind(wx.EVT_MENU, lambda evt: self._frame.Hide(), hide_item)

        menu.AppendSeparator()

        start_stop_item = menu.Append(wx.ID_ANY, "Start/Stop Recording")
        self.Bind(wx.EVT_MENU, lambda evt: self._frame.toggle_recording(), start_stop_item)

        pause_resume_item = menu.Append(wx.ID_ANY, "Pause/Resume")
        self.Bind(wx.EVT_MENU, lambda evt: self._frame.toggle_pause(), pause_resume_item)

        menu.AppendSeparator()

        quit_item = menu.Append(wx.ID_EXIT, "Quit")
        self.Bind(wx.EVT_MENU, lambda evt: self._frame.Close(), quit_item)

        return menu


class MainFrame(wx.Frame):
    """Main application window using native wx controls. Implements GuiPort interface."""

    on_start_recording: Optional[Callable[[], None]] = None
    on_stop_recording: Optional[Callable[[], None]] = None
    on_pause: Optional[Callable[[], None]] = None
    on_resume: Optional[Callable[[], None]] = None

    def __init__(self, parent: Optional[wx.Window] = None):
        super().__init__(parent, title="AGI Assistant", size=(960, 720))

        # Icons (optional, use default if none)
        self.SetIcon(wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)))

        # Logger
        self.logger = get_app_logger()

        # State
        self._is_recording = False
        self._is_paused = False
        self._session_start_time: Optional[datetime] = None
        self._current_session: Optional[Any] = None
        
        # Backend references (set by coordinator)
        self._coordinator: Optional[Any] = None
        self._storage_manager: Optional[Any] = None
        
        # Communication layer
        self._event_bridge: Optional[GuiEventBridge] = None
        self._state_sync: Optional[StateSyncManager] = None
        
        # Progress dialog
        self._progress_dialog: Optional[wx.ProgressDialog] = None

        # Create menu bar
        self._create_menu_bar()

        # Layout
        self._build_ui()

        # Tray (may fail on some systems, handle gracefully)
        try:
            self._tray = SystemTray(self)
        except Exception:
            # System tray not available (e.g., headless, some Linux DEs)
            self._tray = None

        # Timer for status updates
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(1000)

        # Close handling (hide to tray)
        self.Bind(wx.EVT_CLOSE, self._on_close)

        # Keyboard accelerators (Windows-native shortcuts)
        accel = wx.AcceleratorTable([
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('R'), self._bind_menu_id(self.toggle_recording)),
            (wx.ACCEL_CTRL, ord('P'), self._bind_menu_id(self.toggle_pause)),
        ])
        self.SetAcceleratorTable(accel)

    # ---- GuiPort implementation ----
    def get_recording_state(self) -> dict:
        return {
            "is_recording": self._is_recording,
            "is_paused": self._is_paused,
            "session_start_time": self._session_start_time.isoformat() if self._session_start_time else None,
        }

    def update_recording_state(self, is_recording: bool, is_paused: bool) -> None:
        self._is_recording = is_recording
        self._is_paused = is_paused
        self._refresh_controls()

    def update_session_info(self, session: Any) -> None:
        """Update session information display."""
        if session:
            self._current_session = session
            session_id = getattr(session, 'id', 'unknown')
            self._status_bar.SetStatusText(f"Session: {session_id[:8]}…", 1)
            
            # Update dashboard metrics
            wx.CallAfter(self.refresh_dashboard_metrics)

    def add_action_to_feed(self, action: Any) -> None:
        """Add a single action to the activity feed."""
        if hasattr(self, '_activity_panel') and self._activity_panel:
            try:
                from datetime import datetime
                time_str = action.timestamp.strftime("%H:%M:%S") if hasattr(action, 'timestamp') else datetime.now().strftime("%H:%M:%S")
                action_type = action.type.value if hasattr(action, 'type') else str(getattr(action, 'action_type', 'Unknown'))
                app_name = getattr(action, 'application', 'Unknown')
                desc = getattr(action, 'description', getattr(action, 'target_element', 'Action'))
                conf = f"{int(getattr(action, 'confidence', 0.0) * 100)}%"
                
                idx = self._activity_panel.list.InsertItem(0, time_str)
                self._activity_panel.list.SetItem(idx, 1, action_type)
                self._activity_panel.list.SetItem(idx, 2, app_name)
                self._activity_panel.list.SetItem(idx, 3, desc)
                self._activity_panel.list.SetItem(idx, 4, conf)
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Failed to add action to feed: {e}")

    def add_actions_to_feed(self, actions: Sequence[Any]) -> None:
        """Add multiple actions to the activity feed."""
        for action in actions:
            self.add_action_to_feed(action)

    def add_pattern_to_dashboard(self, pattern: Any) -> None:
        """Add a pattern to the workflows panel."""
        if hasattr(self, '_workflows_panel') and self._workflows_panel:
            try:
                pattern_name = getattr(pattern, 'pattern_type', getattr(pattern, 'description', 'Unknown Pattern'))
                frequency = str(getattr(pattern, 'frequency', 0)) + 'x'
                confidence = f"{int(getattr(pattern, 'confidence', 0.0) * 100)}%"
                last_seen = getattr(pattern, 'last_occurrence', None)
                if last_seen:
                    from datetime import datetime
                    if isinstance(last_seen, str):
                        last_seen = datetime.fromisoformat(last_seen)
                    if (datetime.now() - last_seen).days == 0:
                        last_seen_str = "Today"
                    elif (datetime.now() - last_seen).days == 1:
                        last_seen_str = "Yesterday"
                    else:
                        last_seen_str = last_seen.strftime("%Y-%m-%d")
                else:
                    last_seen_str = "Unknown"
                
                idx = self._workflows_panel.list.InsertItem(self._workflows_panel.list.GetItemCount(), pattern_name)
                self._workflows_panel.list.SetItem(idx, 1, frequency)
                self._workflows_panel.list.SetItem(idx, 2, confidence)
                self._workflows_panel.list.SetItem(idx, 3, last_seen_str)
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Failed to add pattern: {e}")

    def add_suggestion_to_dashboard(self, suggestion: Any) -> None:
        """Add a suggestion to the workflows panel."""
        # Could add to a suggestions section or similar
        self.add_pattern_to_dashboard(suggestion)

    def set_patterns(self, patterns: Sequence[Any]) -> None:
        """Replace all patterns in the workflows panel."""
        if hasattr(self, '_workflows_panel') and self._workflows_panel:
            self._workflows_panel.list.DeleteAllItems()
            for pattern in patterns:
                self.add_pattern_to_dashboard(pattern)

    def set_suggestions(self, suggestions: Sequence[Any]) -> None:
        """Set suggestions in the workflows panel."""
        self.set_patterns(suggestions)
    
    # Connection management
    def on_backend_connected(self) -> None:
        """Called when backend connection is established."""
        wx.CallAfter(self._status_bar.SetStatusText, "Connected to backend", 0)
        self.logger.info("Backend connected")
    
    def on_backend_disconnected(self, reason: str) -> None:
        """Called when backend connection is lost."""
        wx.CallAfter(self._status_bar.SetStatusText, f"Disconnected: {reason}", 0)
        wx.CallAfter(self.show_error, "Backend Disconnected", reason)
        self.logger.warning(f"Backend disconnected: {reason}")
    
    def on_backend_reconnecting(self) -> None:
        """Called when attempting to reconnect to backend."""
        wx.CallAfter(self._status_bar.SetStatusText, "Reconnecting to backend...", 0)
        self.logger.info("Attempting to reconnect to backend")
    
    # Service health
    def update_service_health(self, service_name: str, status: str, details: str) -> None:
        """Update health status of a specific service."""
        # Update dashboard with service health
        if hasattr(self, '_dashboard_panel') and self._dashboard_panel:
            wx.CallAfter(self._update_service_health_display, service_name, status, details)
    
    def _update_service_health_display(self, service_name: str, status: str, details: str) -> None:
        """Update service health display in dashboard."""
        # This would update a service health section in the dashboard
        # For now, log it
        self.logger.debug(f"Service {service_name}: {status} - {details}")
    
    def update_performance_metrics(self, metrics: dict[str, Any]) -> None:
        """Update performance metrics display."""
        if hasattr(self, '_dashboard_panel') and self._dashboard_panel:
            wx.CallAfter(self._update_performance_display, metrics)
    
    def _update_performance_display(self, metrics: dict[str, Any]) -> None:
        """Update performance metrics in dashboard."""
        # This would update performance metrics in the dashboard
        cpu = metrics.get('cpu_percent', 0)
        memory = metrics.get('memory_mb', 0)
        self.logger.debug(f"Performance: CPU {cpu:.1f}%, Memory {memory:.1f}MB")
    
    # Error handling
    def show_error(self, title: str, message: str, details: Optional[str] = None) -> None:
        """Display error dialog to user."""
        full_message = message
        if details:
            full_message += f"\n\nDetails:\n{details}"
        wx.CallAfter(wx.MessageBox, full_message, title, wx.OK | wx.ICON_ERROR)
    
    def show_warning(self, title: str, message: str) -> None:
        """Display warning dialog to user."""
        wx.CallAfter(wx.MessageBox, message, title, wx.OK | wx.ICON_WARNING)
    
    def show_info(self, title: str, message: str) -> None:
        """Display information dialog to user."""
        wx.CallAfter(wx.MessageBox, message, title, wx.OK | wx.ICON_INFORMATION)
    
    # Progress tracking
    def show_progress(self, title: str, message: str, progress: float) -> None:
        """Show progress dialog with percentage (0.0 to 1.0)."""
        if not self._progress_dialog:
            self._progress_dialog = wx.ProgressDialog(
                title,
                message,
                maximum=100,
                parent=self,
                style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE
            )
        
        percent = int(progress * 100)
        wx.CallAfter(self._progress_dialog.Update, percent, message)
    
    def hide_progress(self) -> None:
        """Hide progress dialog."""
        if self._progress_dialog:
            wx.CallAfter(self._progress_dialog.Destroy)
            self._progress_dialog = None
    
    # Storage management
    def update_storage_stats(self, stats: dict[str, Any]) -> None:
        """Update storage statistics display."""
        if hasattr(self, '_storage_panel') and self._storage_panel:
            wx.CallAfter(self._update_storage_display, stats)
    
    def _update_storage_display(self, stats: dict[str, Any]) -> None:
        """Update storage panel with stats."""
        total_gb = stats.get('total_used_gb', 0)
        db_mb = stats.get('database_size_mb', 0)
        screenshot_count = stats.get('screenshot_count', 0)
        
        if total_gb < 1:
            used_str = f"{total_gb * 1024:.1f} MB"
        else:
            used_str = f"{total_gb:.2f} GB"
        
        self._storage_panel.lbl_used.SetLabel(used_str)
    
    def on_cleanup_progress(self, files_deleted: int, space_freed: int) -> None:
        """Update cleanup progress."""
        space_mb = space_freed / 1024 / 1024
        message = f"Deleted {files_deleted} files, freed {space_mb:.1f} MB"
        self.show_progress("Cleaning Up", message, 0.5)
    
    # Session management
    def update_sessions_list(self, sessions: list[Any]) -> None:
        """Update list of recording sessions."""
        if hasattr(self, '_privacy_panel') and self._privacy_panel:
            wx.CallAfter(self._update_sessions_display, sessions)
    
    def _update_sessions_display(self, sessions: list[Any]) -> None:
        """Update privacy panel with sessions."""
        self._privacy_panel.table.DeleteAllItems()
        for session in sessions:
            session_id = getattr(session, 'id', 'unknown')
            start_time = getattr(session, 'start_time', None)
            status = getattr(session, 'status', 'unknown')
            
            idx = self._privacy_panel.table.InsertItem(
                self._privacy_panel.table.GetItemCount(),
                session_id[:8] if len(session_id) > 8 else session_id
            )
            self._privacy_panel.table.SetItem(idx, 1, start_time.strftime("%Y-%m-%d %H:%M") if start_time else "Unknown")
            self._privacy_panel.table.SetItem(idx, 2, str(status))
    
    def on_session_deleted(self, session_id: str) -> None:
        """Handle session deletion notification."""
        self.show_info("Session Deleted", f"Session {session_id[:8]}... has been deleted")
        wx.CallAfter(self.refresh_sessions)
    
    # Workflow execution
    def on_workflow_started(self, workflow_id: str) -> None:
        """Called when workflow execution starts."""
        self.show_progress("Executing Workflow", f"Starting workflow {workflow_id}...", 0.0)
    
    def on_workflow_progress(self, workflow_id: str, step: str, progress: float) -> None:
        """Update workflow execution progress."""
        self.show_progress("Executing Workflow", f"Step: {step}", progress)
    
    def on_workflow_completed(self, workflow_id: str, result: dict[str, Any]) -> None:
        """Called when workflow execution completes successfully."""
        self.hide_progress()
        self.show_info("Workflow Complete", f"Workflow {workflow_id} completed successfully")
    
    def on_workflow_failed(self, workflow_id: str, error: str) -> None:
        """Called when workflow execution fails."""
        self.hide_progress()
        self.show_error("Workflow Failed", f"Workflow {workflow_id} failed", error)
    
    # Logging
    def add_log_message(self, level: str, source: str, message: str, timestamp: datetime) -> None:
        """Add log message to debug panel."""
        if hasattr(self, '_debug_panel') and self._debug_panel:
            wx.CallAfter(self._add_log_to_debug, level, source, message, timestamp)
    
    def _add_log_to_debug(self, level: str, source: str, message: str, timestamp: datetime) -> None:
        """Add log message to debug panel."""
        time_str = timestamp.strftime("%H:%M:%S")
        log_line = f"[{time_str}] [{level}] {source}: {message}\n"
        self._debug_panel.log_text.AppendText(log_line)
    
    def set_coordinator(self, coordinator: Any) -> None:
        """Set reference to application coordinator."""
        self._coordinator = coordinator
        if coordinator and hasattr(coordinator, 'storage_manager'):
            self._storage_manager = coordinator.storage_manager
        
        # Initialize communication layer
        self._event_bridge = GuiEventBridge(self)
        self._event_bridge.start()
        
        # Initialize state synchronization
        self._state_sync = StateSyncManager(self, coordinator)
        self._state_sync.start()
        
        # Pass coordinator to workflows panel for emergency stop
        if hasattr(self, '_workflows_panel') and self._workflows_panel:
            self._workflows_panel.set_coordinator(coordinator)
    
    def refresh_storage_stats(self) -> None:
        """Refresh storage panel with real stats."""
        if hasattr(self, '_storage_panel') and self._storage_panel:
            if self._storage_manager:
                try:
                    import asyncio
                    # Get stats synchronously (storage_manager has sync methods)
                    stats = self._storage_manager.get_storage_stats()
                    usage = self._storage_manager.get_storage_usage()
                    
                    total_gb = usage.get('total_size_gb', 0)
                    limit_gb = self._storage_manager.config.storage.max_storage_gb
                    available_gb = max(0, limit_gb - total_gb)
                    
                    # Format display
                    if total_gb < 1:
                        used_str = f"{total_gb * 1024:.1f} MB"
                    else:
                        used_str = f"{total_gb:.2f} GB"
                    
                    if available_gb < 1:
                        avail_str = f"{available_gb * 1024:.1f} MB"
                    else:
                        avail_str = f"{available_gb:.2f} GB"
                    
                    limit_str = f"{limit_gb} GB"
                    
                    # Update UI
                    self._storage_panel.lbl_used.SetLabel(used_str)
                    self._storage_panel.lbl_available.SetLabel(avail_str)
                    self._storage_panel.lbl_limit.SetLabel(limit_str)
                    
                    # Update progress bar
                    if limit_gb > 0:
                        usage_percent = int((total_gb / limit_gb) * 100)
                        self._storage_panel.gauge.SetValue(min(100, usage_percent))
                    else:
                        self._storage_panel.gauge.SetValue(0)
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"Failed to refresh storage stats: {e}")
                    wx.MessageBox(f"Could not refresh storage stats:\n{str(e)}", "Error", wx.OK | wx.ICON_WARNING)
    
    def refresh_sessions(self) -> None:
        """Refresh privacy panel with real sessions."""
        if hasattr(self, '_privacy_panel') and self._privacy_panel:
            if self._storage_manager:
                try:
                    # Clear existing items
                    self._privacy_panel.table.DeleteAllItems()
                    
                    # Get sessions (using sync method for UI responsiveness)
                    session_count = self._storage_manager._get_session_count_sync()
                    
                    # For now, just show count. In full implementation, would fetch actual sessions
                    if session_count > 0:
                        # Add placeholder - in full implementation would load actual sessions
                        pass
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"Failed to refresh sessions: {e}")

    # ---- Menu bar ----
    def _create_menu_bar(self) -> None:
        """Create native Windows menu bar."""
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_EXIT, "E&xit\tAlt+F4", "Exit the application")
        self.Bind(wx.EVT_MENU, self._on_exit, id=wx.ID_EXIT)
        menubar.Append(file_menu, "&File")
        
        # Recording menu
        record_menu = wx.Menu()
        self.record_start = record_menu.Append(wx.ID_ANY, "&Start Recording\tCtrl+Shift+R", "Start recording")
        self.record_stop = record_menu.Append(wx.ID_ANY, "S&top Recording\tCtrl+Shift+S", "Stop recording")
        record_menu.AppendSeparator()
        self.record_pause = record_menu.Append(wx.ID_ANY, "&Pause\tCtrl+P", "Pause recording")
        self.record_resume = record_menu.Append(wx.ID_ANY, "&Resume\tCtrl+R", "Resume recording")
        self.Bind(wx.EVT_MENU, lambda evt: self.toggle_recording(), self.record_start)
        self.Bind(wx.EVT_MENU, lambda evt: self.toggle_recording(), self.record_stop)
        self.Bind(wx.EVT_MENU, lambda evt: self.toggle_pause(), self.record_pause)
        self.Bind(wx.EVT_MENU, lambda evt: self.toggle_pause(), self.record_resume)
        self.record_stop.Enable(False)
        self.record_pause.Enable(False)
        self.record_resume.Enable(False)
        menubar.Append(record_menu, "&Recording")
        
        # View menu
        view_menu = wx.Menu()
        dashboard_item = view_menu.Append(wx.ID_ANY, "&Dashboard", "Show Dashboard tab")
        storage_item = view_menu.Append(wx.ID_ANY, "&Storage", "Show Storage tab")
        activity_item = view_menu.Append(wx.ID_ANY, "&Activity", "Show Activity tab")
        workflows_item = view_menu.Append(wx.ID_ANY, "&Workflows", "Show Workflows tab")
        privacy_item = view_menu.Append(wx.ID_ANY, "&Privacy", "Show Privacy tab")
        settings_item = view_menu.Append(wx.ID_ANY, "&Settings", "Show Settings tab")
        debug_item = view_menu.Append(wx.ID_ANY, "&Debug", "Show Debug tab")
        
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(0), dashboard_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(1), storage_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(2), activity_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(3), workflows_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(4), privacy_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(5), settings_item)
        self.Bind(wx.EVT_MENU, lambda evt: self._notebook.SetSelection(6), debug_item)
        
        menubar.Append(view_menu, "&View")
        
        # Help menu
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About", "About AGI Assistant")
        self.Bind(wx.EVT_MENU, self._on_about, id=wx.ID_ABOUT)
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
        self._menubar = menubar
    
    # ---- UI construction ----
    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Header
        header = wx.Panel(panel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self._indicator = wx.StaticText(header, label="●")
        font = self._indicator.GetFont()
        font.SetPointSize(14)
        self._indicator.SetFont(font)
        self._indicator.SetForegroundColour(wx.Colour(128, 128, 128))
        hbox.Add(self._indicator, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)

        self._status_label = wx.StaticText(header, label="Ready")
        hbox.Add(self._status_label, 1, wx.ALIGN_CENTER_VERTICAL)

        self._start_stop = wx.Button(header, label="Start Recording")
        self._start_stop.Bind(wx.EVT_BUTTON, lambda evt: self.toggle_recording())
        hbox.Add(self._start_stop, flag=wx.LEFT, border=8)

        self._pause_resume = wx.Button(header, label="Pause")
        self._pause_resume.Enable(False)
        self._pause_resume.Bind(wx.EVT_BUTTON, lambda evt: self.toggle_pause())
        hbox.Add(self._pause_resume, flag=wx.LEFT, border=6)

        header.SetSizer(hbox)
        vbox.Add(header, flag=wx.EXPAND | wx.ALL, border=8)

        # Notebook with panel references
        self._notebook = wx.Notebook(panel)
        self._dashboard_panel = DashboardPanel(self._notebook)
        self._storage_panel = StoragePanel(self._notebook)
        self._activity_panel = ActivityPanel(self._notebook)
        self._workflows_panel = WorkflowsPanel(self._notebook)
        self._privacy_panel = PrivacyPanel(self._notebook)
        self._settings_panel = SettingsPanel(self._notebook)
        self._debug_panel = DebugPanel(self._notebook)
        
        self._notebook.AddPage(self._dashboard_panel, "Dashboard")
        self._notebook.AddPage(self._storage_panel, "Storage")
        self._notebook.AddPage(self._activity_panel, "Activity")
        self._notebook.AddPage(self._workflows_panel, "Workflows")
        self._notebook.AddPage(self._privacy_panel, "Privacy")
        self._notebook.AddPage(self._settings_panel, "Settings")
        self._notebook.AddPage(self._debug_panel, "Debug")
        
        # Refresh storage when switching to storage tab
        self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_tab_changed)
        
        vbox.Add(self._notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(vbox)

        # Status bar
        self._status_bar = self.CreateStatusBar(2)
        self._status_bar.SetStatusWidths([-2, -1])
        self._status_bar.SetStatusText("Ready - Local processing only", 0)

    # ---- Actions ----
    def toggle_recording(self) -> None:
        if not self._is_recording:
            self._is_recording = True
            self._is_paused = False
            self._session_start_time = datetime.now()
            if self.on_start_recording:
                self.on_start_recording()
        else:
            self._is_recording = False
            self._is_paused = False
            self._session_start_time = None
            if self.on_stop_recording:
                self.on_stop_recording()
        self._refresh_controls()

    def toggle_pause(self) -> None:
        if not self._is_recording:
            return
        self._is_paused = not self._is_paused
        if self._is_paused:
            if self.on_pause:
                self.on_pause()
        else:
            if self.on_resume:
                self.on_resume()
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        """Update all UI controls to reflect current recording state."""
        if self._is_recording and not self._is_paused:
            self._start_stop.SetLabel("Stop Recording")
            self._pause_resume.Enable(True)
            self._pause_resume.SetLabel("Pause")
            self._indicator.SetForegroundColour(wx.Colour(0, 128, 0))
            self._status_label.SetLabel("Recording")
            # Update menu
            if hasattr(self, '_menubar'):
                self.record_start.Enable(False)
                self.record_stop.Enable(True)
                self.record_pause.Enable(True)
                self.record_resume.Enable(False)
        elif self._is_recording and self._is_paused:
            self._start_stop.SetLabel("Stop Recording")
            self._pause_resume.Enable(True)
            self._pause_resume.SetLabel("Resume")
            self._indicator.SetForegroundColour(wx.Colour(255, 152, 0))
            self._status_label.SetLabel("Paused")
            # Update menu
            if hasattr(self, '_menubar'):
                self.record_start.Enable(False)
                self.record_stop.Enable(True)
                self.record_pause.Enable(False)
                self.record_resume.Enable(True)
        else:
            self._start_stop.SetLabel("Start Recording")
            self._pause_resume.Enable(False)
            self._pause_resume.SetLabel("Pause")
            self._indicator.SetForegroundColour(wx.Colour(128, 128, 128))
            self._status_label.SetLabel("Ready")
            # Update menu
            if hasattr(self, '_menubar'):
                self.record_start.Enable(True)
                self.record_stop.Enable(False)
                self.record_pause.Enable(False)
                self.record_resume.Enable(False)

    # ---- Events ----
    def _on_timer(self, evt: wx.TimerEvent) -> None:
        """Update elapsed time display when recording."""
        if self._is_recording and not self._is_paused and self._session_start_time:
            elapsed = datetime.now() - self._session_start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self._status_label.SetLabel(f"Recording - {time_str}")
            self._status_bar.SetStatusText(f"Recording session - {time_str} elapsed", 0)
    
    def _on_tab_changed(self, evt: wx.NotebookEvent) -> None:
        """Handle tab change - refresh data if needed."""
        page_idx = evt.GetSelection()
        if page_idx == 0:  # Dashboard tab
            # Refresh dashboard metrics
            wx.CallAfter(self.refresh_dashboard_metrics)
        elif page_idx == 1:  # Storage tab
            # Refresh storage stats when viewing storage tab
            wx.CallAfter(self.refresh_storage_stats)
        elif page_idx == 4:  # Privacy tab
            # Refresh sessions when viewing privacy tab
            wx.CallAfter(self.refresh_sessions)
        evt.Skip()
    
    def refresh_dashboard_metrics(self) -> None:
        """Refresh dashboard panel with real metrics."""
        if hasattr(self, '_dashboard_panel') and self._dashboard_panel:
            try:
                metrics_lines = []
                
                # Get action count (from current session if available)
                action_count = 0
                if self._current_session and hasattr(self._current_session, 'detected_actions'):
                    action_count = self._current_session.detected_actions
                
                # Get pattern count
                pattern_count = 0
                if self._storage_manager:
                    try:
                        # Use sync method if available
                        pattern_count = self._storage_manager._get_session_count_sync()  # Temporary - will use patterns when available
                    except:
                        pass
                
                # Get storage usage
                storage_mb = 0
                if self._storage_manager:
                    try:
                        usage = self._storage_manager.get_storage_usage()
                        storage_gb = usage.get('total_size_gb', 0)
                        storage_mb = int(storage_gb * 1024)
                    except:
                        pass
                
                # Get session count
                session_count = 0
                if self._storage_manager:
                    try:
                        session_count = self._storage_manager._get_session_count_sync()
                    except:
                        pass
                
                metrics_lines.append(f"• Total Actions: {action_count}")
                metrics_lines.append(f"• Patterns Detected: {pattern_count}")
                metrics_lines.append(f"• Storage Used: {storage_mb} MB")
                metrics_lines.append(f"• Total Sessions: {session_count}")
                
                self._dashboard_panel.metrics_info.SetLabel("\n".join(metrics_lines))
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.debug(f"Failed to refresh dashboard metrics: {e}")

    def _on_close(self, evt: wx.CloseEvent) -> None:
        # Hide to tray instead of closing (if tray available)
        if self._tray:
            self.Hide()
            if sys.platform == 'win32':
                try:
                    self._tray.ShowBalloon("AGI Assistant", "Application minimized to system tray")
                except Exception:
                    pass
            evt.Veto()  # prevent app from quitting; coordinator handles shutdown later
        else:
            # Stop communication layer
            if self._event_bridge:
                self._event_bridge.stop()
            if self._state_sync:
                self._state_sync.stop()
            
            # No tray available, allow normal close
            evt.Skip()

    def _bind_menu_id(self, func: Callable[[], None]) -> int:
        """Create a hidden menu item ID bound to the given function."""
        mid = wx.NewIdRef().GetId()
        self.Bind(wx.EVT_MENU, lambda evt: func(), id=mid)
        return mid
    
    def _on_exit(self, evt: wx.CommandEvent) -> None:
        """Handle exit menu item."""
        self.Close()
    
    def _on_about(self, evt: wx.CommandEvent) -> None:
        """Show about dialog."""
        info = wx.adv.AboutDialogInfo()
        info.SetName("AGI Assistant")
        info.SetVersion("1.0.0")
        info.SetDescription(
            "AI-Powered Workflow Automation\n\n"
            "Observes your work, learns patterns, and suggests automations.\n"
            "All processing happens locally on your machine."
        )
        info.SetCopyright("(C) 2024")
        wx.adv.AboutBox(info)


