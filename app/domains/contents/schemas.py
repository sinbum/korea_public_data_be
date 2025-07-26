"""
Content domain Pydantic schemas for API requests and responses.

Provides standardized data models for content-related operations
with proper validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class ContentResponse(BaseModel):
    """Response schema for content data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )
    
    id: str = Field(..., description="콘텐츠 고유 ID")
    content_data: Dict[str, Any] = Field(..., description="콘텐츠 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")


class ContentCreate(BaseModel):
    """Schema for creating new contents."""
    
    content_data: Dict[str, Any] = Field(..., description="콘텐츠 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")


class ContentUpdate(BaseModel):
    """Schema for updating existing contents."""
    
    content_data: Optional[Dict[str, Any]] = Field(None, description="콘텐츠 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: Optional[bool] = Field(None, description="활성 상태")


class ContentSummary(BaseModel):
    """Summary schema for content listings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="콘텐츠 고유 ID")
    title: Optional[str] = Field(None, description="콘텐츠 제목")
    content_type: Optional[str] = Field(None, description="콘텐츠 유형")
    category: Optional[str] = Field(None, description="카테고리")
    tags: Optional[List[str]] = Field(None, description="태그 목록")
    view_count: Optional[int] = Field(None, description="조회수")
    like_count: Optional[int] = Field(None, description="좋아요 수")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")


class ContentStats(BaseModel):
    """Statistics schema for contents."""
    
    total_count: int = Field(..., description="전체 콘텐츠 수")
    active_count: int = Field(..., description="활성 콘텐츠 수")
    by_type: Dict[str, int] = Field(..., description="타입별 콘텐츠 수")
    by_category: Dict[str, int] = Field(..., description="카테고리별 콘텐츠 수")
    total_views: int = Field(..., description="총 조회수")
    total_likes: int = Field(..., description="총 좋아요 수")
    recent_count: int = Field(..., description="최근 30일 콘텐츠 수")


class ContentSearch(BaseModel):
    """Search parameters for contents."""
    
    keyword: Optional[str] = Field(None, description="검색 키워드")
    content_type: Optional[str] = Field(None, description="콘텐츠 유형 필터")
    category: Optional[str] = Field(None, description="카테고리 필터")
    tags: Optional[List[str]] = Field(None, description="태그 필터")
    min_view_count: Optional[int] = Field(None, description="최소 조회수")
    min_like_count: Optional[int] = Field(None, description="최소 좋아요 수")
    is_active: Optional[bool] = Field(None, description="활성 상태 필터")
    date_from: Optional[datetime] = Field(None, description="조회 시작 날짜")
    date_to: Optional[datetime] = Field(None, description="조회 종료 날짜")


class ContentLike(BaseModel):
    """Schema for content like action."""
    
    content_id: str = Field(..., description="좋아요할 콘텐츠 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID (선택적)")