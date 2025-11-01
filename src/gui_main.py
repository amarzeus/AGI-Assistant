"""wxPython GUI entry point."""

import sys
import ctypes
from pathlib import Path

import wx

# Add src to path for logging/config access
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_app_logger
from src.config import get_config
from src.wxui.main_frame import MainFrame

# Lazy import of coordinator to allow demo mode if dependencies missing
ApplicationCoordinator = None
try:
    from src.services.application_coordinator import ApplicationCoordinator
except ImportError as e:
    # Coordinator may fail to import if backend dependencies missing
    # This is OK - GUI will run in demo mode
    pass


def _enable_windows_dpi_awareness() -> None:
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor v2
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def _set_windows_app_user_model_id() -> None:
    if sys.platform == 'win32':
        try:
            # Set AppUserModelID for proper taskbar grouping and notifications
            app_id = "AGIAssistant.App"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def _bootstrap() -> None:
    """Initialize the GUI (synchronous version)."""
    logger = get_app_logger()
    config = get_config()
    config.ensure_directories()

    # Create main frame
    frame = MainFrame(None)
    frame.Show()

    # Try to initialize coordinator (may fail if dependencies missing)
    try:
        if ApplicationCoordinator is None:
            raise ImportError("ApplicationCoordinator not available - missing backend dependencies")

        coordinator = ApplicationCoordinator()
        coordinator.set_gui_port(frame)

        # Wire GUI callbacks to coordinator actions (synchronous versions)
        def start_recording():
            try:
                # Create a new event loop for this async call
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coordinator.start())
                loop.close()
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                wx.MessageBox(f"Failed to start recording:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)

        def stop_recording():
            try:
                # Create a new event loop for this async call
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coordinator.stop())
                loop.close()
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
                wx.MessageBox(f"Failed to stop recording:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)

        def pause_recording():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coordinator.pause_capture())
                loop.close()
            except Exception as e:
                logger.error(f"Failed to pause recording: {e}")

        def resume_recording():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coordinator.resume_capture())
                loop.close()
            except Exception as e:
                logger.error(f"Failed to resume recording: {e}")

        frame.on_start_recording = start_recording
        frame.on_stop_recording = stop_recording
        frame.on_pause = pause_recording
        frame.on_resume = resume_recording

        # Set coordinator reference for panel access
        frame.set_coordinator(coordinator)

        # Load initial settings into settings panel
        try:
            config = get_config()
            frame._settings_panel.interval.SetValue(config.screen_capture.screenshot_interval)
            frame._settings_panel.chk_screen.SetValue(True)
            frame._settings_panel.sample_rate.SetValue(config.audio.sample_rate)
            frame._settings_panel.chk_transcription.SetValue(config.audio.enabled)
            frame._settings_panel.storage_limit.SetValue(config.storage.max_storage_gb)
        except Exception as e:
            logger.debug(f"Could not load initial settings: {e}")

        logger.info("GUI initialized - ready for user interaction")

    except Exception as e:
        logger.warning(f"Could not start coordinator (some dependencies may be missing): {e}")
        logger.info("GUI is running in demo mode - controls will not function without full dependencies")
        # Show message to user in status bar
        frame._status_bar.SetStatusText("Demo mode - Install dependencies for full functionality", 0)


def main() -> None:
    _enable_windows_dpi_awareness()
    _set_windows_app_user_model_id()

    # Create standard wx app (no asyncio needed for demo mode)
    app = wx.App(False)
    app.SetAppDisplayName("AGI Assistant")

    # Initialize GUI synchronously
    _bootstrap()

    # Run the wx main loop
    app.MainLoop()


if __name__ == "__main__":
    main()
