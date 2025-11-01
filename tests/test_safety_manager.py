"""Tests for SafetyManager service."""

import pytest
import asyncio
from datetime import datetime, timedelta

from src.services.safety_manager import SafetyManager


@pytest.fixture
def safety_manager():
    """Create safety manager for testing."""
    return SafetyManager()


@pytest.mark.asyncio
async def test_emergency_stop_trigger_and_reset(safety_manager):
    """Test emergency stop trigger and reset."""
    # Initially not triggered
    assert not await safety_manager.check_emergency_stop()
    
    # Trigger emergency stop
    await safety_manager.trigger_emergency_stop()
    assert await safety_manager.check_emergency_stop()
    
    # Reset emergency stop
    await safety_manager.reset_emergency_stop()
    assert not await safety_manager.check_emergency_stop()


@pytest.mark.asyncio
async def test_timeout_detection_click(safety_manager):
    """Test timeout detection for click action."""
    action_type = 'click'
    timeout = safety_manager.get_timeout(action_type)
    
    # Action within timeout
    start_time = datetime.now()
    assert not await safety_manager.check_timeout(action_type, start_time)
    
    # Action exceeding timeout
    old_start_time = datetime.now() - timedelta(seconds=timeout + 1)
    assert await safety_manager.check_timeout(action_type, old_start_time)


@pytest.mark.asyncio
async def test_timeout_detection_browser_navigate(safety_manager):
    """Test timeout detection for browser navigation."""
    action_type = 'browser_navigate'
    timeout = safety_manager.get_timeout(action_type)
    
    # Action within timeout
    start_time = datetime.now()
    assert not await safety_manager.check_timeout(action_type, start_time)
    
    # Action exceeding timeout
    old_start_time = datetime.now() - timedelta(seconds=timeout + 1)
    assert await safety_manager.check_timeout(action_type, old_start_time)


@pytest.mark.asyncio
async def test_rate_limiting(safety_manager):
    """Test rate limiting with multiple actions."""
    # First action should not trigger rate limit
    assert not await safety_manager.check_rate_limit()
    
    # Add actions up to the limit
    for _ in range(safety_manager.max_actions_per_minute - 1):
        assert not await safety_manager.check_rate_limit()
    
    # Next action should trigger rate limit
    assert await safety_manager.check_rate_limit()


@pytest.mark.asyncio
async def test_validate_click_action_valid(safety_manager):
    """Test validation of valid click action."""
    action = {
        'type': 'click',
        'x': 100,
        'y': 100,
        'button': 'left'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_click_action_missing_coordinates(safety_manager):
    """Test validation of click action with missing coordinates."""
    action = {
        'type': 'click',
        'button': 'left'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_click_action_out_of_bounds(safety_manager):
    """Test validation of click action with out of bounds coordinates."""
    action = {
        'type': 'click',
        'x': 999999,
        'y': 999999,
        'button': 'left'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_type_action_valid(safety_manager):
    """Test validation of valid type action."""
    action = {
        'type': 'type_text',
        'text': 'Hello World'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_type_action_missing_text(safety_manager):
    """Test validation of type action with missing text."""
    action = {
        'type': 'type_text'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_hotkey_action_valid(safety_manager):
    """Test validation of valid hotkey action."""
    action = {
        'type': 'hotkey',
        'keys': ['ctrl', 'c']
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_hotkey_action_missing_keys(safety_manager):
    """Test validation of hotkey action with missing keys."""
    action = {
        'type': 'hotkey'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_browser_action_valid(safety_manager):
    """Test validation of valid browser action."""
    action = {
        'type': 'browser_click',
        'selector': '#submit-button'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_browser_action_missing_selector(safety_manager):
    """Test validation of browser action with missing selector."""
    action = {
        'type': 'browser_click'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_browser_navigate_valid(safety_manager):
    """Test validation of valid browser navigate action."""
    action = {
        'type': 'browser_navigate',
        'url': 'https://example.com'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_browser_navigate_missing_url(safety_manager):
    """Test validation of browser navigate with missing URL."""
    action = {
        'type': 'browser_navigate'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_excel_action_valid(safety_manager):
    """Test validation of valid Excel action."""
    action = {
        'type': 'excel_write_cell',
        'sheet': 1,
        'cell': 'A1',
        'value': 'Test'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_excel_action_missing_cell(safety_manager):
    """Test validation of Excel action with missing cell."""
    action = {
        'type': 'excel_write_cell',
        'sheet': 1,
        'value': 'Test'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_file_operation_valid(safety_manager):
    """Test validation of valid file operation."""
    action = {
        'type': 'file_copy',
        'source': 'C:\\source.txt',
        'destination': 'C:\\dest.txt'
    }
    
    assert await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_validate_file_operation_missing_paths(safety_manager):
    """Test validation of file operation with missing paths."""
    action = {
        'type': 'file_copy',
        'source': 'C:\\source.txt'
    }
    
    assert not await safety_manager.validate_action(action)


@pytest.mark.asyncio
async def test_custom_timeout(safety_manager):
    """Test setting custom timeout for action type."""
    action_type = 'custom_action'
    custom_timeout = 60.0
    
    # Set custom timeout
    safety_manager.set_timeout(action_type, custom_timeout)
    
    # Verify timeout was set
    assert safety_manager.get_timeout(action_type) == custom_timeout


@pytest.mark.asyncio
async def test_get_stats(safety_manager):
    """Test getting safety manager statistics."""
    stats = safety_manager.get_stats()
    
    assert 'emergency_stop_active' in stats
    assert 'max_actions_per_minute' in stats
    assert 'actions_in_last_minute' in stats
    assert 'screen_dimensions' in stats
    assert 'configured_timeouts' in stats
    
    assert stats['emergency_stop_active'] == False
    assert stats['max_actions_per_minute'] == 60
    assert stats['actions_in_last_minute'] == 0
