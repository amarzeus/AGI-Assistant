"""Basic integration tests."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.screen_capture import ScreenCaptureService
from src.services.hotkey_manager import HotkeyManager


class TestBasicIntegration:
    """Test basic integration between components."""
    
    @pytest.mark.asyncio
    async def test_screen_capture_basic_flow(self):
        """Test basic screen capture flow."""
        with patch('src.services.screen_capture.mss.mss') as mock_mss:
            # Mock MSS
            mock_sct = MagicMock()
            mock_sct.monitors = [{'top': 0, 'left': 0, 'width': 1920, 'height': 1080}]
            
            # Mock screenshot data
            mock_screenshot = MagicMock()
            mock_screenshot.size = (1920, 1080)
            mock_screenshot.bgra = b'test_data' * 1000  # Mock image data
            mock_sct.grab.return_value = mock_screenshot
            mock_mss.return_value = mock_sct
            
            # Mock PIL Image
            with patch('src.services.screen_capture.Image.frombytes') as mock_frombytes:
                mock_img = MagicMock()
                mock_img.size = (1920, 1080)
                mock_img.resize.return_value = mock_img
                mock_frombytes.return_value = mock_img
                
                # Create service
                service = ScreenCaptureService()
                
                # Test basic functionality
                assert not service._running
                
                # Mock directory creation
                with patch.object(service, '_ensure_directories'), \
                     patch.object(service, '_start_activity_monitoring'), \
                     patch.object(service, '_stop_activity_monitoring'):
                    
                    # Start service
                    await service.start()
                    assert service._running
                    
                    # Test status
                    status = service.get_current_status()
                    assert status.is_recording
                    
                    # Test pause/resume
                    service.pause()
                    assert service._paused
                    
                    service.resume()
                    assert not service._paused
                    
                    # Stop service
                    await service.stop()
                    assert not service._running
    
    def test_hotkey_manager_basic(self):
        """Test hotkey manager basic functionality."""
        with patch('src.services.hotkey_manager.keyboard.GlobalHotKeys') as mock_hotkeys:
            mock_listener = MagicMock()
            mock_hotkeys.return_value = mock_listener
            
            # Create manager
            manager = HotkeyManager()
            
            # Set callback
            callback_called = False
            def test_callback():
                nonlocal callback_called
                callback_called = True
            
            manager.set_pause_callback(test_callback)
            
            # Start listening
            manager.start()
            assert manager._running
            mock_listener.start.assert_called_once()
            
            # Test hotkey parsing
            parsed = manager._parse_hotkey('ctrl+shift+p')
            assert parsed == '<ctrl>+<shift>+p'
            
            # Stop listening
            manager.stop()
            assert not manager._running
            mock_listener.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_screen_capture_with_callbacks(self):
        """Test screen capture with callbacks."""
        with patch('src.services.screen_capture.mss.mss') as mock_mss, \
             patch('src.services.screen_capture.Image.frombytes') as mock_frombytes:
            
            # Setup mocks
            mock_sct = MagicMock()
            mock_sct.monitors = [{'top': 0, 'left': 0, 'width': 1920, 'height': 1080}]
            mock_screenshot = MagicMock()
            mock_screenshot.size = (1920, 1080)
            mock_screenshot.bgra = b'test_data' * 1000
            mock_sct.grab.return_value = mock_screenshot
            mock_mss.return_value = mock_sct
            
            mock_img = MagicMock()
            mock_img.size = (1920, 1080)
            mock_img.resize.return_value = mock_img
            mock_frombytes.return_value = mock_img
            
            # Create service
            service = ScreenCaptureService()
            
            # Setup callbacks
            screenshot_called = False
            video_called = False
            
            async def screenshot_callback(filepath, timestamp, img):
                nonlocal screenshot_called
                screenshot_called = True
            
            async def video_callback(filepath, timestamp, duration):
                nonlocal video_called
                video_called = True
            
            service.set_screenshot_callback(screenshot_callback)
            service.set_video_callback(video_callback)
            
            # Test screenshot capture
            with tempfile.TemporaryDirectory() as temp_dir:
                service._screenshot_dir = Path(temp_dir)
                await service._capture_screenshot()
                
                assert screenshot_called
                assert service._frames_captured == 1