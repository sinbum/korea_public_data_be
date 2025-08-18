from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..interfaces.base_service import BaseService
from ..clients.email_client import EmailClient
from ...core.config import settings

logger = logging.getLogger(__name__)


class EmailTemplateEngine:
    """Jinja2 기반 이메일 템플릿 엔진"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize the template engine.
        
        Args:
            templates_dir: Path to templates directory relative to project root
        """
        # Get project root and create templates path
        project_root = Path(__file__).parent.parent.parent.parent
        self.templates_path = project_root / templates_dir
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_path)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Add custom filters
        self.env.filters['datetime'] = self._datetime_filter
        self.env.filters['date'] = self._date_filter
        self.env.filters['currency'] = self._currency_filter
        
        logger.info(f"Email template engine initialized with path: {self.templates_path}")

    def _datetime_filter(self, value: datetime, format: str = '%Y-%m-%d %H:%M') -> str:
        """Custom datetime filter for templates"""
        if not isinstance(value, datetime):
            return str(value)
        return value.strftime(format)

    def _date_filter(self, value: datetime, format: str = '%Y-%m-%d') -> str:
        """Custom date filter for templates"""
        if not isinstance(value, datetime):
            return str(value)
        return value.strftime(format)

    def _currency_filter(self, value: Union[int, float, str], currency: str = '원') -> str:
        """Custom currency filter for templates"""
        try:
            # Convert to integer for Korean won
            amount = int(float(str(value).replace(',', '')))
            # Format with commas
            formatted = f"{amount:,}{currency}"
            return formatted
        except (ValueError, TypeError):
            return str(value)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with given context.
        
        Args:
            template_name: Template file name (e.g., 'email/new_announcement.html')
            context: Template context variables
            
        Returns:
            Rendered template content
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

    def template_exists(self, template_name: str) -> bool:
        """Check if template exists"""
        try:
            self.env.get_template(template_name)
            return True
        except:
            return False


