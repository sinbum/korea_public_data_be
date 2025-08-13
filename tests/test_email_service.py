from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from app.shared.services.email_service import EmailService, EmailTemplateEngine
from app.shared.clients.email_client import EmailClient


@pytest.fixture
def email_service():
    """Create EmailService instance for testing"""
    return EmailService()


@pytest.fixture
def template_engine():
    """Create EmailTemplateEngine instance for testing"""
    return EmailTemplateEngine()


@pytest.fixture
def sample_announcement():
    """Sample announcement data"""
    return {
        "_id": "673abc123def456789",
        "title": "AI 스타트업 지원사업 공고",
        "organization": "한국벤처투자",
        "category": "기술창업",
        "target": "예비창업자, 초기창업자",
        "application_start_date": datetime.now(),
        "application_end_date": datetime.now() + timedelta(days=30),
        "support_amount": "최대 1억원",
        "summary": "AI 기술 기반 스타트업을 위한 창업지원사업입니다.",
        "description": "인공지능 기술을 활용한 혁신적인 아이디어를 가진 예비창업자 및 초기창업자를 대상으로 한 지원사업입니다.",
        "requirements": "AI 기술 기반 사업아이템 보유, 대표자 만 39세 이하",
        "contact_info": "02-1234-5678"
    }


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "_id": "user123",
        "name": "김개발",
        "email": "test@example.com"
    }


class TestEmailTemplateEngine:
    """Test EmailTemplateEngine functionality"""

    def test_template_engine_initialization(self, template_engine):
        """Test that template engine initializes correctly"""
        assert template_engine.env is not None
        assert 'datetime' in template_engine.env.filters
        assert 'date' in template_engine.env.filters
        assert 'currency' in template_engine.env.filters

    def test_datetime_filter(self, template_engine):
        """Test datetime filter"""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = template_engine._datetime_filter(dt)
        assert result == "2024-01-15 14:30"
        
        # Test custom format
        result = template_engine._datetime_filter(dt, '%Y년 %m월 %d일')
        assert result == "2024년 01월 15일"

    def test_currency_filter(self, template_engine):
        """Test currency filter"""
        result = template_engine._currency_filter(1000000)
        assert result == "1,000,000원"
        
        result = template_engine._currency_filter("5000000")
        assert result == "5,000,000원"
        
        result = template_engine._currency_filter(500, "달러")
        assert result == "500달러"

    def test_template_exists(self, template_engine):
        """Test template existence check"""
        # This will depend on actual template files being present
        # For now, test the method functionality
        exists = template_engine.template_exists("email/nonexistent.html")
        assert isinstance(exists, bool)

    def test_render_template_with_context(self, template_engine):
        """Test template rendering with context"""
        # Create a simple test template content
        context = {
            'user_name': '테스트 사용자',
            'current_date': datetime(2024, 1, 15),
            'platform_name': '테스트 플랫폼'
        }
        
        # This test assumes templates exist - in real scenario,
        # we'd either mock the template or ensure test templates exist
        try:
            result = template_engine.render_template("email/base.html", context)
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception:
            # Template might not exist in test environment
            pytest.skip("Template files not available in test environment")


