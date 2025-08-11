"""
Event store implementation for event sourcing.

Provides persistent storage for domain events.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime

from .domain_events import DomainEvent

logger = logging.getLogger(__name__)


class EventStore(ABC):
    """
    Abstract base class for event stores.
    
    Provides persistent storage for domain events.
    """
    
    @abstractmethod
    async def append_event(self, event: DomainEvent) -> None:
        """
        Append an event to the store.
        
        Args:
            event: Domain event to store
        """
        pass
    
    @abstractmethod
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """
        Get events from the store.
        
        Args:
            aggregate_id: Filter by aggregate ID
            aggregate_type: Filter by aggregate type
            from_version: Minimum version to retrieve
            limit: Maximum number of events to return
            
        Returns:
            List of domain events
        """
        pass
    
    @abstractmethod
    async def get_events_stream(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0
    ) -> AsyncIterator[DomainEvent]:
        """
        Get events as an async stream.
        
        Args:
            aggregate_id: Filter by aggregate ID
            aggregate_type: Filter by aggregate type
            from_version: Minimum version to retrieve
            
        Yields:
            Domain events one by one
        """
        pass
    
    @abstractmethod
    async def get_event_count(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None
    ) -> int:
        """
        Get count of events in the store.
        
        Args:
            aggregate_id: Filter by aggregate ID
            aggregate_type: Filter by aggregate type
            
        Returns:
            Number of events
        """
        pass


class InMemoryEventStore(EventStore):
    """
    In-memory implementation of event store.
    
    Suitable for testing and development.
    Events are lost when the application stops.
    """
    
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._event_index: Dict[str, List[int]] = {}  # aggregate_id -> event indices
    
    async def append_event(self, event: DomainEvent) -> None:
        """Append an event to the in-memory store."""
        event_data = {
            'event_id': event.event_id,
            'event_type': type(event).__name__,
            'event_data': json.loads(event.model_dump_json()),
            'timestamp': event.timestamp.isoformat(),
            'version': event.version,
            'aggregate_id': event.aggregate_id,
            'aggregate_type': event.aggregate_type,
            'user_id': event.user_id,
            'correlation_id': event.correlation_id
        }
        
        # Add to main events list
        event_index = len(self._events)
        self._events.append(event_data)
        
        # Update index for fast lookup
        if event.aggregate_id:
            if event.aggregate_id not in self._event_index:
                self._event_index[event.aggregate_id] = []
            self._event_index[event.aggregate_id].append(event_index)
        
        logger.debug(f"Appended event to store: {event.event_id}")
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Get events from the in-memory store."""
        filtered_events = []
        
        if aggregate_id and aggregate_id in self._event_index:
            # Use index for fast lookup
            event_indices = self._event_index[aggregate_id]
            for index in event_indices:
                event_data = self._events[index]
                if self._matches_criteria(event_data, aggregate_type, from_version):
                    filtered_events.append(event_data)
        else:
            # Full scan
            for event_data in self._events:
                if self._matches_criteria(event_data, aggregate_type, from_version, aggregate_id):
                    filtered_events.append(event_data)
        
        # Sort by timestamp
        filtered_events.sort(key=lambda e: e['timestamp'])
        
        # Apply limit
        if limit:
            filtered_events = filtered_events[:limit]
        
        # Convert back to domain events
        domain_events = []
        for event_data in filtered_events:
            domain_event = self._deserialize_event(event_data)
            if domain_event:
                domain_events.append(domain_event)
        
        return domain_events
    
    async def get_events_stream(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0
    ) -> AsyncIterator[DomainEvent]:
        """Get events as an async stream."""
        events = await self.get_events(aggregate_id, aggregate_type, from_version)
        for event in events:
            yield event
    
    async def get_event_count(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None
    ) -> int:
        """Get count of events in the store."""
        count = 0
        
        if aggregate_id and aggregate_id in self._event_index:
            # Use index for fast lookup
            event_indices = self._event_index[aggregate_id]
            for index in event_indices:
                event_data = self._events[index]
                if self._matches_criteria(event_data, aggregate_type, 0):
                    count += 1
        else:
            # Full scan
            for event_data in self._events:
                if self._matches_criteria(event_data, aggregate_type, 0, aggregate_id):
                    count += 1
        
        return count
    
    def _matches_criteria(
        self,
        event_data: Dict[str, Any],
        aggregate_type: Optional[str] = None,
        from_version: int = 0,
        aggregate_id: Optional[str] = None
    ) -> bool:
        """Check if event matches filter criteria."""
        if aggregate_id and event_data.get('aggregate_id') != aggregate_id:
            return False
        
        if aggregate_type and event_data.get('aggregate_type') != aggregate_type:
            return False
        
        if event_data.get('version', 0) < from_version:
            return False
        
        return True
    
    def _deserialize_event(self, event_data: Dict[str, Any]) -> Optional[DomainEvent]:
        """Deserialize event data back to domain event."""
        try:
            # Import event classes dynamically
            from .domain_events import (
                AnnouncementCreatedEvent, AnnouncementUpdatedEvent, AnnouncementDeletedEvent,
                BusinessCreatedEvent, BusinessUpdatedEvent,
                ContentCreatedEvent, ContentLikedEvent,
                DataFetchedEvent, SystemHealthCheckEvent
            )
            
            event_type_map = {
                'AnnouncementCreatedEvent': AnnouncementCreatedEvent,
                'AnnouncementUpdatedEvent': AnnouncementUpdatedEvent,
                'AnnouncementDeletedEvent': AnnouncementDeletedEvent,
                'BusinessCreatedEvent': BusinessCreatedEvent,
                'BusinessUpdatedEvent': BusinessUpdatedEvent,
                'ContentCreatedEvent': ContentCreatedEvent,
                'ContentLikedEvent': ContentLikedEvent,
                'DataFetchedEvent': DataFetchedEvent,
                'SystemHealthCheckEvent': SystemHealthCheckEvent,
            }
            
            event_type = event_data.get('event_type')
            if event_type in event_type_map:
                event_class = event_type_map[event_type]
                return event_class(**event_data['event_data'])
            
            logger.warning(f"Unknown event type: {event_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to deserialize event: {e}")
            return None
    
    def clear(self) -> None:
        """Clear all events from the store (for testing)."""
        self._events.clear()
        self._event_index.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the event store."""
        event_types = {}
        aggregate_types = {}
        
        for event_data in self._events:
            event_type = event_data.get('event_type', 'unknown')
            aggregate_type = event_data.get('aggregate_type', 'unknown')
            
            event_types[event_type] = event_types.get(event_type, 0) + 1
            aggregate_types[aggregate_type] = aggregate_types.get(aggregate_type, 0) + 1
        
        return {
            'total_events': len(self._events),
            'event_types': event_types,
            'aggregate_types': aggregate_types,
            'indexed_aggregates': len(self._event_index)
        }


class MongoEventStore(EventStore):
    """
    MongoDB implementation of event store.
    
    Suitable for production use with persistent storage.
    """
    
    def __init__(self, database, collection_name: str = "events"):
        self._database = database
        self._collection_name = collection_name
        self._collection = None
        if database:
            self._collection = database[collection_name]
    
    @property
    def collection(self):
        """Get MongoDB collection instance."""
        if self._collection is None and self._database is not None:
            self._collection = self._database[self._collection_name]
        return self._collection
    
    async def append_event(self, event: DomainEvent) -> None:
        """Append an event to MongoDB."""
        event_document = {
            'event_id': event.event_id,
            'event_type': type(event).__name__,
            'event_data': json.loads(event.model_dump_json()),
            'timestamp': event.timestamp,
            'version': event.version,
            'aggregate_id': event.aggregate_id,
            'aggregate_type': event.aggregate_type,
            'user_id': event.user_id,
            'correlation_id': event.correlation_id,
            'created_at': datetime.utcnow()
        }
        
        try:
            self.collection.insert_one(event_document)
            logger.debug(f"Appended event to MongoDB: {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to append event to MongoDB: {e}")
            raise
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Get events from MongoDB."""
        try:
            # Build query
            query = {}
            if aggregate_id:
                query['aggregate_id'] = aggregate_id
            if aggregate_type:
                query['aggregate_type'] = aggregate_type
            if from_version > 0:
                query['version'] = {'$gte': from_version}
            
            # Execute query
            cursor = self.collection.find(query).sort('timestamp', 1)
            if limit:
                cursor = cursor.limit(limit)
            
            # Convert to domain events
            domain_events = []
            for event_doc in cursor:
                domain_event = self._deserialize_event(event_doc)
                if domain_event:
                    domain_events.append(domain_event)
            
            return domain_events
            
        except Exception as e:
            logger.error(f"Failed to get events from MongoDB: {e}")
            return []
    
    async def get_events_stream(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        from_version: int = 0
    ) -> AsyncIterator[DomainEvent]:
        """Get events as an async stream from MongoDB."""
        events = await self.get_events(aggregate_id, aggregate_type, from_version)
        for event in events:
            yield event
    
    async def get_event_count(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None
    ) -> int:
        """Get count of events in MongoDB."""
        try:
            query = {}
            if aggregate_id:
                query['aggregate_id'] = aggregate_id
            if aggregate_type:
                query['aggregate_type'] = aggregate_type
            
            return self.collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"Failed to get event count from MongoDB: {e}")
            return 0
    
    def _deserialize_event(self, event_doc: Dict[str, Any]) -> Optional[DomainEvent]:
        """Deserialize event document back to domain event."""
        try:
            # Same deserialization logic as InMemoryEventStore
            from .domain_events import (
                AnnouncementCreatedEvent, AnnouncementUpdatedEvent, AnnouncementDeletedEvent,
                BusinessCreatedEvent, BusinessUpdatedEvent,
                ContentCreatedEvent, ContentLikedEvent,
                DataFetchedEvent, SystemHealthCheckEvent
            )
            
            event_type_map = {
                'AnnouncementCreatedEvent': AnnouncementCreatedEvent,
                'AnnouncementUpdatedEvent': AnnouncementUpdatedEvent,
                'AnnouncementDeletedEvent': AnnouncementDeletedEvent,
                'BusinessCreatedEvent': BusinessCreatedEvent,
                'BusinessUpdatedEvent': BusinessUpdatedEvent,
                'ContentCreatedEvent': ContentCreatedEvent,
                'ContentLikedEvent': ContentLikedEvent,
                'DataFetchedEvent': DataFetchedEvent,
                'SystemHealthCheckEvent': SystemHealthCheckEvent,
            }
            
            event_type = event_doc.get('event_type')
            if event_type in event_type_map:
                event_class = event_type_map[event_type]
                return event_class(**event_doc['event_data'])
            
            logger.warning(f"Unknown event type: {event_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to deserialize event: {e}")
            return None