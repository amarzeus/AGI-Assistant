"""Backend Event Bridge for publishing events to GUI clients.

This module manages event publishing and command handling for GUI clients,
acting as the backend side of the backend-frontend communication bridge.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from datetime import datetime

from src.logger import get_app_logger
from src.services.event_system import get_event_bus, Event, EventType

if TYPE_CHECKING:
    from src.interfaces.gui import GuiPort
    from src.services.application_coordinator import ApplicationCoordinator


class BackendEventBridge:
    """
    Manages event publishing and command handling for GUI clients.
    
    Responsibilities:
    - Subscribe to EventBus events relevant to GUI
    - Transform backend events to GUI-friendly format
    - Forward events to connected GUI clients
    - Handle GUI commands and route to appropriate services
    - Monitor service health and notify GUI
    """
    
    def __init__(self, coordinator: 'ApplicationCoordinator'):
        """
        Initialize Backend Event Bridge.
        
        Args:
            coordinator: Reference to ApplicationCoordinator
        """
        self._coordinator = coordinator
        self._event_bus = get_event_bus()
        self._gui_clients: List['GuiPort'] = []
        self._running = False
        
        # Performance metrics
        self._metrics = {
            'cpu_percent': 0.0,
            'memory_mb': 0.0,
            'event_rate': 0.0,
            'queue_sizes': {}
        }
        
        # Service health tracking
        self._service_health: Dict[str, Dict[str, Any]] = {}
        
        self.logger = get_app_logger()
        self.logger.info("Backend Event Bridge initialized")
    
    async def start(self) -> None:
        """Start bridge and subscribe to events."""
        if self._running:
            self.logger.warning("Backend Event Bridge already running")
            return
        
        self._running = True
        
        # Subscribe to relevant event queues
        self._subscribe_to_events()
        
        # Start background tasks
        asyncio.create_task(self._monitor_service_health())
        asyncio.create_task(self._collect_performance_metrics())
        
        self.logger.info("Backend Event Bridge started")
    
    async def stop(self) -> None:
        """Stop bridge and cleanup."""
        self._running = False
        self._gui_clients.clear()
        self.logger.info("Backend Event Bridge stopped")
    
    def register_gui_client(self, gui_port: 'GuiPort') -> None:
        """
        Register GUI client for event notifications.
        
        Args:
            gui_port: GUI client implementing GuiPort interface
        """
        if gui_port not in self._gui_clients:
            self._gui_clients.append(gui_port)
            self.logger.info(f"GUI client registered. Total clients: {len(self._gui_clients)}")
    
    def unregister_gui_client(self, gui_port: 'GuiPort') -> None:
        """
        Unregister GUI client.
        
        Args:
            gui_port: GUI client to unregister
        """
        if gui_port in self._gui_clients:
            self._gui_clients.remove(gui_port)
            self.logger.info(f"GUI client unregistered. Total clients: {len(self._gui_clients)}")
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to EventBus events relevant to GUI."""
        # Subscribe to all event queues
        queues = [
            'capture_events',
            'audio_events',
            'analysis_events',
            'storage_events',
            'system_events'
        ]
        
        for queue_name in queues:
            queue = self._event_bus.get_queue(queue_name)
            if queue:
                queue.subscribe(self._on_event)
                self.logger.debug(f"Subscribed to queue: {queue_name}")
    
    async def _on_event(self, event: Event) -> None:
        """
        Handle event from EventBus.
        
        Args:
            event: Event from EventBus
        """
        try:
            # Transform event if needed
            transformed_event = self._transform_event(event)
            
            # Notify all GUI clients
            self._notify_gui_clients(transformed_event)
        except Exception as e:
            self.logger.error(f"Error handling event {event.type.value}: {e}", exc_info=True)
    
    def _transform_event(self, event: Event) -> Event:
        """
        Transform backend event to GUI-friendly format.
        
        Args:
            event: Original event
            
        Returns:
            Transformed event
        """
        # For now, pass through events as-is
        # Can add transformation logic here if needed
        return event
    
    def _notify_gui_clients(self, event: Event) -> None:
        """
        Notify all registered GUI clients of event.
        
        Args:
            event: Event to send to clients
        """
        for client in self._gui_clients:
            try:
                # GUI clients should have an event bridge that handles events
                if hasattr(client, '_event_bridge'):
                    client._event_bridge.on_backend_event(event)
            except Exception as e:
                self.logger.error(f"Error notifying GUI client: {e}", exc_info=True)
    
    async def _monitor_service_health(self) -> None:
        """Monitor service health and publish updates."""
        while self._running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Get service health from coordinator
                if hasattr(self._coordinator, 'get_service_health'):
                    health = self._coordinator.get_service_health()
                    
                    # Check for changes and notify GUI
                    for service_name, is_healthy in health.items():
                        status = 'healthy' if is_healthy else 'failed'
                        details = 'Service running normally' if is_healthy else 'Service not responding'
                        
                        # Update internal tracking
                        if service_name not in self._service_health or \
                           self._service_health[service_name].get('status') != status:
                            self._service_health[service_name] = {
                                'status': status,
                                'details': details,
                                'last_update': datetime.now()
                            }
                            
                            # Notify GUI clients
                            for client in self._gui_clients:
                                try:
                                    client.update_service_health(service_name, status, details)
                                except Exception as e:
                                    self.logger.error(f"Error updating service health in GUI: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring service health: {e}", exc_info=True)
    
    async def _collect_performance_metrics(self) -> None:
        """Collect and publish performance metrics."""
        while self._running:
            try:
                await asyncio.sleep(5)  # Collect every 5 seconds
                
                # Collect metrics
                try:
                    import psutil
                    process = psutil.Process()
                    
                    self._metrics['cpu_percent'] = process.cpu_percent(interval=0.1)
                    self._metrics['memory_mb'] = process.memory_info().rss / 1024 / 1024
                except ImportError:
                    # psutil not available, use basic metrics
                    pass
                
                # Get event bus stats
                stats = self._event_bus.get_all_stats()
                self._metrics['queue_sizes'] = {
                    name: stat.get('queue_size', 0)
                    for name, stat in stats.items()
                }
                
                # Calculate event rate
                total_events = sum(
                    stat.get('events_published', 0)
                    for stat in stats.values()
                )
                self._metrics['event_rate'] = total_events / 5.0  # Events per second
                
                # Notify GUI clients
                for client in self._gui_clients:
                    try:
                        client.update_performance_metrics(self._metrics.copy())
                    except Exception as e:
                        self.logger.error(f"Error updating performance metrics in GUI: {e}")
                
                # Check for performance warnings
                if self._metrics['cpu_percent'] > 80:
                    self.logger.warning(f"High CPU usage: {self._metrics['cpu_percent']:.1f}%")
                    for client in self._gui_clients:
                        try:
                            client.show_warning(
                                "High CPU Usage",
                                f"CPU usage is at {self._metrics['cpu_percent']:.1f}%. Consider reducing capture frequency."
                            )
                        except Exception as e:
                            self.logger.error(f"Error showing warning in GUI: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting performance metrics: {e}", exc_info=True)
    
    def get_service_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current service health status.
        
        Returns:
            Dictionary of service health information
        """
        return self._service_health.copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        return self._metrics.copy()
