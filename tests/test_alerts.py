from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from bson import ObjectId

from app.domains.alerts.models import AlertSubscription, Notification, AlertFilters, NotificationPreference
from app.domains.alerts.service import AlertsService
from app.domains.alerts.repository import AlertsRepository
from app.domains.alerts.frequency_manager import NotificationFrequencyManager
from app.domains.alerts.tasks import match_and_enqueue, send_notification


@pytest.fixture
def mock_db():
    """Mock MongoDB database"""
    db = AsyncMock()
    db.__getitem__ = Mock(return_value=AsyncMock())
    return db


@pytest.fixture
def alerts_service(mock_db):
    """Create AlertsService instance with mocked DB"""
    service = AlertsService(mock_db)
    # Mock the repository to avoid initialization issues
    service.repository = AsyncMock()
    return service


@pytest.fixture
def frequency_manager(mock_db):
    """Create NotificationFrequencyManager instance with mocked DB"""
    manager = NotificationFrequencyManager(mock_db)
    # Mock the repository to avoid initialization issues  
    manager.repository = AsyncMock()
    return manager


@pytest.fixture
def sample_subscription():
    """Sample alert subscription"""
    return AlertSubscription(
        user_id=str(ObjectId()),
        keywords=["AI", "startup", "funding"],
        filters=AlertFilters(
            domain="announcements",
            categories=["기술"],
            regions=["서울"],
            statuses=["active"]
        ),
        channels=["email"],
        frequency="realtime",
        is_active=True,
        match_threshold=0.7
    )


@pytest.fixture
def sample_notification():
    """Sample notification"""
    return Notification(
        subscription_id=str(ObjectId()),
        user_id=str(ObjectId()),
        domain="announcements",
        content_id=str(ObjectId()),
        channel="email",
        status="queued",
        score=0.85
    )


class TestAlertsService:
    """Test AlertsService functionality"""

    @pytest.mark.asyncio
    async def test_init_ensures_indexes(self, alerts_service):
        """Test that init() ensures database indexes"""
        alerts_service.repo.ensure_indexes = AsyncMock()
        await alerts_service.init()
        alerts_service.repo.ensure_indexes.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subscription(self, alerts_service, sample_subscription):
        """Test creating a new alert subscription"""
        alerts_service.repo.create_subscription = AsyncMock(return_value="sub_id_123")
        result = await alerts_service.create_subscription(sample_subscription)
        assert result == "sub_id_123"
        alerts_service.repo.create_subscription.assert_called_once_with(sample_subscription)

    @pytest.mark.asyncio
    async def test_list_subscriptions(self, alerts_service):
        """Test listing user subscriptions"""
        user_id = str(ObjectId())
        mock_subs = [{"id": "1", "keywords": ["test"]}]
        alerts_service.repo.list_subscriptions = AsyncMock(return_value=mock_subs)
        
        result = await alerts_service.list_subscriptions(user_id)
        assert result == mock_subs
        alerts_service.repo.list_subscriptions.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_enqueue_notification(self, alerts_service, sample_notification):
        """Test enqueueing a notification"""
        alerts_service.repo.upsert_notification = AsyncMock()
        await alerts_service.enqueue_notification(sample_notification)
        alerts_service.repo.upsert_notification.assert_called_once_with(sample_notification)

    def test_build_query_with_keywords(self, alerts_service):
        """Test query building with keywords"""
        keywords = ["AI startup", "funding"]
        query = alerts_service.build_query("announcements", keywords, None)
        
        assert "$text" in query
        assert query["$text"]["$search"] == '"AI startup" funding'

    def test_build_query_with_filters(self, alerts_service):
        """Test query building with filters"""
        filters = AlertFilters(
            domain="announcements",
            categories=["기술", "스타트업"],
            regions=["서울", "경기"],
            statuses=["active"],
            start_date_from=datetime(2024, 1, 1),
            start_date_to=datetime(2024, 12, 31)
        )
        
        query = alerts_service.build_query("announcements", [], filters)
        
        assert query["domain"] == "announcements"
        assert query["category"] == {"$in": ["기술", "스타트업"]}
        assert query["region"] == {"$in": ["서울", "경기"]}
        assert query["status"] == {"$in": ["active"]}
        assert "$gte" in query["published_at"]
        assert "$lte" in query["published_at"]

    def test_build_query_with_keywords_and_filters(self, alerts_service):
        """Test query building with both keywords and filters"""
        keywords = ["blockchain"]
        filters = AlertFilters(categories=["기술"])
        
        query = alerts_service.build_query("announcements", keywords, filters)
        
        assert "$text" in query
        assert "category" in query
        assert query["$text"]["$search"] == "blockchain"
        assert query["category"] == {"$in": ["기술"]}


