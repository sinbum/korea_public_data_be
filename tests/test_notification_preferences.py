from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.domains.alerts.models import NotificationPreference
from app.domains.alerts.repository import AlertsRepository
from app.domains.alerts.frequency_manager import NotificationFrequencyManager
from app.domains.alerts.schemas import NotificationPreferenceUpdate, NotificationPreferenceResponse


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    return Mock()


@pytest.fixture
def repository(mock_db):
    """Create AlertsRepository instance for testing"""
    return AlertsRepository(mock_db)


@pytest.fixture
def frequency_manager(mock_db):
    """Create NotificationFrequencyManager instance for testing"""
    return NotificationFrequencyManager(mock_db)


@pytest.fixture
def sample_user_preferences():
    """Sample user notification preferences"""
    return {
        "_id": "pref123",
        "user_id": "user123",
        "email_enabled": True,
        "web_enabled": True,
        "push_enabled": False,
        "sms_enabled": False,
        "new_announcements": True,
        "deadline_reminders": True,
        "digest_notifications": True,
        "system_notifications": True,
        "marketing_notifications": False,
        "digest_frequency": "daily",
        "deadline_reminder_days": [7, 3, 1],
        "max_daily_notifications": 10,
        "quiet_hours_enabled": True,
        "quiet_hours_start": 22,
        "quiet_hours_end": 7,
        "quiet_hours_timezone": "Asia/Seoul",
        "minimum_match_score": 0.6,
        "priority_keywords": ["긴급", "중요"],
        "blocked_keywords": ["광고", "스팸"],
        "auto_subscribe_similar": False,
        "subscription_expiry_days": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


class TestNotificationPreferenceModel:
    """Test NotificationPreference model functionality"""
    
    def test_preference_model_creation(self):
        """Test creating a NotificationPreference model"""
        preference = NotificationPreference(
            user_id="user123",
            email_enabled=True,
            digest_frequency="weekly",
            priority_keywords=["AI", "스타트업"]
        )
        
        assert preference.user_id == "user123"
        assert preference.email_enabled is True
        assert preference.digest_frequency == "weekly"
        assert preference.priority_keywords == ["AI", "스타트업"]
        assert preference.max_daily_notifications == 10  # default value
    
    def test_preference_model_defaults(self):
        """Test that default values are properly set"""
        preference = NotificationPreference(user_id="user123")
        
        assert preference.email_enabled is True
        assert preference.web_enabled is True
        assert preference.push_enabled is False
        assert preference.sms_enabled is False
        assert preference.new_announcements is True
        assert preference.digest_frequency == "daily"
        assert preference.max_daily_notifications == 10
        assert preference.quiet_hours_enabled is False
        assert preference.minimum_match_score == 0.5
        
    def test_preference_validation(self):
        """Test preference model validation"""
        # Test valid quiet hours
        preference = NotificationPreference(
            user_id="user123",
            quiet_hours_start=22,
            quiet_hours_end=6
        )
        assert preference.quiet_hours_start == 22
        assert preference.quiet_hours_end == 6
        
        # Test valid match score
        preference = NotificationPreference(
            user_id="user123",
            minimum_match_score=0.8
        )
        assert preference.minimum_match_score == 0.8


class TestAlertsRepository:
    """Test AlertsRepository notification preference methods"""
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_exists(self, repository):
        """Test getting existing user preferences"""
        mock_preferences = {"user_id": "user123", "email_enabled": True}
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = mock_preferences
        
        result = await repository.get_user_preferences("user123")
        
        assert result == mock_preferences
        repository.preferences.find_one.assert_called_once_with({"user_id": "user123"})
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_not_exists(self, repository):
        """Test getting non-existent user preferences"""
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = None
        
        result = await repository.get_user_preferences("user123")
        
        assert result is None
        repository.preferences.find_one.assert_called_once_with({"user_id": "user123"})
    
    @pytest.mark.asyncio
    async def test_create_user_preferences(self, repository):
        """Test creating user preferences"""
        preference = NotificationPreference(user_id="user123", email_enabled=False)
        mock_result = Mock()
        mock_result.inserted_id = "pref123"
        
        repository.preferences = AsyncMock()
        repository.preferences.insert_one.return_value = mock_result
        
        result = await repository.create_user_preferences(preference)
        
        assert result == "pref123"
        repository.preferences.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, repository):
        """Test successful preference update"""
        mock_result = Mock()
        mock_result.matched_count = 1
        
        repository.preferences = AsyncMock()
        repository.preferences.update_one.return_value = mock_result
        
        result = await repository.update_user_preferences("user123", {"email_enabled": False})
        
        assert result is True
        repository.preferences.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_not_found(self, repository):
        """Test preference update when user not found"""
        mock_result = Mock()
        mock_result.matched_count = 0
        
        repository.preferences = AsyncMock()
        repository.preferences.update_one.return_value = mock_result
        
        result = await repository.update_user_preferences("user123", {"email_enabled": False})
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_notification_allowed_with_preferences(self, repository, sample_user_preferences):
        """Test notification permission check with existing preferences"""
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = sample_user_preferences
        
        # Test allowed notification
        is_allowed, prefs = await repository.is_notification_allowed("user123", "email", "new_announcements")
        assert is_allowed is True
        assert prefs == sample_user_preferences
        
        # Test blocked channel
        sample_user_preferences["email_enabled"] = False
        is_allowed, prefs = await repository.is_notification_allowed("user123", "email", "new_announcements")
        assert is_allowed is False
        
        # Test blocked category
        sample_user_preferences["email_enabled"] = True
        sample_user_preferences["marketing_notifications"] = False
        is_allowed, prefs = await repository.is_notification_allowed("user123", "email", "marketing_notifications")
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_is_notification_allowed_without_preferences(self, repository):
        """Test notification permission check without existing preferences"""
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = None
        
        # Mock get_default_preferences
        default_prefs = {"email_enabled": True, "new_announcements": True}
        with patch.object(repository, 'get_default_preferences', return_value=default_prefs):
            is_allowed, prefs = await repository.is_notification_allowed("user123", "email", "new_announcements")
            
        assert is_allowed is True
        assert prefs == default_prefs
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_enabled(self, repository, sample_user_preferences):
        """Test quiet hours check when enabled"""
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = sample_user_preferences
        
        with patch('app.domains.alerts.repository.datetime') as mock_datetime, \
             patch('app.domains.alerts.repository.pytz') as mock_pytz:
            
            # Mock current time as 23:00 (within quiet hours 22-07)
            mock_datetime.now.return_value.hour = 23
            mock_timezone = Mock()
            mock_pytz.timezone.return_value = mock_timezone
            mock_datetime.now.return_value = mock_datetime.now.return_value
            
            is_quiet, prefs = await repository.check_quiet_hours("user123")
            
            # Should be within quiet hours (22-07, current is 23)
            assert is_quiet is True
            assert prefs == sample_user_preferences
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_disabled(self, repository, sample_user_preferences):
        """Test quiet hours check when disabled"""
        sample_user_preferences["quiet_hours_enabled"] = False
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = sample_user_preferences
        
        is_quiet, prefs = await repository.check_quiet_hours("user123")
        
        assert is_quiet is False
        assert prefs == sample_user_preferences
    
    @pytest.mark.asyncio 
    async def test_check_daily_limit(self, repository, sample_user_preferences):
        """Test daily notification limit check"""
        repository.preferences = AsyncMock()
        repository.preferences.find_one.return_value = sample_user_preferences
        
        # Mock notification count
        repository.notifications = AsyncMock()
        repository.notifications.count_documents.return_value = 5
        
        allowed, current, max_daily = await repository.check_daily_limit("user123")
        
        assert allowed is True  # 5 < 10
        assert current == 5
        assert max_daily == 10
        
        # Test when limit is reached
        repository.notifications.count_documents.return_value = 10
        allowed, current, max_daily = await repository.check_daily_limit("user123")
        
        assert allowed is False  # 10 >= 10
        assert current == 10
        assert max_daily == 10


