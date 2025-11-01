"""Screen capture service using mss and opencv."""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Callable
import uuid

import mss
import cv2
import numpy as np
from PIL import Image
from pynput import mouse, keyboard

from src.config import get_config
from src.logger import get_screen_capture_logger
from src.models.capture import CaptureStatus
from src.services.event_system import (
    get_event_bus, EventType, 
    create_screenshot_event, create_video_segment_event, create_service_event
)


class ScreenCaptureService:
    """
    Screen capture service that continuously captures screenshots and video segments.
    
    Features:
    - Adaptive capture rate based on user activity
    - Screenshot capture every 2-5 seconds
    - Video segment recording (30-60 seconds)
    - Application exclusion support
    - Pause/resume functionality
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_screen_capture_logger()
        
        # State
        self._running = False
        self._paused = False
        self._capture_task: Optional[asyncio.Task] = None
        self._video_task: Optional[asyncio.Task] = None
        
        # Capture settings
        self.screenshot_interval = self.config.screen_capture.screenshot_interval
        self.video_duration = self.config.screen_capture.video_segment_duration
        self.resolution = (
            self.config.screen_capture.resolution_width,
            self.config.screen_capture.resolution_height
        )
        
        # Activity tracking
        self._last_activity = time.time()
        self._activity_threshold = 2.0  # seconds of inactivity before slowing capture
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # Exclusion list
        self._excluded_apps: List[str] = self.config.privacy.excluded_apps.copy()
        
        # Capture statistics
        self._frames_captured = 0
        self._current_segment = ""
        self._session_id = ""
        
        # Event system
        self.event_bus = get_event_bus()
        
        # MSS instance
        self._sct = mss.mss()
        
        # Video recording
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._video_start_time: Optional[datetime] = None
        self._current_video_path: Optional[Path] = None
        self._video_fps = self.config.screen_capture.video_fps
        self._video_codec = cv2.VideoWriter_fourcc(*self.config.screen_capture.video_codec)
        
        self.logger.info("Screen capture service initialized")
    
    async def start(self) -> None:
        """Start screen capture service."""
        if self._running:
            self.logger.warning("Screen capture already running")
            return
        
        self.logger.info("Starting screen capture service")
        self._running = True
        self._session_id = str(uuid.uuid4())
        
        # Ensure capture directories exist
        self._ensure_directories()
        
        # Start activity monitoring
        self._start_activity_monitoring()
        
        # Start capture tasks
        self._capture_task = asyncio.create_task(self._capture_loop())
        self._video_task = asyncio.create_task(self._video_loop())
        
        self.logger.info(f"Screen capture started for session: {self._session_id}")
    
    async def stop(self) -> None:
        """Stop screen capture service."""
        if not self._running:
            return
        
        self.logger.info("Stopping screen capture service")
        self._running = False
        
        # Stop activity monitoring
        self._stop_activity_monitoring()
        
        # Cancel tasks
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
        
        if self._video_task:
            self._video_task.cancel()
            try:
                await self._video_task
            except asyncio.CancelledError:
                pass
        
        # Close video writer
        await self._stop_video_recording()
        
        self.logger.info("Screen capture stopped")
    
    def pause(self) -> None:
        """Pause capture temporarily."""
        self._paused = True
        self.logger.info("Screen capture paused")
    
    def resume(self) -> None:
        """Resume capture."""
        self._paused = False
        self.logger.info("Screen capture resumed")
    
    def set_excluded_apps(self, apps: List[str]) -> None:
        """Set applications to exclude from capture."""
        self._excluded_apps = apps.copy()
        self.logger.info(f"Excluded apps updated: {apps}")
    
    def get_current_status(self) -> CaptureStatus:
        """Get current capture status."""
        return CaptureStatus(
            is_recording=self._running and not self._paused,
            current_segment=self._current_segment,
            frames_captured=self._frames_captured,
            active_window=self._get_active_window_title(),
            is_paused=self._paused
        )
    

    
    async def _capture_loop(self) -> None:
        """Main screenshot capture loop."""
        while self._running:
            try:
                if not self._paused and not self._is_excluded_app_active():
                    await self._capture_screenshot()
                
                # Adaptive interval based on activity
                interval = self._get_adaptive_interval()
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight error loop
    
    async def _video_loop(self) -> None:
        """Video segment recording loop with rotation."""
        while self._running:
            try:
                if not self._paused and not self._is_excluded_app_active():
                    # Record video segment
                    await self._record_video_segment()
                    
                    # Clean up old videos periodically
                    await self._cleanup_old_videos()
                    
                    # Small pause between segments
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(5)  # Longer pause when paused/excluded
                    
            except Exception as e:
                self.logger.error(f"Error in video loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Longer pause on error
    
    async def _capture_screenshot(self) -> None:
        """Capture a single screenshot."""
        try:
            # Get screenshot
            screenshot = self._sct.grab(self._sct.monitors[0])  # Primary monitor
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Resize if needed
            if img.size != self.resolution:
                img = img.resize(self.resolution, Image.Resampling.LANCZOS)
            
            # Generate filename
            timestamp = datetime.now()
            filename = f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.png"
            filepath = self._get_screenshot_path() / filename
            
            # Save screenshot
            img.save(str(filepath), "PNG")
            
            self._frames_captured += 1
            
            # Publish screenshot event
            event = create_screenshot_event(
                source="screen_capture",
                filepath=filepath,
                timestamp=timestamp,
                resolution=self.resolution,
                frames_captured=self._frames_captured
            )
            await self.event_bus.publish(event)
            
            self.logger.debug(f"Screenshot captured: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
    
    async def _record_video_segment(self) -> None:
        """Record a video segment using OpenCV VideoWriter."""
        try:
            # Start new video recording
            await self._start_video_recording()
            
            # Record for the specified duration
            frame_interval = 1.0 / self._video_fps
            frames_to_capture = int(self._video_fps * self.video_duration)
            
            for i in range(frames_to_capture):
                if not self._running or self._paused:
                    break
                
                # Capture and write frame
                await self._capture_video_frame()
                await asyncio.sleep(frame_interval)
            
            # Stop recording and finalize video
            await self._stop_video_recording()
            
        except Exception as e:
            self.logger.error(f"Failed to record video segment: {e}")
            # Ensure video writer is cleaned up on error
            await self._stop_video_recording()
    
    def _get_adaptive_interval(self) -> float:
        """Get adaptive capture interval based on user activity."""
        time_since_activity = time.time() - self._last_activity
        
        if time_since_activity < self._activity_threshold:
            # High activity - capture more frequently
            return max(self.screenshot_interval * 0.5, 1.0)
        else:
            # Low activity - capture less frequently
            return min(self.screenshot_interval * 2.0, 10.0)
    
    def _start_activity_monitoring(self) -> None:
        """Start monitoring mouse and keyboard activity."""
        try:
            self._mouse_listener = mouse.Listener(
                on_move=self._on_activity,
                on_click=self._on_activity,
                on_scroll=self._on_activity
            )
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_activity,
                on_release=self._on_activity
            )
            
            self._mouse_listener.start()
            self._keyboard_listener.start()
            
            self.logger.debug("Activity monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start activity monitoring: {e}")
    
    def _stop_activity_monitoring(self) -> None:
        """Stop activity monitoring."""
        try:
            if self._mouse_listener:
                self._mouse_listener.stop()
                self._mouse_listener = None
            
            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener = None
            
            self.logger.debug("Activity monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop activity monitoring: {e}")
    
    def _on_activity(self, *args) -> None:
        """Handle user activity event."""
        self._last_activity = time.time()
    
    def _is_excluded_app_active(self) -> bool:
        """Check if currently active application is in exclusion list."""
        try:
            active_window = self._get_active_window_title()
            
            for excluded_app in self._excluded_apps:
                if excluded_app.lower() in active_window.lower():
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check excluded app: {e}")
            return False
    
    def _get_active_window_title(self) -> str:
        """Get title of currently active window."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except ImportError:
            # Fallback if pywin32 not available
            return "Unknown"
        except Exception as e:
            self.logger.error(f"Failed to get active window: {e}")
            return "Unknown"
    
    def _ensure_directories(self) -> None:
        """Ensure capture directories exist."""
        paths = self.config.get_data_paths()
        
        # Create session directory
        session_date = datetime.now().strftime('%Y-%m-%d')
        session_dir = paths['sessions'] / session_date / f"session-{self._session_id[:8]}"
        
        screenshot_dir = session_dir / 'screenshots'
        video_dir = session_dir / 'video'
        
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        video_dir.mkdir(parents=True, exist_ok=True)
        
        self._screenshot_dir = screenshot_dir
        self._video_dir = video_dir
    
    def _get_screenshot_path(self) -> Path:
        """Get screenshot directory path."""
        return self._screenshot_dir
    
    def _get_video_path(self) -> Path:
        """Get video directory path."""
        return self._video_dir
    
    async def _start_video_recording(self) -> None:
        """Start a new video recording session."""
        try:
            # Stop any existing recording
            await self._stop_video_recording()
            
            # Generate video filename
            timestamp = datetime.now()
            video_filename = f"video_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            self._current_video_path = self._get_video_path() / video_filename
            
            # Initialize video writer
            self._video_writer = cv2.VideoWriter(
                str(self._current_video_path),
                self._video_codec,
                self._video_fps,
                self.resolution
            )
            
            if not self._video_writer.isOpened():
                raise RuntimeError("Failed to initialize video writer")
            
            self._video_start_time = timestamp
            self._current_segment = video_filename
            
            self.logger.info(f"Started video recording: {video_filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to start video recording: {e}")
            await self._stop_video_recording()
            raise
    
    async def _capture_video_frame(self) -> None:
        """Capture a single frame for video recording."""
        try:
            if not self._video_writer or not self._video_writer.isOpened():
                return
            
            # Capture screenshot
            screenshot = self._sct.grab(self._sct.monitors[0])
            
            # Convert to numpy array (BGR format for OpenCV)
            frame = np.frombuffer(screenshot.bgra, dtype=np.uint8)
            frame = frame.reshape((screenshot.height, screenshot.width, 4))
            
            # Convert BGRA to BGR (remove alpha channel)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Resize if needed
            if (frame_bgr.shape[1], frame_bgr.shape[0]) != self.resolution:
                frame_bgr = cv2.resize(frame_bgr, self.resolution)
            
            # Write frame to video
            self._video_writer.write(frame_bgr)
            
        except Exception as e:
            self.logger.error(f"Failed to capture video frame: {e}")
    
    async def _stop_video_recording(self) -> None:
        """Stop current video recording and publish event."""
        try:
            if self._video_writer is not None:
                self._video_writer.release()
                self._video_writer = None
                
                if self._current_video_path and self._current_video_path.exists():
                    # Calculate actual duration
                    duration = (datetime.now() - self._video_start_time).total_seconds() if self._video_start_time else 0
                    
                    # Get file size for compression info
                    file_size = self._current_video_path.stat().st_size
                    
                    # Publish video segment event
                    event = create_video_segment_event(
                        source="screen_capture",
                        segment_path=self._current_video_path,
                        start_time=self._video_start_time,
                        duration=duration,
                        fps=self._video_fps,
                        file_size_bytes=file_size,
                        codec="mp4v",
                        resolution=self.resolution
                    )
                    await self.event_bus.publish(event)
                    
                    self.logger.info(f"Video recording completed: {self._current_video_path.name} ({duration:.1f}s, {file_size/1024/1024:.1f}MB)")
                
                # Reset video state
                self._current_video_path = None
                self._video_start_time = None
                self._current_segment = ""
                
        except Exception as e:
            self.logger.error(f"Failed to stop video recording: {e}")
    
    async def _cleanup_old_videos(self) -> None:
        """Clean up old video files based on retention policy."""
        try:
            video_dir = self._get_video_path()
            if not video_dir.exists():
                return
            
            # Get all video files
            video_files = list(video_dir.glob("*.mp4"))
            
            # Sort by modification time (oldest first)
            video_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in video_files)
            max_size = self.config.storage.max_storage_gb * 1024 * 1024 * 1024 * 0.3  # 30% for videos
            
            # Remove oldest files if over limit
            while total_size > max_size and video_files:
                oldest_file = video_files.pop(0)
                file_size = oldest_file.stat().st_size
                oldest_file.unlink()
                total_size -= file_size
                self.logger.info(f"Cleaned up old video: {oldest_file.name}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old videos: {e}")
    
    def _detect_active_window_info(self) -> dict:
        """Detect active window information for better context."""
        try:
            import win32gui
            import win32process
            import psutil
            
            # Get active window
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get process info
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            return {
                'window_title': window_title,
                'process_name': process.name(),
                'process_id': pid,
                'executable_path': process.exe() if hasattr(process, 'exe') else None
            }
            
        except Exception as e:
            self.logger.debug(f"Could not detect window info: {e}")
            return {
                'window_title': 'Unknown',
                'process_name': 'Unknown',
                'process_id': None,
                'executable_path': None
            }