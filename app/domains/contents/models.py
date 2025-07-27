from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...shared.models.base import BaseDocument


class ContentData(BaseModel):
    """콘텐츠 개별 데이터 모델 (확장된 필드)"""
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
    
    # 추가된 필드들
    content_summary: Optional[str] = Field(None, description="콘텐츠 요약")
    content_body: Optional[str] = Field(None, description="콘텐츠 본문")
    file_name: Optional[str] = Field(None, description="파일명")
    author: Optional[str] = Field(None, description="작성자")
    update_date: Optional[datetime] = Field(None, description="수정일시")
    publish_status: Optional[str] = Field(None, description="공개상태")


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
    content_data: Dict[str, Any]
    source_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat() if dt else None