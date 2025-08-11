from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum
from ...shared.models.base import BaseDocument


class DataRequestStatus(str, Enum):
    """데이터 요청 상태"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataRequestPriority(str, Enum):
    """데이터 요청 우선순위"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VoteType(str, Enum):
    """투표 타입"""
    LIKE = "like"
    DISLIKE = "dislike"


class Category(BaseModel):
    """카테고리 모델"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="카테고리 ID")
    name: str = Field(..., description="카테고리 이름")
    description: Optional[str] = Field(None, description="카테고리 설명")
    color: str = Field(..., description="카테고리 색상")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성일")


class Vote(BaseModel):
    """투표 모델"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="투표 ID")
    request_id: str = Field(..., description="요청 ID")
    user_id: str = Field(..., description="사용자 ID")
    vote_type: VoteType = Field(..., description="투표 타입")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성일")


class DataRequestData(BaseModel):
    """데이터 요청 개별 데이터 모델"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    # === 기본 정보 ===
    title: str = Field(..., description="요청 제목", min_length=1, max_length=200)
    description: str = Field(..., description="요청 설명", min_length=1, max_length=2000)
    category_id: str = Field(..., description="카테고리 ID")
    user_id: str = Field(..., description="요청자 ID")
    user_name: Optional[str] = Field(None, description="요청자 이름")
    user_email: Optional[str] = Field(None, description="요청자 이메일")
    
    # === 상태 정보 ===
    status: DataRequestStatus = Field(
        default=DataRequestStatus.PENDING,
        description="요청 상태"
    )
    priority: DataRequestPriority = Field(
        default=DataRequestPriority.MEDIUM,
        description="우선순위"
    )
    
    # === 투표 정보 ===
    vote_count: int = Field(default=0, description="총 투표 수", ge=0)
    likes_count: int = Field(default=0, description="좋아요 수", ge=0)
    dislikes_count: int = Field(default=0, description="싫어요 수", ge=0)
    
    # === 관계 필드 ===
    category: Optional[Category] = Field(None, description="카테고리 정보")
    votes: List[Vote] = Field(default_factory=list, description="투표 목록")
    
    # === 메타 정보 ===
    admin_notes: Optional[str] = Field(None, description="관리자 메모")
    estimated_completion: Optional[datetime] = Field(None, description="예상 완료일")
    actual_completion: Optional[datetime] = Field(None, description="실제 완료일")
    
    # === 검색/필터링용 필드 ===
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    search_keywords: Optional[str] = Field(None, description="검색 키워드")
    
    # === 참고 데이터 링크 ===
    reference_data_url: Optional[str] = Field(None, description="참고 공공데이터 링크 주소")


class DataRequest(BaseDocument):
    """데이터 요청 MongoDB 문서 모델"""
    
    # 데이터 요청 정보를 포함
    data: DataRequestData = Field(..., description="데이터 요청 정보")
    
    # BaseDocument에서 상속받는 필드들:
    # - id: ObjectId (aliased as _id)
    # - created_at: datetime  
    # - updated_at: datetime
    
    # 추가 메타데이터
    source: str = Field(default="web", description="요청 출처")
    ip_address: Optional[str] = Field(None, description="요청자 IP")
    user_agent: Optional[str] = Field(None, description="사용자 에이전트")
    is_active: bool = Field(default=True, description="활성 상태")
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True
    )
    
    def get_id(self) -> str:
        """문서 ID를 문자열로 반환"""
        return str(self.id)
    
    def get_title(self) -> str:
        return self.data.title
    
    def get_description(self) -> str:
        return self.data.description
    
    def get_status(self) -> DataRequestStatus:
        return self.data.status
    
    def get_priority(self) -> DataRequestPriority:
        return self.data.priority
    
    def get_vote_count(self) -> int:
        return self.data.vote_count
    
    def get_category_id(self) -> str:
        return self.data.category_id
    
    def get_user_id(self) -> str:
        return self.data.user_id


class CategoryDocument(BaseDocument):
    """카테고리 MongoDB 문서 모델"""
    
    data: Category = Field(..., description="카테고리 정보")
    is_active: bool = Field(default=True, description="활성 상태")
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True
    )
    
    def get_id(self) -> str:
        return str(self.id)
    
    def get_name(self) -> str:
        return self.data.name


class VoteDocument(BaseDocument):
    """투표 MongoDB 문서 모델"""
    
    data: Vote = Field(..., description="투표 정보")
    is_active: bool = Field(default=True, description="활성 상태")
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True
    )
    
    def get_id(self) -> str:
        return str(self.id)
    
    def get_request_id(self) -> str:
        return self.data.request_id
    
    def get_user_id(self) -> str:
        return self.data.user_id
    
    def get_vote_type(self) -> VoteType:
        return self.data.vote_type