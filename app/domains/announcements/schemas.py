"""
Announcement domain Pydantic schemas for API requests and responses.

Provides standardized data models for announcement-related operations
with proper validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .models import AnnouncementData


class AnnouncementResponse(BaseModel):
    """Response schema for announcement data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )
    
    id: str = Field(..., description="공고 고유 ID")
    announcement_data: Dict[str, Any] = Field(..., description="공고 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: str = Field(..., description="생성 일시")
    updated_at: str = Field(..., description="수정 일시")


class AnnouncementCreate(BaseModel):
    """Schema for creating new announcements."""
    
    announcement_data: AnnouncementData = Field(..., description="공고 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")


class AnnouncementUpdate(BaseModel):
    """Schema for updating existing announcements."""
    
    announcement_data: Optional[AnnouncementData] = Field(None, description="공고 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: Optional[bool] = Field(None, description="활성 상태")


class AnnouncementSummary(BaseModel):
    """Summary schema for announcement listings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="공고 고유 ID")
    business_name: Optional[str] = Field(None, description="사업명")
    business_type: Optional[str] = Field(None, description="사업 유형")
    status: Optional[str] = Field(None, description="상태")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")


class AnnouncementStats(BaseModel):
    """Statistics schema for announcements."""
    
    total_count: int = Field(..., description="전체 공고 수")
    active_count: int = Field(..., description="활성 공고 수")
    by_type: Dict[str, int] = Field(..., description="타입별 공고 수")
    by_status: Dict[str, int] = Field(..., description="상태별 공고 수")
    recent_count: int = Field(..., description="최근 30일 공고 수")


class AnnouncementSearch(BaseModel):
    """Search parameters for announcements."""
    
    keyword: Optional[str] = Field(None, description="검색 키워드")
    business_type: Optional[str] = Field(None, description="사업 유형 필터")
    status: Optional[str] = Field(None, description="상태 필터")
    is_active: Optional[bool] = Field(None, description="활성 상태 필터")
    date_from: Optional[datetime] = Field(None, description="조회 시작 날짜")
    date_to: Optional[datetime] = Field(None, description="조회 종료 날짜")