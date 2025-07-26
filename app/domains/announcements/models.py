from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from ...shared.models.base import BaseDocument


class AnnouncementData(BaseModel):
    """사업공고 개별 데이터 모델"""
    business_id: Optional[str] = Field(
        None, 
        description="사업 고유 ID",
        example="KISED-2024-001"
    )
    business_name: Optional[str] = Field(
        None, 
        description="사업명",
        example="창업도약패키지"
    )
    business_type: Optional[str] = Field(
        None, 
        description="사업 유형 분류",
        example="정부지원사업"
    )
    business_overview: Optional[str] = Field(
        None, 
        description="사업의 목적과 주요 내용 요약",
        example="유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진"
    )
    support_target: Optional[str] = Field(
        None, 
        description="지원 대상 및 자격 요건",
        example="창업 3년 이내 기업, 매출 10억원 미만"
    )
    recruitment_period: Optional[str] = Field(
        None, 
        description="모집 기간",
        example="2024.03.15 ~ 2024.04.15"
    )
    application_method: Optional[str] = Field(
        None, 
        description="신청 방법 및 절차",
        example="온라인 접수 (www.k-startup.go.kr)"
    )
    contact_info: Optional[str] = Field(
        None, 
        description="문의처 정보",
        example="창업진흥원 창업성장실 02-123-4567"
    )
    announcement_date: Optional[datetime] = Field(
        None, 
        description="공고 발표일"
    )
    deadline: Optional[datetime] = Field(
        None, 
        description="신청 마감일"
    )
    status: Optional[str] = Field(
        None, 
        description="공고 현재 상태",
        example="모집중"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        },
        json_schema_extra={
            "example": {
                "business_id": "KISED-2024-001",
                "business_name": "창업도약패키지",
                "business_type": "정부지원사업",
                "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
                "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
                "recruitment_period": "2024.03.15 ~ 2024.04.15",
                "application_method": "온라인 접수 (www.k-startup.go.kr)",
                "contact_info": "창업진흥원 창업성장실 02-123-4567",
                "announcement_date": "2024-03-01T09:00:00Z",
                "deadline": "2024-04-15T18:00:00Z",
                "status": "모집중"
            }
        }
    )


class Announcement(BaseModel):
    """사업공고 MongoDB 문서 모델"""
    id: Optional[str] = Field(None, alias="_id", description="고유 식별자")
    announcement_data: AnnouncementData
    source_url: Optional[str] = Field(None, description="원본 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }
    )


class AnnouncementCreate(BaseModel):
    """사업공고 생성 요청 모델"""
    announcement_data: AnnouncementData = Field(
        description="생성할 사업공고 데이터"
    )
    source_url: Optional[str] = Field(
        None,
        description="데이터 출처 URL",
        example="https://www.data.go.kr/dataset/15121654"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "business_id": "KISED-2024-001",
                    "business_name": "창업도약패키지",
                    "business_type": "정부지원사업",
                    "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
                    "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
                    "status": "모집중"
                },
                "source_url": "https://www.data.go.kr/dataset/15121654"
            }
        }
    )


class AnnouncementUpdate(BaseModel):
    """사업공고 수정 요청 모델"""
    announcement_data: Optional[AnnouncementData] = Field(
        None,
        description="수정할 사업공고 데이터 (일부 필드만 업데이트 가능)"
    )
    source_url: Optional[str] = Field(
        None,
        description="수정할 출처 URL"
    )
    is_active: Optional[bool] = Field(
        None,
        description="활성 상태 변경 (True: 활성, False: 비활성)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "announcement_data": {
                    "status": "마감"
                },
                "is_active": False
            }
        }
    )


class AnnouncementResponse(BaseModel):
    """사업공고 응답 모델"""
    id: str = Field(
        description="사업공고 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    )
    announcement_data: AnnouncementData = Field(
        description="사업공고 상세 데이터"
    )
    source_url: Optional[str] = Field(
        description="데이터 출처 URL",
        example="https://www.data.go.kr/dataset/15121654"
    )
    is_active: bool = Field(
        description="활성 상태",
        example=True
    )
    created_at: datetime = Field(
        description="생성 일시",
        example="2024-03-01T09:00:00Z"
    )
    updated_at: datetime = Field(
        description="최종 수정 일시",
        example="2024-03-01T09:00:00Z"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z" if v else None
        },
        json_schema_extra={
            "example": {
                "id": "65f1a2b3c4d5e6f7a8b9c0d1",
                "announcement_data": {
                    "business_id": "KISED-2024-001",
                    "business_name": "창업도약패키지",
                    "business_type": "정부지원사업",
                    "business_overview": "유망 창업기업의 성장 단계별 맞춤형 지원을 통한 스케일업 촉진",
                    "support_target": "창업 3년 이내 기업, 매출 10억원 미만",
                    "recruitment_period": "2024.03.15 ~ 2024.04.15",
                    "application_method": "온라인 접수 (www.k-startup.go.kr)",
                    "contact_info": "창업진흥원 창업성장실 02-123-4567",
                    "announcement_date": "2024-03-01T09:00:00Z",
                    "deadline": "2024-04-15T18:00:00Z",
                    "status": "모집중"
                },
                "source_url": "https://www.data.go.kr/dataset/15121654",
                "is_active": True,
                "created_at": "2024-03-01T09:00:00Z",
                "updated_at": "2024-03-01T09:00:00Z"
            }
        }
    )