"""
Domain events and event handling system.

Provides event-driven architecture support for cross-domain communication.
"""

from .domain_events import DomainEvent, EventHandler, EventBus
from .event_store import EventStore, InMemoryEventStore
from .cross_domain_services import (
    DataSyncService,
    NotificationService,
    AuditService,
    StatisticsAggregationService
)

__all__ = [
    # Event system
    'DomainEvent',
    'EventHandler', 
    'EventBus',
    'EventStore',
    'InMemoryEventStore',
    
    # Cross-domain services
    'DataSyncService',
    'NotificationService',
    'AuditService',
    'StatisticsAggregationService'
]