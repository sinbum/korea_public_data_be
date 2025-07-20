from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ...shared.models import BaseDocument


class ContentData(BaseModel):
    """콘텐츠 개별 데이터 모델"""
    content_id: Optional[str] = Field(None, description="콘텐츠 ID")
    title: Optional[str] = Field(None, description="제목")
    content_type: Optional[str] = Field(None, description="콘텐츠 유형")
    category: Optional[str] = Field(None, description="카테고리")
    description: Optional[str] = Field(None, description="설명")
    content_url: Optional[str] = Field(None, description="콘텐츠 URL")
    thumbnail_url: Optional[str] = Field(None, description="썸네일 URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="태그")
    view_count: Optional[int] = Field(0, description="조회수")
    like_count: Optional[int] = Field(0, description="좋아요 수")
    published_date: Optional[datetime] = Field(None, description="발행일")


class Content(BaseDocument):
    """콘텐츠 MongoDB 문서 모델"""
    content_data: ContentData
    source_url: Optional[str] = Field(None, description="원본 URL")
    is_active: bool = Field(True, description="활성 상태")
    
    class Config:
        collection = "contents"


class ContentCreate(BaseModel):
    """콘텐츠 생성 요청 모델"""
    content_data: ContentData
    source_url: Optional[str] = None


class ContentUpdate(BaseModel):
    """콘텐츠 수정 요청 모델"""
    content_data: Optional[ContentData] = None
    source_url: Optional[str] = None
    is_active: Optional[bool] = None


class ContentResponse(BaseModel):
    """콘텐츠 응답 모델"""
    id: str
    content_data: ContentData
    source_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime