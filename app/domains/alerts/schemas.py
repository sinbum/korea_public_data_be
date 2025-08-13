from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal, Union

from pydantic import BaseModel, Field

from .models import AlertFilters
from ...shared.models.base import PyObjectId


class SubscriptionCreateRequest(BaseModel):
    keywords: List[str] = Field(min_length=1)
    filters: Optional[AlertFilters] = None
    channels: Optional[List[Literal["email", "web", "push"]]] = None
    frequency: Optional[Literal["realtime", "daily", "weekly"]] = None


class SubscriptionResponse(BaseModel):
    id: Union[PyObjectId, str] = Field(alias="_id")
    user_id: Union[PyObjectId, str]
    keywords: List[str]
    filters: AlertFilters
    channels: List[str]
    frequency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class NotificationPreviewRequest(BaseModel):
    keywords: List[str]
    filters: Optional[AlertFilters] = None
    limit: int = Field(default=10, ge=1, le=50)


# 알림 설정 관련 스키마
class NotificationPreferenceUpdate(BaseModel):
    """알림 설정 업데이트 요청"""
    # 채널별 설정
    email_enabled: Optional[bool] = None
    web_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    
    # 카테고리별 설정
    new_announcements: Optional[bool] = None
    deadline_reminders: Optional[bool] = None
    digest_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    marketing_notifications: Optional[bool] = None
    
    # 빈도 설정
    digest_frequency: Optional[Literal["daily", "weekly", "monthly", "off"]] = None
    deadline_reminder_days: Optional[List[int]] = Field(default=None, description="D-day 알림 일정")
    max_daily_notifications: Optional[int] = Field(default=None, ge=1, le=100)
    
    # 방해금지 시간
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = Field(default=None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(default=None, ge=0, le=23)
    quiet_hours_timezone: Optional[str] = None
    
    # 고급 설정
    minimum_match_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    priority_keywords: Optional[List[str]] = None
    blocked_keywords: Optional[List[str]] = None
    auto_subscribe_similar: Optional[bool] = None
    subscription_expiry_days: Optional[int] = Field(default=None, ge=1, le=365)


class NotificationPreferenceResponse(BaseModel):
    """알림 설정 응답"""
    id: Union[PyObjectId, str] = Field(alias="_id")
    user_id: Union[PyObjectId, str]
    
    # 채널별 설정
    email_enabled: bool
    web_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    
    # 카테고리별 설정
    new_announcements: bool
    deadline_reminders: bool
    digest_notifications: bool
    system_notifications: bool
    marketing_notifications: bool
    
    # 빈도 설정
    digest_frequency: str
    deadline_reminder_days: List[int]
    max_daily_notifications: int
    
    # 방해금지 시간
    quiet_hours_enabled: bool
    quiet_hours_start: int
    quiet_hours_end: int
    quiet_hours_timezone: str
    
    # 고급 설정
    minimum_match_score: float
    priority_keywords: List[str]
    blocked_keywords: List[str]
    auto_subscribe_similar: bool
    subscription_expiry_days: Optional[int]
    
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class NotificationPreferencePreview(BaseModel):
    """알림 설정 미리보기"""
    estimated_daily_notifications: int = Field(description="예상 일일 알림 수")
    estimated_weekly_notifications: int = Field(description="예상 주간 알림 수")
    active_channels: List[str] = Field(description="활성화된 채널 목록")
    active_categories: List[str] = Field(description="활성화된 카테고리 목록")
    quiet_hours_summary: str = Field(description="방해금지 시간 요약")
    digest_schedule: str = Field(description="다이제스트 발송 일정")


class NotificationHistoryQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    channel: Optional[str] = None
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