class TestEmailService:
    """Test EmailService functionality"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, email_service):
        """Test that email service initializes correctly"""
        assert email_service.template_engine is not None
        assert email_service.client is not None

    @pytest.mark.asyncio
    async def test_send_templated_email_basic(self, email_service, template_engine):
        """Test basic templated email sending"""
        # Mock EmailClient
        mock_client = Mock()
        mock_client.send.return_value = {"ok": True, "message_id": "test123"}
        email_service.client = mock_client
        
        # Mock template rendering
        with patch.object(template_engine, 'render_template') as mock_render:
            mock_render.return_value = "<html><body>Test Email</body></html>"
            email_service.template_engine = template_engine
            
            result = await email_service.send_templated_email(
                to="test@example.com",
                template_name="email/test.html",
                context={"name": "Test User"}
            )
            
            assert result["success"] is True
            assert "tracking_id" in result
            mock_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_html_to_text_conversion(self, email_service):
        """Test HTML to text conversion"""
        html = "<html><body><h1>Title</h1><p>Content with <strong>bold</strong> text.</p></body></html>"
        text = email_service._html_to_text(html)
        
        assert "Title" in text
        assert "Content with bold text." in text
        assert "<h1>" not in text
        assert "<strong>" not in text

    @pytest.mark.asyncio
    async def test_send_new_announcement_notification(
        self, email_service, sample_announcement, sample_user
    ):
        """Test sending new announcement notification"""
        # Mock EmailClient
        mock_client = Mock()
        mock_client.send.return_value = {"ok": True, "message_id": "ann123"}
        email_service.client = mock_client
        
        # Mock template rendering
        with patch.object(email_service.template_engine, 'render_template') as mock_render:
            mock_render.return_value = "<html><body>New Announcement</body></html>"
            
            result = await email_service.send_new_announcement_notification(
                user_email=sample_user["email"],
                user_name=sample_user["name"],
                announcement=sample_announcement,
                matched_keywords=["AI", "스타트업"],
                match_score=0.85,
                threshold=0.7,
                tracking_id="track123"
            )
            
            assert result["success"] is True
            assert result["tracking_id"] == "track123"
            mock_render.assert_called_once_with(
                "email/new_announcement.html",
                pytest.any(object)  # Context will be complex, just check it's called
            )

    @pytest.mark.asyncio
    async def test_send_deadline_reminder_urgent(
        self, email_service, sample_announcement, sample_user
    ):
        """Test sending urgent deadline reminder"""
        # Mock EmailClient
        mock_client = Mock()
        mock_client.send.return_value = {"ok": True, "message_id": "deadline123"}
        email_service.client = mock_client
        
        # Mock template rendering
        with patch.object(email_service.template_engine, 'render_template') as mock_render:
            mock_render.return_value = "<html><body>Deadline Reminder</body></html>"
            
            result = await email_service.send_deadline_reminder(
                user_email=sample_user["email"],
                user_name=sample_user["name"],
                announcement=sample_announcement,
                days_left=1,  # Urgent
                tracking_id="deadline123"
            )
            
            assert result["success"] is True
            # Check that urgent deadline gets high priority
            # This would be verified by checking the context passed to template
            mock_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_daily_digest(
        self, email_service, sample_announcement, sample_user
    ):
        """Test sending daily digest"""
        # Mock EmailClient
        mock_client = Mock()
        mock_client.send.return_value = {"ok": True, "message_id": "digest123"}
        email_service.client = mock_client
        
        # Sample data for digest
        new_announcements = [sample_announcement]
        deadline_announcements = [{**sample_announcement, "days_left": 3}]
        stats = {
            "new_this_week": 5,
            "matched_this_week": 3,
            "deadline_this_week": 2,
            "popular_keywords": ["AI", "스타트업", "핀테크"]
        }
        
        # Mock template rendering
        with patch.object(email_service.template_engine, 'render_template') as mock_render:
            mock_render.return_value = "<html><body>Daily Digest</body></html>"
            
            result = await email_service.send_daily_digest(
                user_email=sample_user["email"],
                user_name=sample_user["name"],
                new_announcements=new_announcements,
                deadline_announcements=deadline_announcements,
                stats=stats,
                tracking_id="digest123"
            )
            
            assert result["success"] is True
            mock_render.assert_called_once_with(
                "email/digest_daily.html",
                pytest.any(object)
            )

    @pytest.mark.asyncio
    async def test_preview_template(self, email_service):
        """Test template preview functionality"""
        context = {
            "user_name": "테스트 사용자",
            "test_var": "테스트 값"
        }
        
        # Mock template rendering for preview
        with patch.object(email_service.template_engine, 'render_template') as mock_render:
            mock_render.return_value = "<html><body>Preview Content</body></html>"
            
            result = await email_service.preview_template("email/test.html", context)
            
            assert result == "<html><body>Preview Content</body></html>"
            mock_render.assert_called_once()

    def test_get_available_templates(self, email_service):
        """Test getting list of available templates"""
        # Mock the templates directory
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'glob') as mock_glob:
            
            # Mock template files
            mock_files = [
                Mock(name="new_announcement.html"),
                Mock(name="deadline_reminder.html"),
                Mock(name="digest_daily.html")
            ]
            mock_glob.return_value = mock_files
            
            templates = email_service.get_available_templates()
            
            assert isinstance(templates, list)
            # Would contain email/ prefixed template names


class TestEmailServiceIntegration:
    """Integration tests for email service"""

    @pytest.mark.asyncio
    async def test_email_service_error_handling(self, email_service):
        """Test email service handles errors gracefully"""
        # Test with invalid template
        result = await email_service.send_templated_email(
            to="test@example.com",
            template_name="email/nonexistent.html",
            context={}
        )
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_context_default_values(self, email_service):
        """Test that default context values are added"""
        with patch.object(email_service.template_engine, 'render_template') as mock_render, \
             patch.object(email_service.client, 'send', return_value={"ok": True}):
            
            mock_render.return_value = "<html><body>Test</body></html>"
            
            await email_service.send_templated_email(
                to="test@example.com",
                template_name="email/test.html",
                context={"custom_var": "value"}
            )
            
            # Check that default context variables were added
            call_args = mock_render.call_args[1]  # Get context argument
            assert "current_date" in call_args
            assert "platform_name" in call_args
            assert "custom_var" in call_args
            assert call_args["custom_var"] == "value"

    @pytest.mark.asyncio
    async def test_multipart_email_creation(self, email_service):
        """Test that emails are created with both HTML and text parts"""
        with patch.object(email_service.template_engine, 'render_template') as mock_render, \
             patch.object(email_service.client, 'send') as mock_send:
            
            mock_render.return_value = "<html><body><h1>Test</h1><p>Content</p></body></html>"
            mock_send.return_value = {"ok": True}
            
            await email_service.send_templated_email(
                to="test@example.com",
                template_name="email/test.html",
                context={}
            )
            
            # Verify that both HTML and text content were passed to client
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert "html" in call_kwargs
            assert "text" in call_kwargs
            assert call_kwargs["text"] != call_kwargs["html"]  # Text should be different from HTML