"""Event system for inter-service communication."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from src.logger import get_app_logger


class EventType(Enum):
    """Types of events in the system."""
    
    # Screen capture events
    SCREENSHOT_CAPTURED = "screenshot_captured"
    VIDEO_SEGMENT_COMPLETE = "video_segment_complete"
    CAPTURE_PAUSED = "capture_paused"
    CAPTURE_RESUMED = "capture_resumed"
    
    # Audio events (for future implementation)
    AUDIO_TRANSCRIBED = "audio_transcribed"
    AUDIO_CAPTURE_STARTED = "audio_capture_started"
    AUDIO_CAPTURE_STOPPED = "audio_capture_stopped"
    
    # Analysis events (for future implementation)
    ACTION_DETECTED = "action_detected"
    PATTERN_DETECTED = "pattern_detected"
    WORKFLOW_SUGGESTION_GENERATED = "workflow_suggestion_generated"
    
    # Storage events
    SESSION_CREATED = "session_created"
    SESSION_COMPLETED = "session_completed"
    STORAGE_CLEANUP_TRIGGERED = "storage_cleanup_triggered"
    STORAGE_CLEANUP_COMPLETED = "storage_cleanup_completed"
    
    # System events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    SERVICE_ERROR = "service_error"
    APPLICATION_SHUTDOWN = "application_shutdown"


@dataclass
class Event:
    """Base event class."""
    
    type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    event_id: Optional[str] = None
    
    def __post_init__(self):
        if self.event_id is None:
            import uuid
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'data': self.data,
            'event_id': self.event_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(
            type=EventType(data['type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            source=data['source'],
            data=data['data'],
            event_id=data.get('event_id')
        )
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Create event from JSON string."""
        return cls.from_dict(json.loads(json_str))


class EventQueue:
    """Async event queue with filtering and backpressure handling."""
    
    def __init__(self, name: str, maxsize: int = 1000):
        self.name = name
        self.maxsize = maxsize
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers: List[Callable] = []
        self._filters: List[Callable] = []
        self._stats = {
            'events_published': 0,
            'events_consumed': 0,
            'events_dropped': 0,
            'queue_full_count': 0
        }
        self.logger = get_app_logger()
    
    async def publish(self, event: Event) -> bool:
        """
        Publish event to queue.
        
        Returns:
            bool: True if event was queued, False if dropped due to full queue
        """
        try:
            # Apply filters
            for filter_func in self._filters:
                if not filter_func(event):
                    return False
            
            # Try to put event in queue (non-blocking)
            self._queue.put_nowait(event)
            self._stats['events_published'] += 1
            
            # Notify subscribers immediately
            for subscriber in self._subscribers:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        asyncio.create_task(subscriber(event))
                    else:
                        subscriber(event)
                except Exception as e:
                    self.logger.error(f"Error in event subscriber: {e}")
            
            return True
            
        except asyncio.QueueFull:
            self._stats['events_dropped'] += 1
            self._stats['queue_full_count'] += 1
            self.logger.warning(f"Event queue '{self.name}' is full, dropping event: {event.type.value}")
            return False
        
        except Exception as e:
            self.logger.error(f"Error publishing event to queue '{self.name}': {e}")
            return False
    
    async def consume(self, timeout: Optional[float] = None) -> Optional[Event]:
        """
        Consume event from queue.
        
        Args:
            timeout: Maximum time to wait for event (None = wait forever)
            
        Returns:
            Event or None if timeout occurred
        """
        try:
            if timeout is None:
                event = await self._queue.get()
            else:
                event = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            
            self._stats['events_consumed'] += 1
            self._queue.task_done()
            return event
            
        except asyncio.TimeoutError:
            return None
        
        except Exception as e:
            self.logger.error(f"Error consuming event from queue '{self.name}': {e}")
            return None
    
    def subscribe(self, callback: Callable[[Event], Any]) -> None:
        """Subscribe to events (immediate notification)."""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Event], Any]) -> None:
        """Unsubscribe from events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def add_filter(self, filter_func: Callable[[Event], bool]) -> None:
        """Add event filter (return True to allow event)."""
        self._filters.append(filter_func)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self._stats,
            'queue_size': self._queue.qsize(),
            'queue_maxsize': self.maxsize,
            'subscriber_count': len(self._subscribers),
            'filter_count': len(self._filters)
        }
    
    def clear(self) -> None:
        """Clear all events from queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break


