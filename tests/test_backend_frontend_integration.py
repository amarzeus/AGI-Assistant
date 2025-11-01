"""Integration tests for backend-frontend communication."""

import asyncio
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.services.backend_event_bridge import BackendEventBridge
from src.services.command_dispatcher import CommandDispatcher
from src.services.event_system import Event, EventType, get_event_bus
from src.wxui.gui_event_bridge import GuiEventBridge


class MockMainFrame:
    """Mock MainFrame for testing."""
    
    def __init__(self):
        self.actions = []
        self.patterns = []
        self.errors = []
        self.warnings = []
        self.service_health = {}
        self.performance_metrics = {}
        self.connected = False
        self.disconnected = False
        
    def add_action_to_feed(self, action):
        self.actions.append(action)
    
    def add_pattern_to_dashboard(self, pattern):
        self.patterns.append(pattern)
    
    def show_error(self, title, message, details=None):
        self.errors.append((title, message, details))
    
    def show_warning(self, title, message):
        self.warnings.append((title, message))
    
    def update_service_health(self, service_name, status, details):
        self.service_health[service_name] = (status, details)
    
    def update_performance_metrics(self, metrics):
        self.performance_metrics = metrics
    
    def on_backend_connected(self):
        self.connected = True
    
    def on_backend_disconnected(self, reason):
        self.disconnected = True


class MockCoordinator:
    """Mock ApplicationCoordinator for testing."""
    
    def __init__(self):
        self.storage_manager = Mock()
        self.automation_executor = Mock()
        self.screen_capture = Mock()
        self.hotkey_manager = Mock()
        self._running = False
        self._current_session = None
        self._service_health = {
            'screen_capture': True,
            'audio_transcription': True,
            'workflow_analyzer': True
        }
    
    async def start(self):
        self._running = True
        from src.models.session import Session, SessionStatus
        self._current_session = Session(
            id='test-session-123',
            start_time=datetime.now(),
            status=SessionStatus.ACTIVE
        )
    
    async def stop(self):
        self._running = False
    
    async def pause_capture(self):
        pass
    
    async def resume_capture(self):
        pass
    
    def is_running(self):
        return self._running
    
    def get_current_session(self):
        return self._current_session
    
    def get_service_health(self):
        return self._service_health


