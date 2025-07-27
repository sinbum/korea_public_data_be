"""
Announcement domain Pydantic schemas for API requests and responses.

Provides standardized data models for announcement-related operations
with proper validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import AnnouncementData


class AnnouncementResponse(BaseModel):
    """Response schema for announcement data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        },
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6789abcdef",
                "announcement_data": {
                    "announcement_id": "174329",
                    "title": "2025년 민간주도 스타트업 스케일업 실증지원사업 수혜기업 모집 공고",
                    "content": "창업벤처기업의 혁신적인 제품·서비스를 공공서비스 현장에 설치하고 테스트 할 수 있는 기회를 제공...",
                    "start_date": "2025-07-14",
                    "end_date": "2025-08-18",
                    "business_category": "기술개발(R&D)",
                    "support_region": "전북",
                    "organization": "(재)전북테크노파크 원장",
                    "recruitment_progress": "Y"
                },
                "source_url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174329",
                "is_active": True,
                "created_at": "2025-07-27T00:00:00Z",
                "updated_at": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    id: str = Field(
        ..., 
        description="공고 고유 ID (MongoDB ObjectId 문자열)",
        example="674a1b2c3d4e5f6789abcdef"
    )
    announcement_data: Dict[str, Any] = Field(
        ..., 
        description="공고 상세 데이터 (K-Startup API 응답 형태)",
        example={
            "announcement_id": "174329",
            "title": "2025년 민간주도 스타트업 스케일업 실증지원사업 수혜기업 모집 공고",
            "business_category": "기술개발(R&D)",
            "support_region": "전북",
            "recruitment_progress": "Y"
        }
    )
    source_url: Optional[str] = Field(
        None, 
        description="원본 데이터 URL (K-Startup 공고 페이지)",
        example="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174329"
    )
    is_active: bool = Field(
        True, 
        description="활성 상태 (삭제되지 않은 공고인지 여부)",
        example=True
    )
    created_at: str = Field(
        ..., 
        description="생성 일시 (ISO 8601 형식)",
        example="2025-07-27T00:00:00Z"
    )
    updated_at: str = Field(
        ..., 
        description="수정 일시 (ISO 8601 형식)",
        example="2025-07-27T00:00:00Z"
    )


class AnnouncementCreate(BaseModel):
    """Schema for creating new announcements."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "announcement_id": "174330",
                    "title": "새로운 창업지원 사업 공고",
                    "content": "창업지원을 위한 새로운 사업 공고입니다.",
                    "start_date": "2025-08-01",
                    "end_date": "2025-09-01",
                    "business_category": "창업교육",
                    "support_region": "전국",
                    "organization": "중소벤처기업부",
                    "recruitment_progress": "Y"
                },
                "source_url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174330",
                "is_active": True
            }
        }
    )
    
    announcement_data: AnnouncementData = Field(
        ..., 
        description="공고 상세 데이터 (K-Startup API 형태)",
        example={
            "announcement_id": "174330",
            "title": "새로운 창업지원 사업 공고",
            "business_category": "창업교육",
            "support_region": "전국"
        }
    )
    source_url: Optional[str] = Field(
        None, 
        description="원본 데이터 URL",
        example="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=174330"
    )
    is_active: bool = Field(
        True, 
        description="활성 상태 (기본값: True)",
        example=True
    )


class AnnouncementUpdate(BaseModel):
    """Schema for updating existing announcements."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "title": "수정된 공고 제목",
                    "content": "수정된 공고 내용",
                    "recruitment_progress": "N"
                },
                "is_active": False
            }
        }
    )
    
    announcement_data: Optional[AnnouncementData] = Field(
        None, 
        description="수정할 공고 상세 데이터 (부분 업데이트 가능)",
        example={
            "title": "수정된 공고 제목",
            "recruitment_progress": "N"
        }
    )
    source_url: Optional[str] = Field(
        None, 
        description="수정할 원본 데이터 URL",
        example="https://www.k-startup.go.kr/updated-url"
    )
    is_active: Optional[bool] = Field(
        None, 
        description="수정할 활성 상태",
        example=False
    )


class AnnouncementSummary(BaseModel):
    """Summary schema for announcement listings."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6789abcdef",
                "business_name": "민간주도 스타트업 스케일업 실증지원",
                "business_type": "기술개발(R&D)",
                "status": "진행중",
                "is_active": True,
                "created_at": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    id: str = Field(
        ..., 
        description="공고 고유 ID",
        example="674a1b2c3d4e5f6789abcdef"
    )
    business_name: Optional[str] = Field(
        None, 
        description="사업명",
        example="민간주도 스타트업 스케일업 실증지원"
    )
    business_type: Optional[str] = Field(
        None, 
        description="사업 유형",
        example="기술개발(R&D)"
    )
    status: Optional[str] = Field(
        None, 
        description="모집 상태",
        example="진행중"
    )
    is_active: bool = Field(
        True, 
        description="활성 상태",
        example=True
    )
    created_at: datetime = Field(
        ..., 
        description="생성 일시",
        example="2025-07-27T00:00:00Z"
    )


class AnnouncementStats(BaseModel):
    """Statistics schema for announcements."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_count": 1250,
                "active_count": 1180,
                "by_type": {
                    "기술개발(R&D)": 350,
                    "창업교육": 280,
                    "멘토링·컨설팅·교육": 220,
                    "사업화": 180,
                    "시설·공간·보육": 150,
                    "기타": 70
                },
                "by_status": {
                    "진행중": 450,
                    "마감": 600,
                    "예정": 130,
                    "취소": 70
                },
                "recent_count": 125
            }
        }
    )
    
    total_count: int = Field(
        ..., 
        description="전체 공고 수",
        example=1250
    )
    active_count: int = Field(
        ..., 
        description="활성 공고 수 (삭제되지 않은 공고)",
        example=1180
    )
    by_type: Dict[str, int] = Field(
        ..., 
        description="사업 유형별 공고 수 통계",
        example={
            "기술개발(R&D)": 350,
            "창업교육": 280,
            "멘토링·컨설팅·교육": 220
        }
    )
    by_status: Dict[str, int] = Field(
        ..., 
        description="모집 상태별 공고 수 통계",
        example={
            "진행중": 450,
            "마감": 600,
            "예정": 130
        }
    )
    recent_count: int = Field(
        ..., 
        description="최근 30일 내 등록된 공고 수",
        example=125
    )


class AnnouncementSearch(BaseModel):
    """Search parameters for announcements."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keyword": "스타트업",
                "business_type": "기술개발(R&D)",
                "status": "진행중",
                "is_active": True,
                "date_from": "2025-07-01T00:00:00Z",
                "date_to": "2025-08-31T23:59:59Z"
            }
        }
    )
    
    keyword: Optional[str] = Field(
        None, 
        description="검색 키워드 (공고명, 사업명, 기관명 등에서 검색)",
        example="스타트업",
        min_length=2,
        max_length=100
    )
    business_type: Optional[str] = Field(
        None, 
        description="사업 유형 필터 (정확한 일치)",
        example="기술개발(R&D)"
    )
    status: Optional[str] = Field(
        None, 
        description="모집 상태 필터",
        example="진행중"
    )
    is_active: Optional[bool] = Field(
        None, 
        description="활성 상태 필터 (기본값: True)",
        example=True
    )
    date_from: Optional[datetime] = Field(
        None, 
        description="조회 시작 날짜 (공고 시작일 기준)",
        example="2025-07-01T00:00:00Z"
    )
    date_to: Optional[datetime] = Field(
        None, 
        description="조회 종료 날짜 (공고 종료일 기준)",
        example="2025-08-31T23:59:59Z"
    )