class EventBus:
    """Central event bus for managing multiple queues and routing."""
    
    def __init__(self):
        self.logger = get_app_logger()
        self._queues: Dict[str, EventQueue] = {}
        self._global_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        # Create default queues
        self._create_default_queues()
    
    def _create_default_queues(self) -> None:
        """Create default event queues."""
        default_queues = [
            'capture_events',      # Screenshot and video events
            'audio_events',        # Audio transcription events
            'analysis_events',     # Workflow analysis events
            'storage_events',      # Database and file operations
            'system_events',       # Application lifecycle events
        ]
        
        for queue_name in default_queues:
            self._queues[queue_name] = EventQueue(queue_name)
    
    def get_queue(self, name: str) -> Optional[EventQueue]:
        """Get event queue by name."""
        return self._queues.get(name)
    
    def create_queue(self, name: str, maxsize: int = 1000) -> EventQueue:
        """Create new event queue."""
        if name in self._queues:
            self.logger.warning(f"Queue '{name}' already exists")
            return self._queues[name]
        
        queue = EventQueue(name, maxsize)
        self._queues[name] = queue
        self.logger.info(f"Created event queue: {name}")
        return queue
    
    async def publish(self, event: Event, queue_name: Optional[str] = None) -> bool:
        """
        Publish event to specific queue or route automatically.
        
        Args:
            event: Event to publish
            queue_name: Specific queue name, or None for auto-routing
            
        Returns:
            bool: True if event was published successfully
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify global subscribers
        for subscriber in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    asyncio.create_task(subscriber(event))
                else:
                    subscriber(event)
            except Exception as e:
                self.logger.error(f"Error in global event subscriber: {e}")
        
        # Route to specific queue or auto-route
        if queue_name:
            queue = self._queues.get(queue_name)
            if queue:
                return await queue.publish(event)
            else:
                self.logger.error(f"Queue '{queue_name}' not found")
                return False
        else:
            # Auto-route based on event type
            target_queue = self._route_event(event)
            if target_queue:
                return await target_queue.publish(event)
            else:
                self.logger.warning(f"No queue found for event type: {event.type.value}")
                return False
    
    def _route_event(self, event: Event) -> Optional[EventQueue]:
        """Auto-route event to appropriate queue based on type."""
        routing_map = {
            EventType.SCREENSHOT_CAPTURED: 'capture_events',
            EventType.VIDEO_SEGMENT_COMPLETE: 'capture_events',
            EventType.CAPTURE_PAUSED: 'capture_events',
            EventType.CAPTURE_RESUMED: 'capture_events',
            
            EventType.AUDIO_TRANSCRIBED: 'audio_events',
            EventType.AUDIO_CAPTURE_STARTED: 'audio_events',
            EventType.AUDIO_CAPTURE_STOPPED: 'audio_events',
            
            EventType.ACTION_DETECTED: 'analysis_events',
            EventType.PATTERN_DETECTED: 'analysis_events',
            EventType.WORKFLOW_SUGGESTION_GENERATED: 'analysis_events',
            
            EventType.SESSION_CREATED: 'storage_events',
            EventType.SESSION_COMPLETED: 'storage_events',
            EventType.STORAGE_CLEANUP_TRIGGERED: 'storage_events',
            EventType.STORAGE_CLEANUP_COMPLETED: 'storage_events',
            
            EventType.SERVICE_STARTED: 'system_events',
            EventType.SERVICE_STOPPED: 'system_events',
            EventType.SERVICE_ERROR: 'system_events',
            EventType.APPLICATION_SHUTDOWN: 'system_events',
        }
        
        queue_name = routing_map.get(event.type)
        return self._queues.get(queue_name) if queue_name else None
    
    def subscribe_global(self, callback: Callable[[Event], Any]) -> None:
        """Subscribe to all events globally."""
        self._global_subscribers.append(callback)
    
    def unsubscribe_global(self, callback: Callable[[Event], Any]) -> None:
        """Unsubscribe from global events."""
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
    
    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return events[-limit:] if limit > 0 else events
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues."""
        return {
            queue_name: queue.get_stats()
            for queue_name, queue in self._queues.items()
        }
    
    def clear_all_queues(self) -> None:
        """Clear all events from all queues."""
        for queue in self._queues.values():
            queue.clear()
        
        self._event_history.clear()
        self.logger.info("All event queues cleared")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Convenience functions for creating common events

def create_screenshot_event(source: str, filepath: Path, timestamp: datetime, **kwargs) -> Event:
    """Create screenshot captured event."""
    return Event(
        type=EventType.SCREENSHOT_CAPTURED,
        timestamp=timestamp,
        source=source,
        data={
            'filepath': str(filepath),
            'filename': filepath.name,
            'size_bytes': filepath.stat().st_size if filepath.exists() else 0,
            **kwargs
        }
    )


def create_video_segment_event(source: str, segment_path: Path, start_time: datetime, duration: float, **kwargs) -> Event:
    """Create video segment complete event."""
    return Event(
        type=EventType.VIDEO_SEGMENT_COMPLETE,
        timestamp=datetime.now(),
        source=source,
        data={
            'segment_path': str(segment_path),
            'segment_name': segment_path.name,
            'start_time': start_time.isoformat(),
            'duration_seconds': duration,
            **kwargs
        }
    )


def create_service_event(event_type: EventType, source: str, service_name: str, **kwargs) -> Event:
    """Create service lifecycle event."""
    return Event(
        type=event_type,
        timestamp=datetime.now(),
        source=source,
        data={
            'service_name': service_name,
            **kwargs
        }
    )


def create_session_event(event_type: EventType, source: str, session_id: str, **kwargs) -> Event:
    """Create session lifecycle event."""
    return Event(
        type=event_type,
        timestamp=datetime.now(),
        source=source,
        data={
            'session_id': session_id,
            **kwargs
        }
    )