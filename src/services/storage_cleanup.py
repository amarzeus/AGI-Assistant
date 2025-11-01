"""Storage cleanup service with automatic cleanup logic."""

import asyncio
import gzip
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.services.event_system import get_event_bus, EventType, Event


class StorageCleanupService:
    """
    Automatic storage cleanup service.
    
    Features:
    - Automatic cleanup when usage exceeds 90% of limit
    - Retention priority: structured data > screenshots > videos
    - Compression for older data before deletion
    - Scheduled cleanup execution
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Storage configuration
        self.max_storage_gb = self.config.storage.max_storage_gb
        self.cleanup_threshold = self.config.storage.cleanup_threshold
        self.retention_days_structured = self.config.storage.retention_days_structured
        self.retention_days_screenshots = self.config.storage.retention_days_screenshots
        self.retention_days_video = self.config.storage.retention_days_video
        self.enable_compression = self.config.storage.enable_compression
        
        # Paths
        self.data_paths = self.config.get_data_paths()
        
        # Service state
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Cleanup settings
        self.cleanup_check_interval = 300  # Check every 5 minutes
        self.compression_age_days = 2  # Compress data older than 2 days
        
        # Storage manager
        self.storage_manager: Optional[StorageManager] = None
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._cleanup_runs = 0
        self._files_cleaned = 0
        self._bytes_freed = 0
        self._files_compressed = 0
        self._bytes_saved_compression = 0
        
        self.logger.info("Storage cleanup service initialized")
    
    async def initialize(self, storage_manager: StorageManager) -> None:
        """Initialize cleanup service."""
        self.logger.info("Initializing storage cleanup service...")
        self.storage_manager = storage_manager
        self.logger.info("Storage cleanup service initialized")
    
    async def start(self) -> None:
        """Start automatic cleanup service."""
        if self._running:
            self.logger.warning("Storage cleanup service already running")
            return
        
        self.logger.info("Starting storage cleanup service")
        self._running = True
        
        # Start cleanup loop
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Storage cleanup service started")
    
    async def stop(self) -> None:
        """Stop cleanup service."""
        if not self._running:
            return
        
        self.logger.info("Stopping storage cleanup service")
        self._running = False
        
        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Storage cleanup service stopped")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        self.logger.info("Storage cleanup loop started")
        
        try:
            while self._running:
                try:
                    # Check if cleanup is needed
                    await self._check_and_cleanup()
                    
                    # Wait for next check
                    await asyncio.sleep(self.cleanup_check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in cleanup loop: {e}")
                    await asyncio.sleep(60)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in cleanup loop: {e}")
        
        self.logger.info("Storage cleanup loop finished")
    
    async def _check_and_cleanup(self) -> None:
        """Check storage usage and trigger cleanup if needed."""
        try:
            # Calculate current usage
            total_usage_bytes = await self._calculate_total_usage()
            total_usage_gb = total_usage_bytes / (1024 ** 3)
            usage_ratio = total_usage_gb / self.max_storage_gb
            
            self.logger.debug(f"Storage usage: {total_usage_gb:.2f}GB / {self.max_storage_gb}GB ({usage_ratio:.1%})")
            
            # Check if cleanup is needed
            if usage_ratio >= self.cleanup_threshold:
                self.logger.warning(
                    f"Storage usage ({usage_ratio:.1%}) exceeds threshold ({self.cleanup_threshold:.1%}). "
                    f"Triggering cleanup..."
                )
                
                # Perform cleanup
                await self.execute_cleanup()
                
        except Exception as e:
            self.logger.error(f"Error checking storage usage: {e}")
    
    async def execute_cleanup(self) -> Dict[str, Any]:
        """
        Execute storage cleanup with retention priority.
        
        Priority order:
        1. Delete oldest videos first (lowest priority data)
        2. Delete oldest screenshots second
        3. Keep structured data (highest priority)
        4. Compress older data before deletion if enabled
        
        Returns:
            Dictionary with cleanup results
        """
        start_time = datetime.now()
        
        try:
            self.logger.info("Starting storage cleanup execution")
            
            # Initialize counters
            total_files_cleaned = 0
            total_bytes_freed = 0
            
            # Step 1: Compress older data if enabled
            if self.enable_compression:
                compression_results = await self._compress_older_data()
                self._files_compressed += compression_results["files_compressed"]
                self._bytes_saved_compression += compression_results["bytes_saved"]
                self.logger.info(
                    f"Compressed {compression_results['files_compressed']} files, "
                    f"saved {compression_results['bytes_saved'] / (1024**2):.1f}MB"
                )
            
            # Step 2: Clean up old videos (lowest priority)
            video_results = await self._cleanup_old_videos()
            total_files_cleaned += video_results["files_cleaned"]
            total_bytes_freed += video_results["bytes_freed"]
            self.logger.info(
                f"Cleaned {video_results['files_cleaned']} video files, "
                f"freed {video_results['bytes_freed'] / (1024**2):.1f}MB"
            )
            
            # Step 3: Clean up old screenshots (medium priority)
            screenshot_results = await self._cleanup_old_screenshots()
            total_files_cleaned += screenshot_results["files_cleaned"]
            total_bytes_freed += screenshot_results["bytes_freed"]
            self.logger.info(
                f"Cleaned {screenshot_results['files_cleaned']} screenshot files, "
                f"freed {screenshot_results['bytes_freed'] / (1024**2):.1f}MB"
            )
            
            # Step 4: Clean up old logs
            log_results = await self._cleanup_old_logs()
            total_files_cleaned += log_results["files_cleaned"]
            total_bytes_freed += log_results["bytes_freed"]
            
            # Step 5: Clean up orphaned database records
            db_results = await self._cleanup_orphaned_records()
            
            # Update statistics
            self._cleanup_runs += 1
            self._files_cleaned += total_files_cleaned
            self._bytes_freed += total_bytes_freed
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"Cleanup completed: {total_files_cleaned} files, "
                f"{total_bytes_freed / (1024**2):.1f}MB freed in {duration:.1f}s"
            )
            
            # Publish cleanup event
            event = Event(
                type=EventType.STORAGE_CLEANUP_COMPLETED,
                timestamp=datetime.now(),
                source="storage_cleanup",
                data={
                    "files_cleaned": total_files_cleaned,
                    "bytes_freed": total_bytes_freed,
                    "duration": duration,
                    "cleanup_run": self._cleanup_runs
                }
            )
            await self.event_bus.publish(event)
            
            return {
                "success": True,
                "files_cleaned": total_files_cleaned,
                "bytes_freed": total_bytes_freed,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Error executing cleanup: {e}")
            return {
                "success": False,
                "error": str(e),
                "files_cleaned": 0,
                "bytes_freed": 0
            }
    
    async def _compress_older_data(self) -> Dict[str, Any]:
        """
        Compress older data files before deletion.
        
        Compresses screenshots and videos older than compression_age_days.
        """
        files_compressed = 0
        bytes_saved = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.compression_age_days)
            sessions_path = self.data_paths['sessions']
            
            if not sessions_path.exists():
                return {"files_compressed": 0, "bytes_saved": 0}
            
            # Compress old screenshots
            for screenshot_file in sessions_path.rglob('*.png'):
                try:
                    file_time = datetime.fromtimestamp(screenshot_file.stat().st_mtime)
                    
                    # Check if file is old enough and not already compressed
                    if file_time < cutoff_date and not screenshot_file.with_suffix('.png.gz').exists():
                        original_size = screenshot_file.stat().st_size
                        
                        # Compress file
                        compressed_path = screenshot_file.with_suffix('.png.gz')
                        with open(screenshot_file, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb', compresslevel=6) as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        compressed_size = compressed_path.stat().st_size
                        
                        # Delete original if compression successful
                        if compressed_size < original_size:
                            screenshot_file.unlink()
                            files_compressed += 1
                            bytes_saved += (original_size - compressed_size)
                        else:
                            # Compression didn't help, remove compressed file
                            compressed_path.unlink()
                            
                except Exception as e:
                    self.logger.error(f"Error compressing {screenshot_file}: {e}")
            
            return {"files_compressed": files_compressed, "bytes_saved": bytes_saved}
            
        except Exception as e:
            self.logger.error(f"Error in compression: {e}")
            return {"files_compressed": 0, "bytes_saved": 0}
    
    async def _cleanup_old_videos(self) -> Dict[str, Any]:
        """Clean up old video files based on retention policy."""
        files_cleaned = 0
        bytes_freed = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days_video)
            sessions_path = self.data_paths['sessions']
            
            if not sessions_path.exists():
                return {"files_cleaned": 0, "bytes_freed": 0}
            
            # Find and delete old video files
            for video_file in sessions_path.rglob('*.mp4'):
                try:
                    file_time = datetime.fromtimestamp(video_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        file_size = video_file.stat().st_size
                        video_file.unlink()
                        files_cleaned += 1
                        bytes_freed += file_size
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning video {video_file}: {e}")
            
            return {"files_cleaned": files_cleaned, "bytes_freed": bytes_freed}
            
        except Exception as e:
            self.logger.error(f"Error cleaning up videos: {e}")
            return {"files_cleaned": 0, "bytes_freed": 0}
    
    async def _cleanup_old_screenshots(self) -> Dict[str, Any]:
        """Clean up old screenshot files based on retention policy."""
        files_cleaned = 0
        bytes_freed = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days_screenshots)
            sessions_path = self.data_paths['sessions']
            
            if not sessions_path.exists():
                return {"files_cleaned": 0, "bytes_freed": 0}
            
            # Find and delete old screenshot files (including compressed ones)
            for screenshot_file in sessions_path.rglob('*.png*'):
                try:
                    file_time = datetime.fromtimestamp(screenshot_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        file_size = screenshot_file.stat().st_size
                        screenshot_file.unlink()
                        files_cleaned += 1
                        bytes_freed += file_size
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning screenshot {screenshot_file}: {e}")
            
            return {"files_cleaned": files_cleaned, "bytes_freed": bytes_freed}
            
        except Exception as e:
            self.logger.error(f"Error cleaning up screenshots: {e}")
            return {"files_cleaned": 0, "bytes_freed": 0}
    
    async def _cleanup_old_logs(self) -> Dict[str, Any]:
        """Clean up old log files."""
        files_cleaned = 0
        bytes_freed = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=7)  # Keep logs for 7 days
            logs_path = self.data_paths['logs']
            
            if not logs_path.exists():
                return {"files_cleaned": 0, "bytes_freed": 0}
            
            for log_file in logs_path.glob('*.log*'):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        files_cleaned += 1
                        bytes_freed += file_size
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning log {log_file}: {e}")
            
            return {"files_cleaned": files_cleaned, "bytes_freed": bytes_freed}
            
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {e}")
            return {"files_cleaned": 0, "bytes_freed": 0}
    
    async def _cleanup_orphaned_records(self) -> Dict[str, Any]:
        """Clean up orphaned database records."""
        records_cleaned = 0
        
        try:
            if not self.storage_manager:
                return {"records_cleaned": 0}
            
            cutoff_date = datetime.now() - timedelta(days=self.retention_days_structured)
            
            # Clean up old database records
            await self.storage_manager.cleanup_old_data(cutoff_date)
            
            records_cleaned = 1  # Placeholder
            
            return {"records_cleaned": records_cleaned}
            
        except Exception as e:
            self.logger.error(f"Error cleaning up database records: {e}")
            return {"records_cleaned": 0}
    
    async def _calculate_total_usage(self) -> int:
        """Calculate total storage usage in bytes."""
        total_bytes = 0
        
        try:
            # Database
            db_path = self.data_paths['db'] / 'agi_assistant.db'
            if db_path.exists():
                total_bytes += db_path.stat().st_size
            
            # Sessions (screenshots and videos)
            sessions_path = self.data_paths['sessions']
            if sessions_path.exists():
                for file_path in sessions_path.rglob('*'):
                    if file_path.is_file():
                        total_bytes += file_path.stat().st_size
            
            # Logs
            logs_path = self.data_paths['logs']
            if logs_path.exists():
                for file_path in logs_path.rglob('*'):
                    if file_path.is_file():
                        total_bytes += file_path.stat().st_size
            
            return total_bytes
            
        except Exception as e:
            self.logger.error(f"Error calculating total usage: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup service statistics."""
        return {
            "running": self._running,
            "cleanup_runs": self._cleanup_runs,
            "files_cleaned": self._files_cleaned,
            "bytes_freed": self._bytes_freed,
            "files_compressed": self._files_compressed,
            "bytes_saved_compression": self._bytes_saved_compression,
            "retention_policy": {
                "structured_days": self.retention_days_structured,
                "screenshots_days": self.retention_days_screenshots,
                "video_days": self.retention_days_video
            },
            "compression_enabled": self.enable_compression,
            "cleanup_threshold": self.cleanup_threshold,
            "max_storage_gb": self.max_storage_gb
        }
    
    def is_running(self) -> bool:
        """Check if cleanup service is running."""
        return self._running

    def run_cleanup(self) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute_cleanup for UI usage.
        
        Returns:
            Dictionary with cleanup results including files_removed and space_freed_mb
        """
        try:
            # Run cleanup in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.execute_cleanup())
            loop.close()
            
            # Convert to UI-friendly format
            return {
                'success': result.get('success', False),
                'files_removed': result.get('files_cleaned', 0),
                'space_freed_mb': result.get('bytes_freed', 0) / (1024 ** 2),
                'duration': result.get('duration', 0)
            }
        except Exception as e:
            self.logger.error(f"Error in run_cleanup: {e}")
            return {
                'success': False,
                'files_removed': 0,
                'space_freed_mb': 0,
                'error': str(e)
            }
