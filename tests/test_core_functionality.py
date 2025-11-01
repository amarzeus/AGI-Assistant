#!/usr/bin/env python3
"""
Test core functionality without audio dependencies.
This tests the application coordinator and event system.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.application_coordinator import ApplicationCoordinator
from src.services.event_system import get_event_bus, EventType, Event
from src.config import get_config


async def test_core_system():
    """Test the core application system without audio."""
    print("Testing AGI Assistant core functionality...")
    
    try:
        # Test configuration
        print("\n1. Testing configuration...")
        config = get_config()
        print(f"✓ Config loaded: {config.app_name}")
        print(f"✓ Data directory: {config.data_dir}")
        print(f"✓ Screen capture interval: {config.screen_capture.screenshot_interval}s")
        print(f"✓ Video segment duration: {config.screen_capture.video_segment_duration}s")
        
        # Test event system
        print("\n2. Testing event system...")
        event_bus = get_event_bus()
        print("✓ Event bus created")
        
        # Create test event
        test_event = Event(
            type=EventType.SERVICE_STARTED,
            timestamp=datetime.now(),
            source="test",
            data={"service_name": "test_service"}
        )
        
        # Test event publishing
        success = await event_bus.publish(test_event)
        print(f"✓ Event published: {success}")
        
        # Test event history
        history = event_bus.get_event_history()
        print(f"✓ Event history: {len(history)} events")
        
        # Test queue stats
        stats = event_bus.get_all_stats()
        print(f"✓ Queue stats: {len(stats)} queues")
        
        # Test application coordinator (without starting services)
        print("\n3. Testing application coordinator...")
        coordinator = ApplicationCoordinator()
        print("✓ Application coordinator created")
        
        # Test service health
        health = coordinator.get_service_health()
        print(f"✓ Service health check: {len(health)} services")
        
        print("\n✅ Core system test completed successfully!")
        print("\n📝 Next steps to test audio:")
        print("1. Install Visual Studio Build Tools from:")
        print("   https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("2. Then run: pip install pyaudio faster-whisper webrtcvad")
        print("3. Finally run: python test_transcription.py")
        
        return True
        
    except Exception as e:
        print(f"✗ Core system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    from datetime import datetime
    success = asyncio.run(test_core_system())
    if success:
        print("\n🎉 Core system is working correctly!")
    else:
        print("\n❌ Core system has issues.")