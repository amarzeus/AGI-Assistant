#!/usr/bin/env python3
"""
Simple test script to verify video recording functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.screen_capture import ScreenCaptureService
from src.config import get_config


async def test_video_recording():
    """Test video recording for a short duration."""
    print("Testing video recording functionality...")
    
    # Initialize service
    service = ScreenCaptureService()
    
    try:
        # Start service
        print("Starting screen capture service...")
        await service.start()
        
        # Let it run for 10 seconds
        print("Recording for 10 seconds...")
        await asyncio.sleep(10)
        
        # Stop service
        print("Stopping service...")
        await service.stop()
        
        # Check if video files were created
        config = get_config()
        paths = config.get_data_paths()
        
        print(f"Checking for video files in: {paths['sessions']}")
        
        video_files = list(paths['sessions'].rglob("*.mp4"))
        if video_files:
            print(f"✓ Video recording successful! Created {len(video_files)} video file(s):")
            for video_file in video_files:
                size_mb = video_file.stat().st_size / (1024 * 1024)
                print(f"  - {video_file.name} ({size_mb:.2f} MB)")
        else:
            print("✗ No video files found")
        
        # Check for screenshot files
        screenshot_files = list(paths['sessions'].rglob("*.png"))
        if screenshot_files:
            print(f"✓ Screenshot capture successful! Created {len(screenshot_files)} screenshot(s)")
        else:
            print("✗ No screenshot files found")
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_video_recording())