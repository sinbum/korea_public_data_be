from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import DataRequestStatus, DataRequestPriority, VoteType


# === 요청/응답 스키마 ===

class DataRequestCreateRequest(BaseModel):
    """데이터 요청 생성 요청 스키마"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    title: str = Field(..., description="요청 제목", min_length=1, max_length=200, example="공공 WiFi 위치 데이터")
    description: str = Field(..., description="요청 설명", min_length=1, max_length=2000, example="서울시 내 공공 WiFi 설치 위치와 접속 정보를 제공해주세요.")
    category_id: str = Field(..., description="카테고리 ID", example="transport")
    priority: Optional[DataRequestPriority] = Field(default=DataRequestPriority.MEDIUM, description="우선순위")
    tags: Optional[List[str]] = Field(default_factory=list, description="태그 목록", example=["wifi", "공공", "서울"])
    reference_data_url: Optional[str] = Field(None, description="참고 공공데이터 링크 주소", example="https://data.go.kr/dataset/example")


class DataRequestUpdateRequest(BaseModel):
    """데이터 요청 수정 요청 스키마"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    title: Optional[str] = Field(None, description="요청 제목", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="요청 설명", min_length=1, max_length=2000)
    category_id: Optional[str] = Field(None, description="카테고리 ID")
    priority: Optional[DataRequestPriority] = Field(None, description="우선순위")
    tags: Optional[List[str]] = Field(None, description="태그 목록")
    reference_data_url: Optional[str] = Field(None, description="참고 공공데이터 링크 주소")


class DataRequestStatusUpdateRequest(BaseModel):
    """데이터 요청 상태 변경 요청 스키마 (관리자용)"""
    status: DataRequestStatus = Field(..., description="새로운 상태")
    admin_notes: Optional[str] = Field(None, description="관리자 메모", max_length=500)
    estimated_completion: Optional[datetime] = Field(None, description="예상 완료일")


class VoteRequest(BaseModel):
    """투표 요청 스키마"""
    request_id: str = Field(..., description="요청 ID")
    vote_type: VoteType = Field(..., description="투표 타입")


class CategoryCreateRequest(BaseModel):
    """카테고리 생성 요청 스키마"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., description="카테고리 이름", min_length=1, max_length=50, example="교통")
    description: Optional[str] = Field(None, description="카테고리 설명", max_length=200, example="교통 관련 데이터")
    color: str = Field(..., description="카테고리 색상", example="#3B82F6")


# === 응답 스키마 ===

class CategoryResponse(BaseModel):
    """카테고리 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="카테고리 ID")
    name: str = Field(..., description="카테고리 이름")
    description: Optional[str] = Field(None, description="카테고리 설명")
    color: str = Field(..., description="카테고리 색상")
    created_at: datetime = Field(..., description="생성일")


class VoteResponse(BaseModel):
    """투표 응답 스키마"""
    success: bool = Field(..., description="성공 여부")
    vote_count: int = Field(..., description="총 투표 수")
    likes_count: int = Field(..., description="좋아요 수")
    dislikes_count: int = Field(..., description="싫어요 수")
    user_voted: bool = Field(..., description="사용자 투표 여부")
    user_vote_type: Optional[VoteType] = Field(None, description="사용자 투표 타입")


class DataRequestResponse(BaseModel):
    """데이터 요청 응답 스키마"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="요청 ID")
    title: str = Field(..., description="요청 제목")
    description: str = Field(..., description="요청 설명")
    category_id: str = Field(..., description="카테고리 ID")
    category: Optional[CategoryResponse] = Field(None, description="카테고리 정보")
    user_id: str = Field(..., description="요청자 ID")
    user_name: Optional[str] = Field(None, description="요청자 이름")
    user_email: Optional[str] = Field(None, description="요청자 이메일")
    status: DataRequestStatus = Field(..., description="요청 상태")
    priority: DataRequestPriority = Field(..., description="우선순위")
    vote_count: int = Field(..., description="총 투표 수")
    likes_count: int = Field(..., description="좋아요 수")
    dislikes_count: int = Field(..., description="싫어요 수")
    user_voted: Optional[bool] = Field(None, description="현재 사용자 투표 여부")
    user_vote_type: Optional[VoteType] = Field(None, description="현재 사용자 투표 타입")
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    reference_data_url: Optional[str] = Field(None, description="참고 공공데이터 링크 주소")
    admin_notes: Optional[str] = Field(None, description="관리자 메모")
    estimated_completion: Optional[datetime] = Field(None, description="예상 완료일")
    actual_completion: Optional[datetime] = Field(None, description="실제 완료일")
    created_at: datetime = Field(..., description="생성일")
    updated_at: datetime = Field(..., description="수정일")


class DataRequestListResponse(BaseModel):
    """데이터 요청 목록 응답 스키마"""
    data: List[DataRequestResponse] = Field(..., description="데이터 요청 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    limit: int = Field(..., description="페이지당 개수")
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_previous: bool = Field(..., description="이전 페이지 존재 여부")


# === 필터 스키마 ===

class DataRequestFilters(BaseModel):
    """데이터 요청 필터 스키마"""
    category: Optional[str] = Field(None, description="카테고리 ID")
    status: Optional[DataRequestStatus] = Field(None, description="상태")
    priority: Optional[DataRequestPriority] = Field(None, description="우선순위")
    search: Optional[str] = Field(None, description="검색어", max_length=100)
    tags: Optional[List[str]] = Field(None, description="태그 목록")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    sort: Optional[str] = Field(default="likes", description="정렬 기준", pattern="^(likes|newest|oldest|priority)$")
    page: int = Field(default=1, description="페이지", ge=1)
    limit: int = Field(default=20, description="페이지당 개수", ge=1, le=100)
    
    @validator('sort')
    def validate_sort(cls, v):
        allowed_sorts = ['likes', 'newest', 'oldest', 'priority']
        if v not in allowed_sorts:
            raise ValueError(f'sort must be one of {allowed_sorts}')
        return v


# === 통계 스키마 ===

class DataRequestStatsResponse(BaseModel):
    """데이터 요청 통계 응답 스키마"""
    total_requests: int = Field(..., description="전체 요청 수")
    pending_requests: int = Field(..., description="대기중 요청 수")
    in_progress_requests: int = Field(..., description="진행중 요청 수")
    completed_requests: int = Field(..., description="완료된 요청 수")
    rejected_requests: int = Field(..., description="거절된 요청 수")
    total_votes: int = Field(..., description="전체 투표 수")
    requests_by_category: Dict[str, int] = Field(..., description="카테고리별 요청 수")
    popular_requests: List[DataRequestResponse] = Field(..., description="인기 요청 목록")


# === 검색 스키마 ===

class DataRequestSearchRequest(BaseModel):
    """데이터 요청 검색 요청 스키마"""
    query: str = Field(..., description="검색어", min_length=1, max_length=100)
    category: Optional[str] = Field(None, description="카테고리 ID")
    status: Optional[DataRequestStatus] = Field(None, description="상태")
    sort: Optional[str] = Field(default="relevance", description="정렬 기준")
    page: int = Field(default=1, description="페이지", ge=1)
    limit: int = Field(default=20, description="페이지당 개수", ge=1, le=100)