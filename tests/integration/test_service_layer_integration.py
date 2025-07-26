"""
Integration tests for the service layer architecture.

Tests the complete service layer including:
- BaseService template methods
- Domain service implementations
- CQRS pattern integration
- Event-driven architecture
- Cross-domain services
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from app.shared.interfaces.base_service import BaseService
from app.shared.cqrs.commands import CreateAnnouncementCommand, UpdateAnnouncementCommand
from app.shared.cqrs.queries import GetAnnouncementQuery, ListAnnouncementsQuery
from app.shared.cqrs.bus import CommandBus, QueryBus
from app.shared.events.domain_events import (
    EventBus, AnnouncementCreatedEvent, BusinessCreatedEvent,
    ContentCreatedEvent, event_bus
)
from app.shared.events.event_store import InMemoryEventStore
from app.shared.events.cross_domain_services import (
    DataSyncService, NotificationService, AuditService,
    StatisticsAggregationService, create_cross_domain_services
)
from app.domains.announcements.service import AnnouncementService
from app.domains.businesses.service import BusinessService
from app.domains.contents.service import ContentService
from app.domains.statistics.service import StatisticsService


class MockRepository:
    """Mock repository for testing service layer."""
    
    def __init__(self):
        self.data = {}
        self.next_id = 1
    
    async def get_by_id(self, item_id: str) -> Dict[str, Any]:
        return self.data.get(item_id)
    
    async def get_list(self, offset: int, limit: int, filters: Dict, sort_by: str = None, sort_order: str = "desc") -> tuple[List[Dict[str, Any]], int]:
        items = list(self.data.values())
        total = len(items)
        return items[offset:offset + limit], total
    
    async def create(self, item_data) -> Dict[str, Any]:
        item_id = str(self.next_id)
        self.next_id += 1
        
        if hasattr(item_data, 'model_dump'):
            data = item_data.model_dump()
        else:
            data = item_data
        
        data['id'] = item_id
        data['created_at'] = datetime.utcnow()
        self.data[item_id] = data
        return data
    
    async def update(self, item_id: str, update_data) -> Dict[str, Any]:
        if item_id in self.data:
            if hasattr(update_data, 'model_dump'):
                updates = update_data.model_dump(exclude_unset=True)
            else:
                updates = update_data
            
            self.data[item_id].update(updates)
            self.data[item_id]['updated_at'] = datetime.utcnow()
            return self.data[item_id]
        return None
    
    async def delete(self, item_id: str) -> bool:
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False
    
    async def count(self) -> int:
        return len(self.data)


class TestServiceLayerIntegration:
    """Integration tests for the complete service layer."""
    
    @pytest.fixture
    def mock_repository(self):
        return MockRepository()
    
    @pytest.fixture
    def event_store(self):
        return InMemoryEventStore()
    
    @pytest.fixture
    def event_bus_fixture(self):
        # Use a fresh event bus for each test
        return EventBus()
    
    @pytest.fixture
    def mock_api_client(self):
        client = Mock()
        client.get_announcements = Mock(return_value=Mock(
            success=True,
            data=Mock(data=[])
        ))
        return client
    
    @pytest.fixture
    async def announcement_service(self, mock_repository, mock_api_client):
        """Create AnnouncementService with mocked dependencies."""
        service = AnnouncementService(mock_repository, mock_api_client)
        return service
    
    @pytest.fixture
    async def business_service(self, mock_repository, mock_api_client):
        """Create BusinessService with mocked dependencies."""
        service = BusinessService(mock_repository, mock_api_client)
        return service
    
    @pytest.fixture
    async def content_service(self, mock_repository, mock_api_client):
        """Create ContentService with mocked dependencies."""
        service = ContentService(mock_repository, mock_api_client)
        return service
    
    @pytest.fixture
    async def statistics_service(self, mock_repository, mock_api_client):
        """Create StatisticsService with mocked dependencies."""
        service = StatisticsService(mock_repository, mock_api_client)
        return service
    
    @pytest.mark.asyncio
    async def test_base_service_template_methods(self, announcement_service):
        """Test that BaseService template methods work correctly."""
        
        # Test create flow
        create_data = {
            'title': '테스트 공고',
            'organization_name': '테스트 기관',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        result = await announcement_service.create(create_data)
        
        assert result is not None
        assert 'id' in result
        assert result['title'] == '테스트 공고'
        
        # Test get by id
        item_id = result['id']
        retrieved = await announcement_service.get_by_id(item_id)
        
        assert retrieved is not None
        assert retrieved['title'] == '테스트 공고'
        
        # Test update
        update_data = {'title': '수정된 공고'}
        updated = await announcement_service.update(item_id, update_data)
        
        assert updated is not None
        assert updated['title'] == '수정된 공고'
        
        # Test list
        list_result = await announcement_service.get_list(page=1, limit=10)
        
        assert list_result is not None
        assert len(list_result.data) >= 1
        
        # Test delete
        deleted = await announcement_service.delete(item_id)
        assert deleted is True
        
        # Verify deletion
        retrieved_after_delete = await announcement_service.get_by_id(item_id)
        assert retrieved_after_delete is None
    
    @pytest.mark.asyncio
    async def test_cqrs_integration(self):
        """Test CQRS command and query bus integration."""
        
        command_bus = CommandBus()
        query_bus = QueryBus()
        
        # Mock handlers
        create_handler = AsyncMock(return_value={'id': '1', 'title': '테스트 공고'})
        get_handler = AsyncMock(return_value={'id': '1', 'title': '테스트 공고'})
        
        # Register handlers
        command_bus.register_handler(CreateAnnouncementCommand, create_handler)
        query_bus.register_handler(GetAnnouncementQuery, get_handler)
        
        # Test command execution
        create_command = CreateAnnouncementCommand(
            title='테스트 공고',
            organization_name='테스트 기관',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        
        create_result = await command_bus.execute(create_command)
        
        assert create_result is not None
        assert create_result['title'] == '테스트 공고'
        create_handler.assert_called_once()
        
        # Test query execution
        get_query = GetAnnouncementQuery(announcement_id='1')
        
        get_result = await query_bus.execute(get_query)
        
        assert get_result is not None
        assert get_result['id'] == '1'
        get_handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_driven_architecture(self, event_bus_fixture, event_store):
        """Test event-driven architecture integration."""
        
        events_received = []
        
        class TestEventHandler:
            async def handle(self, event):
                events_received.append(event)
        
        handler = TestEventHandler()
        
        # Subscribe to events
        event_bus_fixture.subscribe(AnnouncementCreatedEvent, handler)
        event_bus_fixture.subscribe(BusinessCreatedEvent, handler)
        
        # Publish events
        announcement_event = AnnouncementCreatedEvent(
            announcement_id='1',
            title='테스트 공고',
            organization_name='테스트 기관'
        )
        
        business_event = BusinessCreatedEvent(
            business_id='1',
            business_name='테스트 기업',
            category='스타트업'
        )
        
        await event_bus_fixture.publish(announcement_event, wait_for_completion=True)
        await event_bus_fixture.publish(business_event, wait_for_completion=True)
        
        # Verify events were handled
        assert len(events_received) == 2
        assert isinstance(events_received[0], AnnouncementCreatedEvent)
        assert isinstance(events_received[1], BusinessCreatedEvent)
        
        # Test event store
        await event_store.append_event(announcement_event)
        await event_store.append_event(business_event)
        
        stored_events = await event_store.get_events()
        assert len(stored_events) == 2
    
    @pytest.mark.asyncio
    async def test_cross_domain_services_integration(self, event_store):
        """Test cross-domain services integration."""
        
        # Create services
        services = create_cross_domain_services(event_store)
        
        assert 'data_sync' in services
        assert 'notification' in services
        assert 'audit' in services
        assert 'statistics' in services
        
        # Test data sync service
        data_sync = services['data_sync']
        await data_sync.sync_announcement_data('1', {'title': '테스트 공고'})
        
        # Test notification service
        notification = services['notification']
        await notification.subscribe_user('user1', ['announcements'])
        await notification.send_notification(
            'test',
            '테스트 알림',
            '테스트 메시지',
            target_users=['user1']
        )
        
        user_notifications = notification.get_user_notifications('user1')
        assert len(user_notifications) == 1
        
        # Test audit service
        audit = services['audit']
        await audit.log_audit_event(
            'create',
            'Announcement',
            '1',
            'user1',
            {'title': '테스트 공고'}
        )
        
        audit_trail = audit.get_audit_trail()
        assert len(audit_trail) == 1
        
        # Test statistics service
        stats = services['statistics']
        announcement_event = AnnouncementCreatedEvent(
            announcement_id='1',
            title='테스트 공고',
            organization_name='테스트 기관'
        )
        
        await stats.update_announcement_stats(announcement_event)
        metrics = stats.get_current_metrics()
        
        assert metrics['announcements']['total'] == 1
    
    @pytest.mark.asyncio
    async def test_service_layer_error_handling(self, announcement_service):
        """Test error handling across the service layer."""
        
        # Test handling of non-existent items
        non_existent = await announcement_service.get_by_id('non-existent')
        assert non_existent is None
        
        # Test update of non-existent item
        update_result = await announcement_service.update('non-existent', {'title': '수정'})
        assert update_result is None
        
        # Test delete of non-existent item
        delete_result = await announcement_service.delete('non-existent')
        assert delete_result is False
    
    @pytest.mark.asyncio
    async def test_service_layer_validation(self, announcement_service):
        """Test validation in the service layer."""
        
        # Test validation hooks are called
        with patch.object(announcement_service, '_validate_create_data') as mock_validate:
            create_data = {
                'title': '테스트 공고',
                'organization_name': '테스트 기관',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            }
            
            await announcement_service.create(create_data)
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_layer_hooks(self, announcement_service):
        """Test that service layer hooks are properly called."""
        
        # Test before/after hooks
        with patch.object(announcement_service, '_before_create') as before_mock:
            with patch.object(announcement_service, '_after_create') as after_mock:
                create_data = {
                    'title': '테스트 공고',
                    'organization_name': '테스트 기관',
                    'start_date': '2024-01-01',
                    'end_date': '2024-12-31'
                }
                
                result = await announcement_service.create(create_data)
                
                before_mock.assert_called_once()
                after_mock.assert_called_once()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_multiple_service_interaction(self, announcement_service, business_service, content_service):
        """Test interaction between multiple services."""
        
        # Create announcement
        announcement_data = {
            'title': '테스트 공고',
            'organization_name': '테스트 기관',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        announcement = await announcement_service.create(announcement_data)
        
        # Create related business
        business_data = {
            'business_name': '테스트 기업',
            'category': '스타트업',
            'description': '테스트 기업 설명'
        }
        business = await business_service.create(business_data)
        
        # Create related content
        content_data = {
            'title': '관련 콘텐츠',
            'content_type': '가이드',
            'summary': '테스트 콘텐츠 요약'
        }
        content = await content_service.create(content_data)
        
        # Verify all items were created
        assert announcement is not None
        assert business is not None
        assert content is not None
        
        # Verify they can be retrieved
        retrieved_announcement = await announcement_service.get_by_id(announcement['id'])
        retrieved_business = await business_service.get_by_id(business['id'])
        retrieved_content = await content_service.get_by_id(content['id'])
        
        assert retrieved_announcement is not None
        assert retrieved_business is not None
        assert retrieved_content is not None
    
    @pytest.mark.asyncio
    async def test_service_layer_concurrency(self, announcement_service):
        """Test service layer under concurrent operations."""
        
        # Create multiple items concurrently
        tasks = []
        for i in range(10):
            create_data = {
                'title': f'테스트 공고 {i}',
                'organization_name': f'테스트 기관 {i}',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            }
            tasks.append(announcement_service.create(create_data))
        
        results = await asyncio.gather(*tasks)
        
        # Verify all items were created
        assert len(results) == 10
        for result in results:
            assert result is not None
            assert 'id' in result
        
        # Verify all items are retrievable
        list_result = await announcement_service.get_list(page=1, limit=20)
        assert len(list_result.data) == 10
    
    @pytest.mark.asyncio
    async def test_service_layer_performance(self, announcement_service):
        """Test service layer performance characteristics."""
        
        # Measure create performance
        start_time = datetime.utcnow()
        
        for i in range(100):
            create_data = {
                'title': f'성능 테스트 공고 {i}',
                'organization_name': f'성능 테스트 기관 {i}',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31'
            }
            await announcement_service.create(create_data)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should be able to create 100 items in reasonable time (< 10 seconds)
        assert duration < 10.0
        
        # Measure list performance
        start_time = datetime.utcnow()
        
        list_result = await announcement_service.get_list(page=1, limit=100)
        
        end_time = datetime.utcnow()
        list_duration = (end_time - start_time).total_seconds()
        
        # List operation should be fast (< 1 second)
        assert list_duration < 1.0
        assert len(list_result.data) == 100


class TestServiceLayerValidation:
    """Tests for service layer validation and error handling."""
    
    @pytest.fixture
    def mock_repository(self):
        return MockRepository()
    
    @pytest.fixture
    def mock_api_client(self):
        return Mock()
    
    @pytest.mark.asyncio
    async def test_input_validation(self, mock_repository, mock_api_client):
        """Test input validation in services."""
        
        service = AnnouncementService(mock_repository, mock_api_client)
        
        # Test invalid input data
        invalid_data = {}  # Missing required fields
        
        # Should handle validation gracefully
        try:
            result = await service.create(invalid_data)
            # If no exception, result should be None or contain error info
            assert result is None or 'error' in result
        except Exception as e:
            # Validation exception is acceptable
            assert 'validation' in str(e).lower() or 'required' in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_repository_error_handling(self, mock_api_client):
        """Test handling of repository errors."""
        
        # Mock repository that raises exceptions
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
        mock_repo.create = AsyncMock(side_effect=Exception("Database error"))
        
        service = AnnouncementService(mock_repo, mock_api_client)
        
        # Should handle repository errors gracefully
        result = await service.get_by_id('1')
        assert result is None
        
        create_data = {
            'title': '테스트 공고',
            'organization_name': '테스트 기관',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        try:
            create_result = await service.create(create_data)
            assert create_result is None or 'error' in create_result
        except Exception:
            # Exception handling is acceptable
            pass
    
    @pytest.mark.asyncio
    async def test_api_client_error_handling(self, mock_repository):
        """Test handling of API client errors."""
        
        # Mock API client that raises exceptions
        mock_client = Mock()
        mock_client.get_announcements = Mock(side_effect=Exception("API error"))
        
        service = AnnouncementService(mock_repository, mock_client)
        
        # Should handle API errors gracefully
        result = await service.fetch_announcements_from_api()
        assert result.errors  # Should contain error information


if __name__ == '__main__':
    pytest.main([__file__, '-v'])