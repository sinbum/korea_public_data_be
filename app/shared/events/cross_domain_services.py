"""
Cross-domain services implementation for event-driven architecture.

Provides services that operate across multiple domains using events.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from .domain_events import (
    DomainEvent, EventHandler, event_bus,
    AnnouncementCreatedEvent, AnnouncementUpdatedEvent, AnnouncementDeletedEvent,
    BusinessCreatedEvent, BusinessUpdatedEvent,
    ContentCreatedEvent, ContentLikedEvent,
    DataFetchedEvent, SystemHealthCheckEvent
)
from .event_store import EventStore, InMemoryEventStore

logger = logging.getLogger(__name__)


class CrossDomainService(ABC):
    """
    Base class for cross-domain services.
    
    These services handle business logic that spans multiple domains.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        self.event_store = event_store or InMemoryEventStore()
        self._handlers_registered = False
    
    def register_handlers(self) -> None:
        """Register event handlers for this service."""
        if not self._handlers_registered:
            self._setup_handlers()
            self._handlers_registered = True
    
    @abstractmethod
    def _setup_handlers(self) -> None:
        """Setup event handlers specific to this service."""
        pass


class DataSyncService(CrossDomainService):
    """
    Service for synchronizing data across domains.
    
    Handles data consistency and cross-domain updates.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        super().__init__(event_store)
        self._sync_queue: asyncio.Queue = asyncio.Queue()
        self._sync_running = False
    
    def _setup_handlers(self) -> None:
        """Setup handlers for data synchronization events."""
        event_bus.subscribe(AnnouncementCreatedEvent, AnnouncementSyncHandler(self))
        event_bus.subscribe(BusinessCreatedEvent, BusinessSyncHandler(self))
        event_bus.subscribe(ContentCreatedEvent, ContentSyncHandler(self))
    
    async def start_sync_processing(self) -> None:
        """Start the data synchronization processing loop."""
        if self._sync_running:
            return
        
        self._sync_running = True
        logger.info("Started data sync processing")
        
        while self._sync_running:
            try:
                sync_task = await asyncio.wait_for(self._sync_queue.get(), timeout=1.0)
                await self._process_sync_task(sync_task)
                self._sync_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in sync processing: {e}")
    
    def stop_sync_processing(self) -> None:
        """Stop the data synchronization processing."""
        self._sync_running = False
        logger.info("Stopped data sync processing")
    
    async def sync_announcement_data(self, announcement_id: str, data: Dict[str, Any]) -> None:
        """Sync announcement data across related domains."""
        await self._sync_queue.put({
            'type': 'announcement_sync',
            'id': announcement_id,
            'data': data,
            'timestamp': datetime.utcnow()
        })
    
    async def sync_business_data(self, business_id: str, data: Dict[str, Any]) -> None:
        """Sync business data across related domains."""
        await self._sync_queue.put({
            'type': 'business_sync',
            'id': business_id,
            'data': data,
            'timestamp': datetime.utcnow()
        })
    
    async def sync_content_data(self, content_id: str, data: Dict[str, Any]) -> None:
        """Sync content data across related domains."""
        await self._sync_queue.put({
            'type': 'content_sync',
            'id': content_id,
            'data': data,
            'timestamp': datetime.utcnow()
        })
    
    async def _process_sync_task(self, task: Dict[str, Any]) -> None:
        """Process a synchronization task."""
        try:
            sync_type = task.get('type')
            if sync_type == 'announcement_sync':
                await self._sync_announcement_relations(task)
            elif sync_type == 'business_sync':
                await self._sync_business_relations(task)
            elif sync_type == 'content_sync':
                await self._sync_content_relations(task)
            
            logger.debug(f"Processed sync task: {sync_type}")
            
        except Exception as e:
            logger.error(f"Failed to process sync task: {e}")
    
    async def _sync_announcement_relations(self, task: Dict[str, Any]) -> None:
        """Sync announcement with related business and content data."""
        # Implementation would sync announcement data with business profiles
        # and related content items
        pass
    
    async def _sync_business_relations(self, task: Dict[str, Any]) -> None:
        """Sync business with related announcements and content."""
        # Implementation would update business references in announcements
        # and content items
        pass
    
    async def _sync_content_relations(self, task: Dict[str, Any]) -> None:
        """Sync content with related announcements and businesses."""
        # Implementation would update content references and tags
        pass


class NotificationService(CrossDomainService):
    """
    Service for handling notifications across domains.
    
    Manages user notifications and system alerts.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        super().__init__(event_store)
        self._notification_channels: Dict[str, List[str]] = {}
        self._notification_history: List[Dict[str, Any]] = []
    
    def _setup_handlers(self) -> None:
        """Setup handlers for notification events."""
        event_bus.subscribe(AnnouncementCreatedEvent, NotificationHandler(self, 'announcement_created'))
        event_bus.subscribe(BusinessCreatedEvent, NotificationHandler(self, 'business_created'))
        event_bus.subscribe(ContentLikedEvent, NotificationHandler(self, 'content_liked'))
        event_bus.subscribe(SystemHealthCheckEvent, SystemNotificationHandler(self))
    
    async def subscribe_user(self, user_id: str, channels: List[str]) -> None:
        """Subscribe a user to notification channels."""
        if user_id not in self._notification_channels:
            self._notification_channels[user_id] = []
        
        for channel in channels:
            if channel not in self._notification_channels[user_id]:
                self._notification_channels[user_id].append(channel)
        
        logger.info(f"User {user_id} subscribed to channels: {channels}")
    
    async def unsubscribe_user(self, user_id: str, channels: List[str]) -> None:
        """Unsubscribe a user from notification channels."""
        if user_id in self._notification_channels:
            for channel in channels:
                if channel in self._notification_channels[user_id]:
                    self._notification_channels[user_id].remove(channel)
        
        logger.info(f"User {user_id} unsubscribed from channels: {channels}")
    
    async def send_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        target_users: Optional[List[str]] = None
    ) -> None:
        """Send a notification to users."""
        notification = {
            'id': f"notif_{datetime.utcnow().timestamp()}",
            'type': notification_type,
            'title': title,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow(),
            'sent_to': target_users or []
        }
        
        # Store notification history
        self._notification_history.append(notification)
        
        # Send to specific users or broadcast
        if target_users:
            for user_id in target_users:
                await self._send_to_user(user_id, notification)
        else:
            await self._broadcast_notification(notification)
        
        logger.info(f"Sent notification: {title} to {len(target_users or [])} users")
    
    async def _send_to_user(self, user_id: str, notification: Dict[str, Any]) -> None:
        """Send notification to a specific user."""
        # Implementation would integrate with email, SMS, push notifications, etc.
        logger.debug(f"Sending notification to user {user_id}: {notification['title']}")
    
    async def _broadcast_notification(self, notification: Dict[str, Any]) -> None:
        """Broadcast notification to all subscribed users."""
        for user_id in self._notification_channels:
            await self._send_to_user(user_id, notification)
    
    def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notifications for a specific user."""
        user_notifications = [
            notif for notif in self._notification_history
            if user_id in notif.get('sent_to', []) or not notif.get('sent_to')
        ]
        return sorted(user_notifications, key=lambda x: x['timestamp'], reverse=True)[:limit]


class AuditService(CrossDomainService):
    """
    Service for auditing and logging cross-domain activities.
    
    Tracks changes and maintains audit trails.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        super().__init__(event_store)
        self._audit_trail: List[Dict[str, Any]] = []
    
    def _setup_handlers(self) -> None:
        """Setup handlers for audit events."""
        # Subscribe to all domain events for auditing
        event_bus.subscribe(AnnouncementCreatedEvent, AuditHandler(self, 'create'))
        event_bus.subscribe(AnnouncementUpdatedEvent, AuditHandler(self, 'update'))
        event_bus.subscribe(AnnouncementDeletedEvent, AuditHandler(self, 'delete'))
        event_bus.subscribe(BusinessCreatedEvent, AuditHandler(self, 'create'))
        event_bus.subscribe(BusinessUpdatedEvent, AuditHandler(self, 'update'))
        event_bus.subscribe(ContentCreatedEvent, AuditHandler(self, 'create'))
        event_bus.subscribe(DataFetchedEvent, AuditHandler(self, 'data_fetch'))
    
    async def log_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event."""
        audit_event = {
            'id': f"audit_{datetime.utcnow().timestamp()}",
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'user_id': user_id,
            'changes': changes or {},
            'metadata': metadata or {},
            'timestamp': datetime.utcnow()
        }
        
        self._audit_trail.append(audit_event)
        await self.event_store.append_event(DomainEvent(
            aggregate_type="Audit",
            aggregate_id=audit_event['id'],
            user_id=user_id
        ))
        
        logger.info(f"Audit logged: {action} on {resource_type}:{resource_id}")
    
    def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail with optional filters."""
        filtered_trail = self._audit_trail
        
        if resource_type:
            filtered_trail = [e for e in filtered_trail if e['resource_type'] == resource_type]
        
        if resource_id:
            filtered_trail = [e for e in filtered_trail if e['resource_id'] == resource_id]
        
        if user_id:
            filtered_trail = [e for e in filtered_trail if e['user_id'] == user_id]
        
        return sorted(filtered_trail, key=lambda x: x['timestamp'], reverse=True)[:limit]


