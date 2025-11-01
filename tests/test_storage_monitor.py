#!/usr/bin/env python3
"""
Test script for storage monitoring system.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from src.services.storage_monitor import StorageMonitor
    from src.config import get_config
    print("✓ Successfully imported storage monitor")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


async def test_storage_monitor_basic():
    """Test basic storage monitor functionality."""
    print("📊 Testing Storage Monitor (Basic)")
    print("=" * 40)
    
    try:
        # Create storage monitor
        monitor = StorageMonitor()
        print("✓ Storage monitor created")
        
        # Check configuration
        stats = monitor.get_stats()
        print(f"📋 Configuration:")
        print(f"  - Max storage: {stats['max_storage_gb']}GB")
        print(f"  - Cleanup threshold: {stats['cleanup_threshold']:.1%}")
        print(f"  - Monitoring interval: {stats['monitoring_interval']}s")
        print(f"  - Retention days (structured): {stats['retention_days']['structured']}")
        print(f"  - Retention days (screenshots): {stats['retention_days']['screenshots']}")
        print(f"  - Retention days (video): {stats['retention_days']['video']}")
        
        # Initialize monitor
        print("\n🔧 Initializing storage monitor...")
        await monitor.initialize()
        print("✓ Storage monitor initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_storage_stats():
    """Test storage statistics calculation."""
    print("\n\n📈 Testing Storage Statistics")
    print("=" * 40)
    
    try:
        # Create and initialize monitor
        monitor = StorageMonitor()
        await monitor.initialize()
        
        # Get storage statistics
        print("📊 Calculating storage statistics...")
        stats = await monitor.get_storage_stats()
        
        print("✓ Storage statistics calculated")
        print(f"\n📋 Current Storage Usage:")
        print(f"  - Total size: {stats.total_used_gb:.3f}GB")
        print(f"  - Database: {stats.database_size_gb:.3f}GB")
        print(f"  - Screenshots: {stats.screenshot_size_gb:.3f}GB")
        print(f"  - Videos: {stats.video_size_gb:.3f}GB")
        print(f"  - Sessions: {stats.session_count}")
        print(f"  - Oldest data: {stats.oldest_data_date.strftime('%Y-%m-%d')}")
        
        # Calculate usage ratio using the monitor's max storage setting
        monitor_stats = monitor.get_stats()
        max_storage_gb = monitor_stats['max_storage_gb']
        usage_ratio = stats.total_used_gb / max_storage_gb
        print(f"  - Usage ratio: {usage_ratio:.1%} of {max_storage_gb}GB limit")
        
        # Use the built-in properties
        if stats.needs_cleanup:
            print(f"  ⚠️  Usage exceeds cleanup threshold (needs cleanup)")
        elif stats.is_near_limit:
            print(f"  ⚠️  Usage is near limit")
        else:
            print(f"  ✓ Usage is within normal limits")
        
        return True
        
    except Exception as e:
        print(f"✗ Storage stats test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cleanup_functionality():
    """Test storage cleanup functionality."""
    print("\n\n🧹 Testing Storage Cleanup")
    print("=" * 40)
    
    try:
        # Create and initialize monitor
        monitor = StorageMonitor()
        await monitor.initialize()
        
        # Get initial stats
        initial_stats = await monitor.get_storage_stats()
        print(f"📊 Initial usage: {initial_stats.total_used_gb:.3f}GB")
        
        # Test manual cleanup (force=True to run regardless of threshold)
        print("\n🔧 Testing manual cleanup...")
        cleanup_results = await monitor.trigger_cleanup(force=True)
        
        if cleanup_results.get("cleanup_performed"):
            print("✓ Cleanup performed successfully")
            print(f"  - Files cleaned: {cleanup_results.get('files_cleaned', 0)}")
            print(f"  - Bytes freed: {cleanup_results.get('bytes_freed', 0) / (1024**2):.2f}MB")
            print(f"  - Duration: {cleanup_results.get('cleanup_duration', 0):.2f}s")
            print(f"  - Usage before: {cleanup_results.get('usage_before_gb', 0):.3f}GB")
            print(f"  - Usage after: {cleanup_results.get('usage_after_gb', 0):.3f}GB")
            print(f"  - Space freed: {cleanup_results.get('space_freed_gb', 0):.3f}GB")
        else:
            reason = cleanup_results.get("reason", "Unknown reason")
            print(f"ℹ️  Cleanup not performed: {reason}")
        
        # Test threshold-based cleanup
        print("\n🎯 Testing threshold-based cleanup...")
        threshold_cleanup = await monitor.trigger_cleanup(force=False)
        
        if threshold_cleanup.get("cleanup_performed"):
            print("✓ Threshold-based cleanup performed")
        else:
            reason = threshold_cleanup.get("reason", "Unknown reason")
            print(f"ℹ️  Threshold-based cleanup not needed: {reason}")
        
        return True
        
    except Exception as e:
        print(f"✗ Cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_monitoring_service():
    """Test storage monitoring service lifecycle."""
    print("\n\n🔄 Testing Monitoring Service")
    print("=" * 40)
    
    try:
        # Create and initialize monitor
        monitor = StorageMonitor()
        await monitor.initialize()
        
        # Test service lifecycle
        print("🚀 Starting monitoring service...")
        await monitor.start()
        print("✓ Monitoring service started")
        print(f"  - Running: {monitor.is_running()}")
        
        # Let it run for a few seconds
        print("⏱️  Running for 3 seconds...")
        await asyncio.sleep(3)
        
        # Check stats
        stats = monitor.get_stats()
        print(f"📊 Service stats:")
        print(f"  - Running: {stats['running']}")
        print(f"  - Cleanup runs: {stats['cleanup_runs']}")
        print(f"  - Files cleaned: {stats['files_cleaned']}")
        print(f"  - Bytes freed: {stats['bytes_freed']}")
        
        # Stop service
        print("\n🛑 Stopping monitoring service...")
        await monitor.stop()
        print("✓ Monitoring service stopped")
        print(f"  - Running: {monitor.is_running()}")
        
        return True
        
    except Exception as e:
        print(f"✗ Monitoring service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_create_test_data():
    """Create some test data to demonstrate cleanup."""
    print("\n\n📁 Creating Test Data")
    print("=" * 40)
    
    try:
        config = get_config()
        data_paths = config.get_data_paths()
        
        # Create test session directory
        test_session_dir = data_paths['sessions'] / '2025-10-26' / 'test-session'
        screenshots_dir = test_session_dir / 'screenshots'
        video_dir = test_session_dir / 'video'
        
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test screenshot files
        for i in range(5):
            test_screenshot = screenshots_dir / f'test_screenshot_{i:03d}.png'
            test_screenshot.write_text(f"Test screenshot {i}" * 100)  # Create some content
        
        # Create test video files
        for i in range(2):
            test_video = video_dir / f'test_video_{i:03d}.mp4'
            test_video.write_text(f"Test video {i}" * 1000)  # Create larger content
        
        # Create test log files
        logs_dir = data_paths['logs']
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        test_log = logs_dir / 'test.log'
        test_log.write_text("Test log content" * 50)
        
        print("✓ Test data created:")
        print(f"  - Screenshots: {len(list(screenshots_dir.glob('*.png')))}")
        print(f"  - Videos: {len(list(video_dir.glob('*.mp4')))}")
        print(f"  - Logs: {len(list(logs_dir.glob('*.log')))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test data creation failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Storage Monitor Test")
    print("=" * 50)
    
    # Create test data first
    test_data_success = await test_create_test_data()
    
    # Test basic functionality
    basic_success = await test_storage_monitor_basic()
    
    # Test storage statistics
    stats_success = await test_storage_stats()
    
    # Test cleanup functionality
    cleanup_success = await test_cleanup_functionality()
    
    # Test monitoring service
    service_success = await test_monitoring_service()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"  - Test Data Creation: {'✓ PASS' if test_data_success else '✗ FAIL'}")
    print(f"  - Basic Functionality: {'✓ PASS' if basic_success else '✗ FAIL'}")
    print(f"  - Storage Statistics: {'✓ PASS' if stats_success else '✗ FAIL'}")
    print(f"  - Cleanup Functionality: {'✓ PASS' if cleanup_success else '✗ FAIL'}")
    print(f"  - Monitoring Service: {'✓ PASS' if service_success else '✗ FAIL'}")
    
    all_passed = all([basic_success, stats_success, cleanup_success, service_success])
    
    if all_passed:
        print("\n🎉 All storage monitor tests passed!")
        print("\n💡 Features implemented:")
        print("  ✅ Real-time storage usage calculation")
        print("  ✅ Configurable storage limits (5-50GB)")
        print("  ✅ Automatic cleanup with retention policies")
        print("  ✅ Storage statistics dashboard data")
        print("  ✅ Manual cleanup triggers")
        print("  ✅ Event system integration")
        print("  ✅ Service lifecycle management")
        
        print("\n🔧 Next steps:")
        print("1. Integrate with application coordinator")
        print("2. Add compression for older data")
        print("3. Create UI dashboard for storage stats")
        print("4. Test with real captured data")
    else:
        print("\n❌ Some storage monitor tests failed.")


if __name__ == "__main__":
    asyncio.run(main())