class TestNotificationFrequencyManager:
    """Test NotificationFrequencyManager functionality"""
    
    @pytest.mark.asyncio
    async def test_should_send_notification_allowed(self, frequency_manager):
        """Test notification should be sent when all conditions are met"""
        # Mock repository methods
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "new_announcements": True,
            "minimum_match_score": 0.5
        }
        frequency_manager.repository.check_quiet_hours.return_value = (False, {})
        frequency_manager.repository.check_daily_limit.return_value = (True, 5, 10)
        
        # Mock database count
        frequency_manager.db = {"notifications": AsyncMock()}
        frequency_manager.db["notifications"].count_documents.return_value = 0
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        
        assert should_send is True
        assert reason == "Allowed"
    
    @pytest.mark.asyncio
    async def test_should_send_notification_blocked_by_category(self, frequency_manager):
        """Test notification blocked by disabled category"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "new_announcements": False  # Category disabled
        }
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        
        assert should_send is False
        assert "Category new_announcements disabled" in reason
    
    @pytest.mark.asyncio
    async def test_should_send_notification_quiet_hours(self, frequency_manager):
        """Test notification blocked by quiet hours"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "new_announcements": True
        }
        frequency_manager.repository.check_quiet_hours.return_value = (True, {})
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        
        assert should_send is False
        assert reason == "Quiet hours active"
    
    @pytest.mark.asyncio
    async def test_should_send_notification_daily_limit(self, frequency_manager):
        """Test notification blocked by daily limit"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "new_announcements": True
        }
        frequency_manager.repository.check_quiet_hours.return_value = (False, {})
        frequency_manager.repository.check_daily_limit.return_value = (False, 10, 10)
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        
        assert should_send is False
        assert "Daily limit reached" in reason
    
    @pytest.mark.asyncio
    async def test_should_send_notification_duplicate(self, frequency_manager):
        """Test notification blocked by duplicate content"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "new_announcements": True
        }
        frequency_manager.repository.check_quiet_hours.return_value = (False, {})
        frequency_manager.repository.check_daily_limit.return_value = (True, 5, 10)
        
        # Mock duplicate notification found
        frequency_manager.db = {"notifications": AsyncMock()}
        frequency_manager.db["notifications"].count_documents.return_value = 1
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        
        assert should_send is False
        assert reason == "Duplicate notification"
    
    @pytest.mark.asyncio
    async def test_is_content_blocked_by_keywords(self, frequency_manager):
        """Test content blocking by keywords"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "blocked_keywords": ["광고", "스팸", "마케팅"]
        }
        
        # Test blocked content
        content_data = {
            "title": "새로운 광고 상품 출시",
            "description": "최신 마케팅 솔루션"
        }
        
        is_blocked, reason = await frequency_manager.is_content_blocked("user123", content_data)
        
        assert is_blocked is True
        assert "Blocked by keyword" in reason
        
        # Test allowed content
        content_data = {
            "title": "AI 스타트업 지원사업",
            "description": "인공지능 기술 창업 지원"
        }
        
        is_blocked, reason = await frequency_manager.is_content_blocked("user123", content_data)
        
        assert is_blocked is False
        assert reason == "Content allowed"
    
    @pytest.mark.asyncio
    async def test_calculate_notification_priority(self, frequency_manager):
        """Test notification priority calculation"""
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "priority_keywords": ["긴급", "중요", "AI"]
        }
        
        # Test urgent deadline reminder
        notification_data = {
            "type": "deadline_reminder",
            "days_left": 1,
            "match_score": 0.8,
            "content": {
                "title": "긴급 공고 마감 임박",
                "description": "중요한 사업 공고입니다"
            }
        }
        
        priority = await frequency_manager.calculate_notification_priority("user123", notification_data)
        
        # Should be high priority (urgent deadline + priority keywords + high match score)
        assert priority >= 4
        
        # Test low priority marketing
        notification_data = {
            "type": "marketing_notification",
            "match_score": 0.3,
            "content": {
                "title": "일반 상품 안내",
                "description": "새로운 서비스 소개"
            }
        }
        
        priority = await frequency_manager.calculate_notification_priority("user123", notification_data)
        
        # Should be low priority
        assert priority <= 3
    
    @pytest.mark.asyncio
    async def test_get_optimal_send_time_no_quiet_hours(self, frequency_manager):
        """Test optimal send time calculation without quiet hours"""
        base_time = datetime(2024, 1, 15, 14, 30, 0)
        
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "quiet_hours_enabled": False
        }
        
        optimal_time = await frequency_manager.get_optimal_send_time("user123", base_time)
        
        assert optimal_time == base_time  # Should return original time
    
    @pytest.mark.asyncio
    async def test_get_optimal_send_time_with_quiet_hours(self, frequency_manager):
        """Test optimal send time calculation with quiet hours"""
        # Test time during quiet hours (23:00)
        base_time = datetime(2024, 1, 15, 23, 0, 0)
        
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "quiet_hours_enabled": True,
            "quiet_hours_start": 22,
            "quiet_hours_end": 7,
            "quiet_hours_timezone": "Asia/Seoul"
        }
        
        with patch('app.domains.alerts.frequency_manager.pytz') as mock_pytz:
            mock_timezone = Mock()
            mock_pytz.timezone.return_value = mock_timezone
            mock_pytz.UTC = Mock()
            
            # Mock timezone conversion
            mock_local_time = Mock()
            mock_local_time.hour = 23
            mock_local_time.replace.return_value.astimezone.return_value.replace.return_value = datetime(2024, 1, 16, 7, 0, 0)
            
            base_time_with_tz = Mock()
            base_time_with_tz.replace.return_value.astimezone.return_value = mock_local_time
            
            with patch.object(base_time, 'replace', return_value=base_time_with_tz):
                optimal_time = await frequency_manager.get_optimal_send_time("user123", base_time)
                
                # Should be delayed to after quiet hours end
                assert isinstance(optimal_time, datetime)
    
    @pytest.mark.asyncio
    async def test_get_user_engagement_score(self, frequency_manager):
        """Test user engagement score calculation"""
        frequency_manager.db = {"notifications": AsyncMock()}
        frequency_manager.db["notifications"].count_documents.return_value = 20
        
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = {
            "email_enabled": True,
            "web_enabled": True,
            "push_enabled": False,
            "sms_enabled": False,
            "new_announcements": True,
            "deadline_reminders": True,
            "digest_notifications": True,
            "system_notifications": False
        }
        
        score = await frequency_manager.get_user_engagement_score("user123")
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be higher than default due to active settings


class TestNotificationPreferenceSchemas:
    """Test notification preference Pydantic schemas"""
    
    def test_notification_preference_update_schema(self):
        """Test NotificationPreferenceUpdate schema validation"""
        update_data = {
            "email_enabled": False,
            "quiet_hours_enabled": True,
            "quiet_hours_start": 23,
            "quiet_hours_end": 6,
            "max_daily_notifications": 5
        }
        
        update = NotificationPreferenceUpdate(**update_data)
        
        assert update.email_enabled is False
        assert update.quiet_hours_enabled is True
        assert update.quiet_hours_start == 23
        assert update.quiet_hours_end == 6
        assert update.max_daily_notifications == 5
        
        # Test partial update
        partial_update = NotificationPreferenceUpdate(email_enabled=False)
        assert partial_update.email_enabled is False
        assert partial_update.web_enabled is None  # Optional fields are None
    
    def test_notification_preference_response_schema(self, sample_user_preferences):
        """Test NotificationPreferenceResponse schema"""
        response = NotificationPreferenceResponse(**sample_user_preferences)
        
        assert response.user_id == "user123"
        assert response.email_enabled is True
        assert response.digest_frequency == "daily"
        assert response.priority_keywords == ["긴급", "중요"]
        assert response.blocked_keywords == ["광고", "스팸"]


class TestIntegrationScenarios:
    """Integration test scenarios for notification preferences"""
    
    @pytest.mark.asyncio
    async def test_complete_notification_filtering_workflow(self, frequency_manager):
        """Test complete notification filtering workflow"""
        # Setup user with specific preferences
        user_preferences = {
            "email_enabled": True,
            "new_announcements": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": 22,
            "quiet_hours_end": 7,
            "max_daily_notifications": 5,
            "blocked_keywords": ["광고"],
            "minimum_match_score": 0.7
        }
        
        frequency_manager.repository = AsyncMock()
        frequency_manager.repository.get_user_preferences.return_value = user_preferences
        frequency_manager.repository.check_quiet_hours.return_value = (False, user_preferences)
        frequency_manager.repository.check_daily_limit.return_value = (True, 3, 5)
        
        frequency_manager.db = {"notifications": AsyncMock()}
        frequency_manager.db["notifications"].count_documents.return_value = 0
        
        # Test allowed notification
        content_data = {
            "title": "AI 스타트업 지원사업",
            "description": "인공지능 기술 창업 지원 프로그램"
        }
        
        should_send, reason = await frequency_manager.should_send_notification(
            "user123", "new_announcements", "content123"
        )
        assert should_send is True
        
        is_blocked, block_reason = await frequency_manager.is_content_blocked("user123", content_data)
        assert is_blocked is False
        
        # Test blocked notification (contains blocked keyword)
        blocked_content = {
            "title": "새로운 광고 상품",
            "description": "마케팅 솔루션 안내"
        }
        
        is_blocked, block_reason = await frequency_manager.is_content_blocked("user123", blocked_content)
        assert is_blocked is True
        assert "광고" in block_reason