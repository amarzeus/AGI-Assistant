"""Test storage cleanup service."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.services.storage_cleanup import StorageCleanupService
from src.database.storage_manager import StorageManager
from src.config import get_config, set_config, AppConfig


async def test_cleanup_service():
    """Test storage cleanup service."""
    print("Testing Storage Cleanup Service")
    print("=" * 50)
    
    # Create temporary data directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temp directory: {temp_dir}")
    
    try:
        # Configure with temp directory
        config = AppConfig()
        config.data_dir = temp_dir
        config.storage.max_storage_gb = 1  # 1GB limit for testing
        config.storage.cleanup_threshold = 0.5  # 50% threshold
        config.storage.retention_days_video = 1
        config.storage.retention_days_screenshots = 3
        config.storage.retention_days_structured = 7
        config.storage.enable_compression = True
        set_config(config)
        config.ensure_directories()
        
        # Initialize storage manager
        storage_manager = StorageManager()
        await storage_manager.initialize()
        
        # Initialize cleanup service
        cleanup_service = StorageCleanupService()
        await cleanup_service.initialize(storage_manager)
        
        print("\n1. Creating test data...")
        
        # Create test session directories with old files
        sessions_path = temp_dir / 'sessions'
        sessions_path.mkdir(exist_ok=True)
        
        # Create old video files (should be cleaned)
        old_video_dir = sessions_path / 'session-old' / 'video'
        old_video_dir.mkdir(parents=True, exist_ok=True)
        old_video_file = old_video_dir / 'old_video.mp4'
        old_video_file.write_text("old video data" * 1000)
        
        # Set old modification time
        old_time = (datetime.now() - timedelta(days=5)).timestamp()
        old_video_file.touch()
        import os
        os.utime(old_video_file, (old_time, old_time))
        
        # Create old screenshot files (should be cleaned)
        old_screenshot_dir = sessions_path / 'session-old' / 'screenshots'
        old_screenshot_dir.mkdir(parents=True, exist_ok=True)
        old_screenshot_file = old_screenshot_dir / 'old_screenshot.png'
        old_screenshot_file.write_text("old screenshot data" * 1000)
        os.utime(old_screenshot_file, (old_time, old_time))
        
        # Create recent files (should be kept)
        recent_video_dir = sessions_path / 'session-recent' / 'video'
        recent_video_dir.mkdir(parents=True, exist_ok=True)
        recent_video_file = recent_video_dir / 'recent_video.mp4'
        recent_video_file.write_text("recent video data" * 1000)
        
        recent_screenshot_dir = sessions_path / 'session-recent' / 'screenshots'
        recent_screenshot_dir.mkdir(parents=True, exist_ok=True)
        recent_screenshot_file = recent_screenshot_dir / 'recent_screenshot.png'
        recent_screenshot_file.write_text("recent screenshot data" * 1000)
        
        print(f"   Created old video: {old_video_file.exists()}")
        print(f"   Created old screenshot: {old_screenshot_file.exists()}")
        print(f"   Created recent video: {recent_video_file.exists()}")
        print(f"   Created recent screenshot: {recent_screenshot_file.exists()}")
        
        print("\n2. Calculating initial storage usage...")
        initial_usage = await cleanup_service._calculate_total_usage()
        print(f"   Initial usage: {initial_usage / (1024**2):.2f} MB")
        
        print("\n3. Executing cleanup...")
        cleanup_results = await cleanup_service.execute_cleanup()
        
        print(f"   Success: {cleanup_results.get('success', False)}")
        print(f"   Files cleaned: {cleanup_results.get('files_cleaned', 0)}")
        print(f"   Bytes freed: {cleanup_results.get('bytes_freed', 0) / (1024**2):.2f} MB")
        print(f"   Duration: {cleanup_results.get('duration', 0):.2f}s")
        
        print("\n4. Verifying cleanup results...")
        print(f"   Old video exists: {old_video_file.exists()} (should be False)")
        print(f"   Old screenshot exists: {old_screenshot_file.exists()} (should be False)")
        print(f"   Recent video exists: {recent_video_file.exists()} (should be True)")
        print(f"   Recent screenshot exists: {recent_screenshot_file.exists()} (should be True)")
        
        print("\n5. Calculating final storage usage...")
        final_usage = await cleanup_service._calculate_total_usage()
        print(f"   Final usage: {final_usage / (1024**2):.2f} MB")
        print(f"   Space freed: {(initial_usage - final_usage) / (1024**2):.2f} MB")
        
        print("\n6. Getting cleanup statistics...")
        stats = cleanup_service.get_stats()
        print(f"   Cleanup runs: {stats['cleanup_runs']}")
        print(f"   Total files cleaned: {stats['files_cleaned']}")
        print(f"   Total bytes freed: {stats['bytes_freed'] / (1024**2):.2f} MB")
        print(f"   Files compressed: {stats['files_compressed']}")
        print(f"   Compression enabled: {stats['compression_enabled']}")
        
        print("\n7. Testing automatic cleanup loop...")
        await cleanup_service.start()
        print("   Cleanup service started")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        await cleanup_service.stop()
        print("   Cleanup service stopped")
        
        # Cleanup
        await storage_manager.close()
        
        print("\n✓ Storage cleanup service test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temp directory: {temp_dir}")


if __name__ == "__main__":
    asyncio.run(test_cleanup_service())
