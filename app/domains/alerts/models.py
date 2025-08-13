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


class DeliveryLog(BaseDocument):
    notification_id: Union[PyObjectId, str]
    attempt: int = Field(default=1)
    provider_response: Optional[dict] = None
    error: Optional[str] = None
    next_retry_at: Optional[datetime] = None

