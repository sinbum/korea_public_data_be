"""
Domain events implementation for event-driven architecture.

Provides base classes and infrastructure for domain events.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Callable, Set
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)


class DomainEvent(BaseModel, ABC):
    """
    Base class for all domain events.
    
    Events represent something that happened in the domain.
    They are immutable and contain all relevant data.
    """
    
    # Event metadata
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
    
    # Event context
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    class Config:
        # Events should be immutable
        frozen = True
        # Allow arbitrary types for flexibility
        arbitrary_types_allowed = True


class EventHandler(ABC):
    """
    Abstract base class for event handlers.
    
    Handlers process domain events and perform side effects.
    """
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a domain event.
        
        Args:
            event: The domain event to handle
        """
        pass
    
    def can_handle(self, event: DomainEvent) -> bool:
        """
        Check if this handler can process the given event.
        
        Default implementation checks event type.
        Can be overridden for more complex logic.
        """
        return isinstance(event, self._get_event_type())
    
    def _get_event_type(self) -> Type[DomainEvent]:
        """Get the event type this handler processes."""
        # This should be overridden in concrete handlers
        return DomainEvent


class EventBus:
    """
    Event bus for publishing and subscribing to domain events.
    
    Supports both synchronous and asynchronous event handling.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._middleware: List[Callable] = []
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._failed_events: List[tuple] = []
    
    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler to register
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__class__.__name__} to event {event_type.__name__}")
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Unsubscribed handler {handler.__class__.__name__} from event {event_type.__name__}")
            except ValueError:
                logger.warning(f"Handler {handler.__class__.__name__} was not subscribed to {event_type.__name__}")
    
    async def publish(self, event: DomainEvent, wait_for_completion: bool = False) -> None:
        """
        Publish a domain event.
        
        Args:
            event: Event to publish
            wait_for_completion: Whether to wait for all handlers to complete
        """
        logger.info(f"Publishing event: {type(event).__name__} (ID: {event.event_id})")
        
        if wait_for_completion:
            await self._handle_event_sync(event)
        else:
            await self._event_queue.put(event)
    
    async def _handle_event_sync(self, event: DomainEvent) -> None:
        """Handle event synchronously."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers registered for event: {event_type.__name__}")
            return
        
        # Apply middleware (pre-handling)
        for middleware in self._middleware:
            if hasattr(middleware, 'before_handle'):
                await middleware.before_handle(event)
        
        # Execute all handlers
        tasks = []
        for handler in handlers:
            if handler.can_handle(event):
                tasks.append(self._execute_handler(handler, event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler = handlers[i]
                    logger.error(f"Handler {handler.__class__.__name__} failed: {result}")
                    self._failed_events.append((event, handler, result))
        
        # Apply middleware (post-handling)
        for middleware in reversed(self._middleware):
            if hasattr(middleware, 'after_handle'):
                await middleware.after_handle(event)
    
    async def _execute_handler(self, handler: EventHandler, event: DomainEvent) -> None:
        """Execute a single event handler with error handling."""
        try:
            await handler.handle(event)
            logger.debug(f"Handler {handler.__class__.__name__} completed successfully")
        except Exception as e:
            logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
            raise
    
    async def start_processing(self) -> None:
        """Start asynchronous event processing."""
        if self._running:
            return
        
        self._running = True
        logger.info("Started event bus processing")
        
        while self._running:
            try:
                # Wait for event with timeout to allow checking _running flag
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._handle_event_sync(event)
                self._event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    def stop_processing(self) -> None:
        """Stop asynchronous event processing."""
        self._running = False
        logger.info("Stopped event bus processing")
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the event bus."""
        self._middleware.append(middleware)
    
    def get_failed_events(self) -> List[tuple]:
        """Get list of failed events for retry or analysis."""
        return self._failed_events.copy()
    
    def clear_failed_events(self) -> None:
        """Clear the failed events list."""
        self._failed_events.clear()
    
    def get_handler_count(self, event_type: Type[DomainEvent]) -> int:
        """Get number of handlers for an event type."""
        return len(self._handlers.get(event_type, []))


# Specific domain events

class AnnouncementCreatedEvent(DomainEvent):
    """Event fired when an announcement is created."""
    
    announcement_id: str
    title: str
    organization_name: str
    category_code: Optional[str] = None
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Announcement"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("announcement_id")
        super().__init__(**data)


class AnnouncementUpdatedEvent(DomainEvent):
    """Event fired when an announcement is updated."""
    
    announcement_id: str
    changes: Dict[str, Any]
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Announcement"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("announcement_id")
        super().__init__(**data)


class AnnouncementDeletedEvent(DomainEvent):
    """Event fired when an announcement is deleted."""
    
    announcement_id: str
    title: str
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Announcement"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("announcement_id")
        super().__init__(**data)


class BusinessCreatedEvent(DomainEvent):
    """Event fired when a business is created."""
    
    business_id: str
    business_name: str
    category: str
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Business"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("business_id")
        super().__init__(**data)


class BusinessUpdatedEvent(DomainEvent):
    """Event fired when a business is updated."""
    
    business_id: str
    changes: Dict[str, Any]
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Business"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("business_id")
        super().__init__(**data)


class ContentCreatedEvent(DomainEvent):
    """Event fired when content is created."""
    
    content_id: str
    title: str
    content_type: str
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Content"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("content_id")
        super().__init__(**data)


class ContentLikedEvent(DomainEvent):
    """Event fired when content is liked."""
    
    content_id: str
    like_count: int
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "Content"
        if 'aggregate_id' not in data:
            data['aggregate_id'] = data.get("content_id")
        super().__init__(**data)


class DataFetchedEvent(DomainEvent):
    """Event fired when data is fetched from external API."""
    
    data_type: str  # "announcement", "business", "content", "statistics"
    total_fetched: int
    new_items: int
    updated_items: int
    errors: List[str] = []
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "DataCollection"
        super().__init__(**data)


class SystemHealthCheckEvent(DomainEvent):
    """Event fired for system health monitoring."""
    
    component: str
    status: str  # "healthy", "warning", "error"
    metrics: Dict[str, Any]
    
    def __init__(self, **data):
        if 'aggregate_type' not in data:
            data['aggregate_type'] = "System"
        super().__init__(**data)


# Event middleware

class LoggingEventMiddleware:
    """Middleware that logs event processing."""
    
    async def before_handle(self, event: DomainEvent) -> None:
        logger.info(f"Processing event: {type(event).__name__} (ID: {event.event_id})")
    
    async def after_handle(self, event: DomainEvent) -> None:
        logger.info(f"Completed event: {type(event).__name__} (ID: {event.event_id})")


class MetricsEventMiddleware:
    """Middleware that collects event processing metrics."""
    
    def __init__(self):
        self.metrics = {
            'events_processed': 0,
            'events_by_type': {},
            'processing_times': []
        }
    
    async def before_handle(self, event: DomainEvent) -> None:
        self.metrics['events_processed'] += 1
        event_type = type(event).__name__
        if event_type not in self.metrics['events_by_type']:
            self.metrics['events_by_type'][event_type] = 0
        self.metrics['events_by_type'][event_type] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.copy()


# Global event bus instance
event_bus = EventBus()