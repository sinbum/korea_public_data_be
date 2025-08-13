from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal, Union

from pydantic import BaseModel, Field

from ...shared.models.base import BaseDocument, PyObjectId


class AlertFilters(BaseModel):
    domain: Optional[Literal["announcements", "contents", "statistics"]] = None
    categories: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None


class AlertSubscription(BaseDocument):
    user_id: Union[PyObjectId, str] = Field(..., description="구독자 ID")
    keywords: List[str] = Field(default_factory=list, min_items=1, description="키워드 목록")
    filters: AlertFilters = Field(default_factory=AlertFilters, description="부가 필터")
    channels: List[Literal["email", "web", "push"]] = Field(default_factory=lambda: ["email"]) 
    frequency: Literal["realtime", "daily", "weekly"] = Field(default="realtime")
    is_active: bool = Field(default=True)
    match_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="매칭 점수 임계값 (0.0-1.0)")


class Notification(BaseDocument):
    subscription_id: Union[PyObjectId, str] = Field(...)
    user_id: Union[PyObjectId, str] = Field(...)
    domain: Literal["announcements", "contents", "statistics"]
    content_id: Union[PyObjectId, str] = Field(...)
    channel: Literal["email", "web", "push"] = Field(default="email")
    status: Literal["queued", "sent", "failed", "skipped"] = Field(default="queued")
    sent_at: Optional[datetime] = None
    score: Optional[float] = None


class NotificationPreference(BaseDocument):
    """사용자별 알림 설정 관리 모델"""
    user_id: Union[PyObjectId, str] = Field(..., description="사용자 ID")
    
    # 채널별 활성화 설정
    email_enabled: bool = Field(default=True, description="이메일 알림 활성화")
    web_enabled: bool = Field(default=True, description="웹 알림 활성화")  
    push_enabled: bool = Field(default=False, description="푸시 알림 활성화")
    sms_enabled: bool = Field(default=False, description="SMS 알림 활성화")
    
    # 알림 카테고리별 설정
    new_announcements: bool = Field(default=True, description="새 공고 알림")
    deadline_reminders: bool = Field(default=True, description="마감 임박 알림")
    digest_notifications: bool = Field(default=True, description="다이제스트 알림")
    system_notifications: bool = Field(default=True, description="시스템 알림")
    marketing_notifications: bool = Field(default=False, description="마케팅 알림")
    
    # 알림 빈도 설정
    digest_frequency: Literal["daily", "weekly", "monthly", "off"] = Field(default="daily", description="다이제스트 발송 빈도")
    deadline_reminder_days: List[int] = Field(default_factory=lambda: [7, 3, 1], description="마감 알림 발송 일정 (D-day)")
    max_daily_notifications: int = Field(default=10, ge=1, le=100, description="일일 최대 알림 수")
    
    # 시간대 차단 설정 (24시간 형식)
    quiet_hours_enabled: bool = Field(default=False, description="방해금지 시간 활성화")
    quiet_hours_start: int = Field(default=22, ge=0, le=23, description="방해금지 시작 시간")
    quiet_hours_end: int = Field(default=7, ge=0, le=23, description="방해금지 종료 시간")
    quiet_hours_timezone: str = Field(default="Asia/Seoul", description="시간대")
    
    # 고급 설정
    minimum_match_score: float = Field(default=0.5, ge=0.0, le=1.0, description="최소 매칭 점수")
    priority_keywords: List[str] = Field(default_factory=list, description="우선순위 키워드")
    blocked_keywords: List[str] = Field(default_factory=list, description="차단 키워드")
    
    # 구독 설정
    auto_subscribe_similar: bool = Field(default=False, description="유사 공고 자동 구독")
    subscription_expiry_days: Optional[int] = Field(default=None, ge=1, le=365, description="구독 만료 일수")


class DeliveryLog(BaseDocument):
    notification_id: Union[PyObjectId, str]
    attempt: int = Field(default=1)
    provider_response: Optional[dict] = None
    error: Optional[str] = None
    next_retry_at: Optional[datetime] = None