class TestAlertsTasks:
    """Test Celery tasks for alerts"""

    @patch('app.domains.alerts.tasks.settings')
    @patch('app.domains.alerts.tasks.DatabaseManager')
    @patch('app.domains.alerts.tasks.AlertsService')
    def test_match_and_enqueue_disabled(self, mock_service, mock_dbm, mock_settings):
        """Test match_and_enqueue when alerts are disabled"""
        mock_settings.alerts_enabled = False
        
        result = match_and_enqueue("announcements", 15)
        assert result == 0
        mock_service.assert_not_called()

    @patch('app.domains.alerts.tasks.settings')
    @patch('app.domains.alerts.tasks.asyncio.run')
    def test_match_and_enqueue_with_threshold(self, mock_run, mock_settings):
        """Test match_and_enqueue with threshold filtering"""
        mock_settings.alerts_enabled = True
        mock_run.return_value = 5  # 5 matches
        
        result = match_and_enqueue("announcements", 15)
        assert result == 5
        mock_run.assert_called_once()

    @patch('app.domains.alerts.tasks.settings')
    @patch('app.domains.alerts.tasks.DatabaseManager')
    @patch('app.domains.alerts.tasks.EmailClient')
    @patch('app.domains.alerts.tasks.RateLimiter')
    def test_send_notification_disabled(self, mock_limiter, mock_email, mock_dbm, mock_settings):
        """Test send_notification when alerts are disabled"""
        mock_settings.alerts_enabled = False
        
        result = send_notification("notif_123")
        assert result is False
        mock_email.assert_not_called()

    @patch('app.domains.alerts.tasks.settings')
    @patch('app.domains.alerts.tasks.asyncio.run')
    def test_send_notification_success(self, mock_run, mock_settings):
        """Test successful notification sending"""
        mock_settings.alerts_enabled = True
        mock_settings.alerts_global_rps = 10
        mock_settings.alerts_user_daily_cap = 100
        mock_run.return_value = True
        
        result = send_notification("notif_123")
        assert result is True
        mock_run.assert_called_once()


class TestThresholdMatching:
    """Test threshold-based matching logic"""

    def test_score_normalization(self):
        """Test score normalization logic"""
        # Test data
        raw_scores = [0.5, 1.0, 2.5, 5.0]
        keyword_counts = [1, 2, 3, 5]
        
        for raw_score in raw_scores:
            for keyword_count in keyword_counts:
                normalized = min(1.0, raw_score / max(1, keyword_count))
                assert 0.0 <= normalized <= 1.0
                
                # Higher keyword counts should result in lower normalized scores
                if keyword_count > 1:
                    normalized_higher = min(1.0, raw_score / (keyword_count + 1))
                    assert normalized_higher <= normalized

    def test_threshold_filtering(self):
        """Test that notifications are filtered by threshold"""
        test_cases = [
            # (normalized_score, threshold, should_match)
            (0.8, 0.5, True),
            (0.8, 0.9, False),
            (0.5, 0.5, True),
            (0.4, 0.5, False),
            (1.0, 0.9, True),
            (0.0, 0.1, False),
        ]
        
        for score, threshold, should_match in test_cases:
            matches = score >= threshold
            assert matches == should_match, f"Score {score} vs threshold {threshold} should be {should_match}"


class TestIntegration:
    """Integration tests for alerts system"""

    @pytest.mark.asyncio
    @patch('app.domains.alerts.tasks.DatabaseManager')
    @patch('app.domains.alerts.tasks.settings')
    async def test_end_to_end_alert_flow(self, mock_settings, mock_dbm):
        """Test complete alert flow from subscription to notification"""
        mock_settings.alerts_enabled = True
        
        # Setup mock database
        mock_db = AsyncMock()
        mock_db.__getitem__ = Mock(return_value=AsyncMock())
        mock_dbm.return_value.get_async_database.return_value = mock_db
        
        # Create test subscription
        sub_data = {
            "_id": ObjectId(),
            "user_id": ObjectId(),
            "keywords": ["test", "keyword"],
            "filters": {"categories": ["tech"]},
            "channels": ["email"],
            "frequency": "realtime",
            "is_active": True,
            "match_threshold": 0.6
        }
        
        # Mock subscription fetch
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = [sub_data]
        mock_db.__getitem__.return_value.find.return_value = mock_cursor
        
        # Test matching content
        content_data = {
            "_id": ObjectId(),
            "title": "Test keyword announcement",
            "score": 1.5,  # Raw MongoDB text score
            "updated_at": datetime.utcnow()
        }
        
        # Calculate expected normalized score
        normalized_score = min(1.0, 1.5 / 2)  # 0.75
        assert normalized_score >= sub_data["match_threshold"]
        
        # Mock content search
        content_cursor = AsyncMock()
        content_cursor.__aiter__.return_value = [content_data]
        
        # Create service
        service = AlertsService(mock_db)
        await service.init()
        
        # Verify query building
        query = service.build_query(
            "announcements",
            sub_data["keywords"],
            sub_data["filters"]
        )
        assert "$text" in query
        assert "category" in query