class EmailService(BaseService):
    """Enhanced email service with template support and comprehensive features"""
    
    def __init__(self):
        super().__init__()
        self.template_engine = EmailTemplateEngine()
        self.client = EmailClient(provider="dev")  # Can be configured
        
    async def send_templated_email(
        self,
        to: str,
        template_name: str,
        context: Dict[str, Any],
        subject: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        priority: str = "normal",
        tracking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send templated email with enhanced features.
        
        Args:
            to: Recipient email address
            template_name: Template file name
            context: Template context data
            subject: Email subject (if not provided, will look for subject in context)
            from_email: Sender email
            reply_to: Reply-to email
            attachments: List of file paths to attach
            priority: Email priority (low, normal, high)
            tracking_id: Optional tracking ID for analytics
            
        Returns:
            Dictionary with send result
        """
        try:
            # Add default context variables
            default_context = {
                'current_date': datetime.now(),
                'year': datetime.now().year,
                'platform_name': '한국 공공데이터 플랫폼',
                'support_email': 'support@example.com',
                'unsubscribe_url': f"{settings.frontend_url}/unsubscribe",
                'settings_url': f"{settings.frontend_url}/settings/notifications",
                'support_url': f"{settings.frontend_url}/support"
            }
            
            # Merge with provided context
            full_context = {**default_context, **context}
            
            # Render email content
            html_content = self.template_engine.render_template(template_name, full_context)
            
            # Generate text version from HTML (simple fallback)
            text_content = self._html_to_text(html_content)
            
            # Determine subject
            email_subject = subject or full_context.get('subject', '한국 공공데이터 알림')
            
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_subject
            msg['From'] = from_email or f"한국 공공데이터 플랫폼 <{settings.smtp_from_email if hasattr(settings, 'smtp_from_email') else 'noreply@example.com'}>"
            msg['To'] = to
            
            if reply_to:
                msg['Reply-To'] = reply_to
                
            # Set priority
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == "low":
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'
            
            # Add tracking headers if provided
            if tracking_id:
                msg['X-Tracking-ID'] = tracking_id
                
            # Attach text and HTML parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Use existing EmailClient to send
            result = self.client.send(
                to=to,
                subject=email_subject,
                html=html_content,
                text=text_content,
                meta={
                    'template': template_name,
                    'tracking_id': tracking_id,
                    'priority': priority,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Templated email sent to {to} using template {template_name}")
            
            return {
                'success': result.get('ok', False),
                'message_id': result.get('message_id'),
                'template': template_name,
                'tracking_id': tracking_id,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending templated email to {to}: {e}")
            return {
                'success': False,
                'error': str(e),
                'template': template_name,
                'tracking_id': tracking_id
            }

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simple implementation)"""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Replace common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        
        return text.strip()

    async def send_new_announcement_notification(
        self,
        user_email: str,
        user_name: str,
        announcement: Dict[str, Any],
        matched_keywords: List[str],
        match_score: float,
        threshold: float,
        tracking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send new announcement notification"""
        
        context = {
            'user_name': user_name,
            'announcement': announcement,
            'matched_keywords': matched_keywords,
            'match_score': match_score,
            'threshold': threshold,
            'announcement_url': f"{settings.frontend_url}/announcements/{announcement.get('id')}",
            'notification_settings_url': f"{settings.frontend_url}/settings/notifications",
            'subject': f"🚀 새로운 공고 알림: {announcement.get('title', '')[:50]}..."
        }
        
        return await self.send_templated_email(
            to=user_email,
            template_name="email/new_announcement.html",
            context=context,
            priority="normal",
            tracking_id=tracking_id
        )

    async def send_deadline_reminder(
        self,
        user_email: str,
        user_name: str,
        announcement: Dict[str, Any],
        days_left: int,
        tracking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send deadline reminder notification"""
        
        # Determine urgency text
        if days_left <= 1:
            urgency_text = "임박"
            priority = "high"
        elif days_left <= 3:
            urgency_text = "임박"
            priority = "high"
        else:
            urgency_text = f"{days_left}일 전"
            priority = "normal"
        
        context = {
            'user_name': user_name,
            'announcement': announcement,
            'days_left': days_left,
            'urgency_text': urgency_text,
            'announcement_url': f"{settings.frontend_url}/announcements/{announcement.get('id')}",
            'notification_settings_url': f"{settings.frontend_url}/settings/notifications",
            'subject': f"⏰ 마감 {urgency_text} 알림 (D-{days_left}): {announcement.get('title', '')[:40]}..."
        }
        
        return await self.send_templated_email(
            to=user_email,
            template_name="email/deadline_reminder.html",
            context=context,
            priority=priority,
            tracking_id=tracking_id
        )

    async def send_daily_digest(
        self,
        user_email: str,
        user_name: str,
        new_announcements: List[Dict[str, Any]],
        deadline_announcements: List[Dict[str, Any]],
        stats: Dict[str, Any],
        digest_time: str = "오전 9시",
        tracking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send daily digest notification"""
        
        context = {
            'user_name': user_name,
            'date': datetime.now(),
            'new_announcements': new_announcements,
            'deadline_announcements': deadline_announcements,
            'stats': stats,
            'digest_time': digest_time,
            'dashboard_url': f"{settings.frontend_url}/dashboard",
            'browse_url': f"{settings.frontend_url}/announcements",
            'notification_settings_url': f"{settings.frontend_url}/settings/notifications",
            'subject': f"📰 일간 다이제스트 ({len(new_announcements)}건 신규, {len(deadline_announcements)}건 마감임박)"
        }
        
        return await self.send_templated_email(
            to=user_email,
            template_name="email/digest_daily.html",
            context=context,
            priority="low",
            tracking_id=tracking_id
        )

    async def preview_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Preview template rendering for testing purposes"""
        
        try:
            # Add default context
            default_context = {
                'current_date': datetime.now(),
                'year': datetime.now().year,
                'platform_name': '한국 공공데이터 플랫폼'
            }
            
            full_context = {**default_context, **context}
            return self.template_engine.render_template(template_name, full_context)
            
        except Exception as e:
            logger.error(f"Error previewing template {template_name}: {e}")
            raise

    def get_available_templates(self) -> List[str]:
        """Get list of available email templates"""
        templates = []
        email_dir = self.template_engine.templates_path / "email"
        
        if email_dir.exists():
            for template_file in email_dir.glob("*.html"):
                if template_file.name != "base.html":  # Skip base template
                    templates.append(f"email/{template_file.name}")
        
        return templates