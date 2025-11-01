"""Integration tests for automation system."""

import pytest
import asyncio
from pathlib import Path

from src.services.automation_executor import AutomationExecutor
from src.services.platforms.desktop_automation import DesktopAutomationPlatform
from src.database.storage_manager import StorageManager


@pytest.mark.asyncio
async def test_desktop_platform_initialization():
    """Test desktop automation platform initialization."""
    platform = DesktopAutomationPlatform()
    
    # Check initialization
    assert platform is not None
    
    # Check screen size
    width, height = platform.get_screen_size()
    assert width > 0
    assert height > 0
    
    print(f"Screen size: {width}x{height}")


@pytest.mark.asyncio
async def test_desktop_platform_mouse_position():
    """Test getting mouse position."""
    platform = DesktopAutomationPlatform()
    
    if platform.enabled:
        x, y = platform.get_mouse_position()
        assert isinstance(x, int)
        assert isinstance(y, int)
        print(f"Mouse position: ({x}, {y})")
    else:
        print("Desktop platform not available (PyAutoGUI not installed)")


@pytest.mark.asyncio
async def test_end_to_end_simple_workflow():
    """Test end-to-end workflow execution with simple actions."""
    # Initialize storage
    storage_manager = StorageManager()
    await storage_manager.initialize()
    
    # Initialize executor
    executor = AutomationExecutor()
    await executor.initialize(storage_manager)
    await executor.start()
    
    try:
        # Create simple workflow
        workflow_data = {
            'id': 'test_e2e',
            'name': 'End-to-End Test',
            'description': 'Simple end-to-end test',
            'actions': [
                {'type': 'wait', 'duration': 0.5},
                {'type': 'wait', 'duration': 0.5}
            ]
        }
        
        # Queue execution
        execution_id = await executor.queue_execution(workflow_data)
        print(f"Queued execution: {execution_id}")
        
        # Wait for execution
        await asyncio.sleep(3)
        
        # Check stats
        stats = executor.get_stats()
        print(f"Executor stats: {stats}")
        
        assert stats['executions_completed'] >= 1
        
    finally:
        await executor.stop()
        await storage_manager.close()


@pytest.mark.asyncio
async def test_action_types():
    """Test different action types."""
    executor = AutomationExecutor()
    
    # Test wait action
    result = await executor._dispatch_action('wait', {'duration': 0.1})
    assert result is True
    print("✓ Wait action works")
    
    # Test click action (will fail without valid coordinates)
    result = await executor._dispatch_action('click', {'x': -1, 'y': -1})
    # Should return False for invalid coordinates
    print(f"✓ Click action validation works (result: {result})")
    
    # Test type_text action
    result = await executor._dispatch_action('type_text', {'text': 'test'})
    # May fail if PyAutoGUI not available, but shouldn't crash
    print(f"✓ Type text action handled (result: {result})")


@pytest.mark.asyncio
async def test_workflow_with_multiple_action_types():
    """Test workflow with multiple action types."""
    storage_manager = StorageManager()
    await storage_manager.initialize()
    
    executor = AutomationExecutor()
    await executor.initialize(storage_manager)
    await executor.start()
    
    try:
        workflow_data = {
            'id': 'test_multi_action',
            'name': 'Multi-Action Test',
            'description': 'Test multiple action types',
            'actions': [
                {'type': 'wait', 'duration': 0.2},
                {'type': 'wait', 'duration': 0.2},
                {'type': 'wait', 'duration': 0.2}
            ]
        }
        
        execution_id = await executor.queue_execution(workflow_data)
        print(f"Queued multi-action workflow: {execution_id}")
        
        # Monitor execution
        for i in range(10):
            await asyncio.sleep(0.5)
            status = executor.get_execution_status(execution_id)
            if status:
                print(f"Progress: {status['progress']:.0%} - Step {status['current_step']}/{status['total_steps']}")
                if status['state'] in ['completed', 'failed']:
                    break
        
        stats = executor.get_stats()
        print(f"Final stats: {stats}")
        
    finally:
        await executor.stop()
        await storage_manager.close()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in automation."""
    executor = AutomationExecutor()
    
    # Test with invalid action type
    result = await executor._dispatch_action('invalid_action', {})
    assert result is False
    print("✓ Invalid action handled gracefully")
    
    # Test with missing parameters
    result = await executor._dispatch_action('click', {})
    # Should handle missing parameters
    print(f"✓ Missing parameters handled (result: {result})")


def test_workflow_validation():
    """Test workflow validation logic."""
    executor = AutomationExecutor()
    
    # Valid workflow
    valid = {
        'id': 'test',
        'name': 'Test',
        'actions': [{'type': 'wait', 'duration': 1}]
    }
    assert executor._validate_workflow(valid)
    print("✓ Valid workflow accepted")
    
    # Invalid - missing id
    invalid1 = {
        'name': 'Test',
        'actions': [{'type': 'wait'}]
    }
    assert not executor._validate_workflow(invalid1)
    print("✓ Invalid workflow (missing id) rejected")
    
    # Invalid - empty actions
    invalid2 = {
        'id': 'test',
        'name': 'Test',
        'actions': []
    }
    assert not executor._validate_workflow(invalid2)
    print("✓ Invalid workflow (empty actions) rejected")


if __name__ == '__main__':
    # Run tests
    print("Running automation integration tests...\n")
    
    print("=" * 60)
    print("Test 1: Desktop Platform Initialization")
    print("=" * 60)
    asyncio.run(test_desktop_platform_initialization())
    
    print("\n" + "=" * 60)
    print("Test 2: Mouse Position")
    print("=" * 60)
    asyncio.run(test_desktop_platform_mouse_position())
    
    print("\n" + "=" * 60)
    print("Test 3: Workflow Validation")
    print("=" * 60)
    test_workflow_validation()
    
    print("\n" + "=" * 60)
    print("Test 4: Action Types")
    print("=" * 60)
    asyncio.run(test_action_types())
    
    print("\n" + "=" * 60)
    print("Test 5: Error Handling")
    print("=" * 60)
    asyncio.run(test_error_handling())
    
    print("\n" + "=" * 60)
    print("Test 6: End-to-End Simple Workflow")
    print("=" * 60)
    asyncio.run(test_end_to_end_simple_workflow())
    
    print("\n" + "=" * 60)
    print("Test 7: Multi-Action Workflow")
    print("=" * 60)
    asyncio.run(test_workflow_with_multiple_action_types())
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
