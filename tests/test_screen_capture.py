"""Tests for screen capture service."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.screen_capture import ScreenCaptureService
from src.models.capture import CaptureStatus


class TestScreenCaptureService:
    """Test ScreenCaptureService."""
    
    @pytest.fixture
    def capture_service(self):
        """Create screen capture service for testing."""
        with patch('src.services.screen_capture.mss.mss') as mock_mss:
            # Mock MSS
            mock_sct = MagicMock()
            mock_sct.monitors = [{'top': 0, 'left': 0, 'width': 1920, 'height': 1080}]
            mock_sct.grab.return_value = MagicMock()
            mock_mss.return_value = mock_sct
            
            service = ScreenCaptureService()
            yield service
    
    def test_service_initialization(self, capture_service):
        """Test service initializes correctly."""
        assert not capture_service._running
        assert not capture_service._paused
        assert capture_service._frames_captured == 0
    
    def test_pause_resume(self, capture_service):
        """Test pause and resume functionality."""
        capture_service.pause()
        assert capture_service._paused
        
        capture_service.resume()
        assert not capture_service._paused
    
    def test_excluded_apps(self, capture_service):
        """Test excluded apps functionality."""
        apps = ['KeePass', '1Password']
        capture_service.set_excluded_apps(apps)
        assert capture_service._excluded_apps == apps
    
    def test_get_status(self, capture_service):
        """Test getting capture status."""
        status = capture_service.get_current_status()
        assert isinstance(status, CaptureStatus)
        assert not status.is_recording
        assert status.frames_captured == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, capture_service):
        """Test starting and stopping capture."""
        with patch.object(capture_service, '_ensure_directories'), \
             patch.object(capture_service, '_start_activity_monitoring'), \
             patch.object(capture_service, '_stop_activity_monitoring'):
            
            # Start service
            await capture_service.start()
            assert capture_service._running
            
            # Stop service
            await capture_service.stop()
            assert not capture_service._running
    
    def test_adaptive_interval(self, capture_service):
        """Test adaptive capture interval."""
        import time
        
        # Recent activity - should be faster
        capture_service._last_activity = time.time()
        interval = capture_service._get_adaptive_interval()
        assert interval <= capture_service.screenshot_interval
        
        # Old activity - should be slower
        capture_service._last_activity = time.time() - 10
        interval = capture_service._get_adaptive_interval()
        assert interval >= capture_service.screenshot_interval
    
    @patch('src.services.screen_capture.Image.frombytes')
    async def test_capture_screenshot(self, mock_frombytes, capture_service):
        """Test screenshot capture."""
        # Mock image data
        mock_img = MagicMock()
        mock_img.size = (1920, 1080)
        mock_img.resize.return_value = mock_img
        mock_frombytes.return_value = mock_img
        
        # Setup directories
        with tempfile.TemporaryDirectory() as temp_dir:
            capture_service._screenshot_dir = Path(temp_dir)
            
            # Capture screenshot
            await capture_service._capture_screenshot()
            
            # Verify screenshot was saved
            mock_img.save.assert_called_once()
            assert capture_service._frames_captured == 1
    
    def test_activity_monitoring(self, capture_service):
        """Test activity monitoring setup."""
        with patch('src.services.screen_capture.mouse.Listener') as mock_mouse, \
             patch('src.services.screen_capture.keyboard.Listener') as mock_keyboard:
            
            mock_mouse_listener = MagicMock()
            mock_keyboard_listener = MagicMock()
            mock_mouse.return_value = mock_mouse_listener
            mock_keyboard.return_value = mock_keyboard_listener
            
            # Start monitoring
            capture_service._start_activity_monitoring()
            
            mock_mouse_listener.start.assert_called_once()
            mock_keyboard_listener.start.assert_called_once()
            
            # Stop monitoring
            capture_service._stop_activity_monitoring()
            
            mock_mouse_listener.stop.assert_called_once()
            mock_keyboard_listener.stop.assert_called_once()
    
    def test_on_activity(self, capture_service):
        """Test activity callback."""
        import time
        
        old_time = capture_service._last_activity
        time.sleep(0.01)  # Small delay
        
        capture_service._on_activity()
        
        assert capture_service._last_activity > old_time
    
    @patch('src.services.screen_capture.win32gui.GetForegroundWindow')
    @patch('src.services.screen_capture.win32gui.GetWindowText')
    def test_get_active_window(self, mock_get_text, mock_get_window, capture_service):
        """Test getting active window title."""
        mock_get_window.return_value = 12345
        mock_get_text.return_value = "Test Window"
        
        title = capture_service._get_active_window_title()
        assert title == "Test Window"
    
    def test_is_excluded_app_active(self, capture_service):
        """Test excluded app detection."""
        capture_service._excluded_apps = ['KeePass', 'Password']
        
        with patch.object(capture_service, '_get_active_window_title', return_value='KeePass - Database'):
            assert capture_service._is_excluded_app_active()
        
        with patch.object(capture_service, '_get_active_window_title', return_value='Chrome Browser'):
            assert not capture_service._is_excluded_app_active()