class TestBackendFrontendIntegration(unittest.TestCase):
    """Test backend-frontend integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.coordinator = MockCoordinator()
        self.main_frame = MockMainFrame()
        self.event_bus = get_event_bus()
        
    def test_command_dispatcher_start_recording(self):
        """Test start recording command."""
        dispatcher = CommandDispatcher(self.coordinator)
        
        async def run_test():
            result = await dispatcher.dispatch('start_recording', {})
            self.assertTrue(result['success'])
            self.assertIn('session_id', result['result'])
            self.assertTrue(self.coordinator.is_running())
        
        asyncio.run(run_test())
    
    def test_command_dispatcher_validation(self):
        """Test command validation."""
        dispatcher = CommandDispatcher(self.coordinator)
        
        async def run_test():
            # Test invalid command
            result = await dispatcher.dispatch('invalid_command', {})
            self.assertFalse(result['success'])
            self.assertIn('Unknown command', result['error'])
            
            # Test missing required parameter
            result = await dispatcher.dispatch('execute_workflow', {})
            self.assertFalse(result['success'])
            self.assertIn('workflow_id is required', result['error'])
        
        asyncio.run(run_test())
    
    def test_command_dispatcher_settings_validation(self):
        """Test settings validation."""
        dispatcher = CommandDispatcher(self.coordinator)
        
        async def run_test():
            # Test invalid screenshot interval
            result = await dispatcher.dispatch('update_settings', {
                'settings': {'screenshot_interval': 100}  # Out of range
            })
            self.assertFalse(result['success'])
            self.assertIn('screenshot_interval', result['error'])
            
            # Test valid settings
            result = await dispatcher.dispatch('update_settings', {
                'settings': {'screenshot_interval': 5}
            })
            self.assertTrue(result['success'])
        
        asyncio.run(run_test())
    
    def test_backend_event_bridge_initialization(self):
        """Test backend event bridge initialization."""
        bridge = BackendEventBridge(self.coordinator)
        
        self.assertIsNotNone(bridge)
        self.assertEqual(len(bridge._gui_clients), 0)
        
        # Register GUI client
        bridge.register_gui_client(self.main_frame)
        self.assertEqual(len(bridge._gui_clients), 1)
        
        # Unregister GUI client
        bridge.unregister_gui_client(self.main_frame)
        self.assertEqual(len(bridge._gui_clients), 0)
    
    def test_event_flow(self):
        """Test event flow from backend to GUI."""
        async def run_test():
            # Create backend event bridge
            backend_bridge = BackendEventBridge(self.coordinator)
            backend_bridge.register_gui_client(self.main_frame)
            await backend_bridge.start()
            
            # Create and publish event
            event = Event(
                type=EventType.ACTION_DETECTED,
                timestamp=datetime.now(),
                source='test',
                data={
                    'action_id': 'test-123',
                    'timestamp': datetime.now().isoformat(),
                    'action_type': 'click',
                    'application': 'TestApp',
                    'description': 'Test action',
                    'confidence': 0.95
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            # Wait for event processing
            await asyncio.sleep(0.5)
            
            # Stop bridge
            await backend_bridge.stop()
        
        asyncio.run(run_test())
    
    def test_service_health_monitoring(self):
        """Test service health monitoring."""
        async def run_test():
            backend_bridge = BackendEventBridge(self.coordinator)
            backend_bridge.register_gui_client(self.main_frame)
            await backend_bridge.start()
            
            # Wait for health check
            await asyncio.sleep(6)  # Health check runs every 5 seconds
            
            # Verify health was reported
            self.assertGreater(len(self.main_frame.service_health), 0)
            
            await backend_bridge.stop()
        
        asyncio.run(run_test())
    
    def test_performance_metrics_collection(self):
        """Test performance metrics collection."""
        async def run_test():
            backend_bridge = BackendEventBridge(self.coordinator)
            backend_bridge.register_gui_client(self.main_frame)
            await backend_bridge.start()
            
            # Wait for metrics collection
            await asyncio.sleep(6)  # Metrics collected every 5 seconds
            
            # Verify metrics were collected
            self.assertIsNotNone(self.main_frame.performance_metrics)
            
            await backend_bridge.stop()
        
        asyncio.run(run_test())
    
    def test_error_handling(self):
        """Test error handling in command dispatcher."""
        dispatcher = CommandDispatcher(self.coordinator)
        
        async def run_test():
            # Test with coordinator that raises exception
            self.coordinator.storage_manager = None
            
            result = await dispatcher.dispatch('get_storage_stats', {})
            self.assertFalse(result['success'])
            self.assertIn('Storage manager not available', result['error'])
        
        asyncio.run(run_test())


class TestGuiEventBridge(unittest.TestCase):
    """Test GUI event bridge."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.main_frame = MockMainFrame()
    
    def test_gui_event_bridge_initialization(self):
        """Test GUI event bridge initialization."""
        # Note: Can't fully test without wx.App running
        # This is a basic structure test
        bridge = GuiEventBridge(self.main_frame)
        
        self.assertIsNotNone(bridge)
        self.assertEqual(bridge._connected, False)
        self.assertEqual(len(bridge._state_cache), 0)
    
    def test_state_caching(self):
        """Test state caching."""
        bridge = GuiEventBridge(self.main_frame)
        
        # Test cache operations
        bridge.update_cached_state('test_key', 'test_value')
        value = bridge.get_cached_state('test_key')
        self.assertEqual(value, 'test_value')
        
        # Test default value
        value = bridge.get_cached_state('nonexistent', 'default')
        self.assertEqual(value, 'default')
    
    def test_event_throttling(self):
        """Test event throttling."""
        bridge = GuiEventBridge(self.main_frame)
        
        # Create test event
        event = Event(
            type=EventType.SCREENSHOT_CAPTURED,
            timestamp=datetime.now(),
            source='test',
            data={}
        )
        
        # First event should not be throttled
        should_throttle = bridge._should_throttle(event)
        self.assertFalse(should_throttle)
        
        # Update last event time
        bridge._last_event_time[event.type.value] = datetime.now()
        
        # Immediate second event should be throttled
        should_throttle = bridge._should_throttle(event)
        self.assertTrue(should_throttle)


if __name__ == '__main__':
    unittest.main()
