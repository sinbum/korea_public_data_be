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


class NotificationHistoryQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    channel: Optional[str] = None
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