class StatisticsAggregationService(CrossDomainService):
    """
    Service for aggregating statistics across domains.
    
    Collects and processes metrics from all domains.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        super().__init__(event_store)
        self._metrics: Dict[str, Any] = {
            'announcements': {'total': 0, 'created_today': 0},
            'businesses': {'total': 0, 'created_today': 0},
            'contents': {'total': 0, 'created_today': 0, 'total_likes': 0},
            'data_fetches': {'total': 0, 'successful': 0, 'failed': 0}
        }
    
    def _setup_handlers(self) -> None:
        """Setup handlers for statistics events."""
        event_bus.subscribe(AnnouncementCreatedEvent, StatisticsHandler(self, 'announcement_created'))
        event_bus.subscribe(BusinessCreatedEvent, StatisticsHandler(self, 'business_created'))
        event_bus.subscribe(ContentCreatedEvent, StatisticsHandler(self, 'content_created'))
        event_bus.subscribe(ContentLikedEvent, StatisticsHandler(self, 'content_liked'))
        event_bus.subscribe(DataFetchedEvent, StatisticsHandler(self, 'data_fetched'))
    
    async def update_announcement_stats(self, event: AnnouncementCreatedEvent) -> None:
        """Update announcement statistics."""
        self._metrics['announcements']['total'] += 1
        
        # Check if created today
        if event.timestamp.date() == datetime.utcnow().date():
            self._metrics['announcements']['created_today'] += 1
    
    async def update_business_stats(self, event: BusinessCreatedEvent) -> None:
        """Update business statistics."""
        self._metrics['businesses']['total'] += 1
        
        if event.timestamp.date() == datetime.utcnow().date():
            self._metrics['businesses']['created_today'] += 1
    
    async def update_content_stats(self, event: DomainEvent) -> None:
        """Update content statistics."""
        if isinstance(event, ContentCreatedEvent):
            self._metrics['contents']['total'] += 1
            if event.timestamp.date() == datetime.utcnow().date():
                self._metrics['contents']['created_today'] += 1
        elif isinstance(event, ContentLikedEvent):
            self._metrics['contents']['total_likes'] += 1
    
    async def update_data_fetch_stats(self, event: DataFetchedEvent) -> None:
        """Update data fetch statistics."""
        self._metrics['data_fetches']['total'] += 1
        
        if event.errors:
            self._metrics['data_fetches']['failed'] += 1
        else:
            self._metrics['data_fetches']['successful'] += 1
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current aggregated metrics."""
        return {
            **self._metrics,
            'last_updated': datetime.utcnow().isoformat(),
            'system_health': self._calculate_system_health()
        }
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health score."""
        total_fetches = self._metrics['data_fetches']['total']
        if total_fetches == 0:
            return 'unknown'
        
        success_rate = self._metrics['data_fetches']['successful'] / total_fetches
        
        if success_rate >= 0.95:
            return 'excellent'
        elif success_rate >= 0.85:
            return 'good'
        elif success_rate >= 0.70:
            return 'fair'
        else:
            return 'poor'


# Event Handlers

class AnnouncementSyncHandler(EventHandler):
    """Handler for announcement synchronization events."""
    
    def __init__(self, sync_service: DataSyncService):
        self.sync_service = sync_service
    
    async def handle(self, event: AnnouncementCreatedEvent) -> None:
        await self.sync_service.sync_announcement_data(
            event.announcement_id,
            {
                'title': event.title,
                'organization_name': event.organization_name,
                'category_code': event.category_code
            }
        )


class BusinessSyncHandler(EventHandler):
    """Handler for business synchronization events."""
    
    def __init__(self, sync_service: DataSyncService):
        self.sync_service = sync_service
    
    async def handle(self, event: BusinessCreatedEvent) -> None:
        await self.sync_service.sync_business_data(
            event.business_id,
            {
                'business_name': event.business_name,
                'category': event.category
            }
        )


class ContentSyncHandler(EventHandler):
    """Handler for content synchronization events."""
    
    def __init__(self, sync_service: DataSyncService):
        self.sync_service = sync_service
    
    async def handle(self, event: ContentCreatedEvent) -> None:
        await self.sync_service.sync_content_data(
            event.content_id,
            {
                'title': event.title,
                'content_type': event.content_type
            }
        )


class NotificationHandler(EventHandler):
    """Handler for domain events that trigger notifications."""
    
    def __init__(self, notification_service: NotificationService, notification_type: str):
        self.notification_service = notification_service
        self.notification_type = notification_type
    
    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, AnnouncementCreatedEvent):
            await self.notification_service.send_notification(
                self.notification_type,
                "새로운 공고가 등록되었습니다",
                f"{event.title} - {event.organization_name}"
            )
        elif isinstance(event, BusinessCreatedEvent):
            await self.notification_service.send_notification(
                self.notification_type,
                "새로운 기업이 등록되었습니다",
                f"{event.business_name} ({event.category})"
            )
        elif isinstance(event, ContentLikedEvent):
            await self.notification_service.send_notification(
                self.notification_type,
                "콘텐츠 좋아요",
                f"콘텐츠 좋아요 수: {event.like_count}"
            )


class SystemNotificationHandler(EventHandler):
    """Handler for system health notifications."""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
    
    async def handle(self, event: SystemHealthCheckEvent) -> None:
        if event.status in ['warning', 'error']:
            await self.notification_service.send_notification(
                'system_alert',
                f"시스템 {event.status.upper()}: {event.component}",
                f"컴포넌트 상태: {event.status}",
                data=event.metrics
            )


class AuditHandler(EventHandler):
    """Handler for audit logging."""
    
    def __init__(self, audit_service: AuditService, action: str):
        self.audit_service = audit_service
        self.action = action
    
    async def handle(self, event: DomainEvent) -> None:
        await self.audit_service.log_audit_event(
            action=self.action,
            resource_type=event.aggregate_type or 'unknown',
            resource_id=event.aggregate_id or 'unknown',
            user_id=event.user_id,
            metadata={
                'event_id': event.event_id,
                'correlation_id': event.correlation_id,
                'timestamp': event.timestamp.isoformat()
            }
        )


class StatisticsHandler(EventHandler):
    """Handler for statistics aggregation."""
    
    def __init__(self, stats_service: StatisticsAggregationService, event_type: str):
        self.stats_service = stats_service
        self.event_type = event_type
    
    async def handle(self, event: DomainEvent) -> None:
        if self.event_type == 'announcement_created' and isinstance(event, AnnouncementCreatedEvent):
            await self.stats_service.update_announcement_stats(event)
        elif self.event_type == 'business_created' and isinstance(event, BusinessCreatedEvent):
            await self.stats_service.update_business_stats(event)
        elif self.event_type in ['content_created', 'content_liked']:
            await self.stats_service.update_content_stats(event)
        elif self.event_type == 'data_fetched' and isinstance(event, DataFetchedEvent):
            await self.stats_service.update_data_fetch_stats(event)


# Factory function to create and configure cross-domain services
def create_cross_domain_services(event_store: Optional[EventStore] = None) -> Dict[str, CrossDomainService]:
    """
    Create and configure all cross-domain services.
    
    Returns:
        Dictionary of configured cross-domain services
    """
    services = {
        'data_sync': DataSyncService(event_store),
        'notification': NotificationService(event_store),
        'audit': AuditService(event_store),
        'statistics': StatisticsAggregationService(event_store)
    }
    
    # Register all handlers
    for service in services.values():
        service.register_handlers()
    
    logger.info("Cross-domain services created and configured")
    return services