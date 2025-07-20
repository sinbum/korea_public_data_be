from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ...shared.models import BaseDocument


class BusinessData(BaseModel):
    """사업정보 개별 데이터 모델"""
    business_id: Optional[str] = Field(None, description="사업 ID")
    business_name: Optional[str] = Field(None, description="사업명")
    business_type: Optional[str] = Field(None, description="사업 유형")
    organization: Optional[str] = Field(None, description="주관기관")
    business_field: Optional[str] = Field(None, description="사업분야")
    description: Optional[str] = Field(None, description="사업설명")
    target_startup_stage: Optional[str] = Field(None, description="대상 창업단계")
    support_scale: Optional[str] = Field(None, description="지원규모")
    support_period: Optional[str] = Field(None, description="지원기간")
    eligibility: Optional[str] = Field(None, description="지원자격")
    selection_method: Optional[str] = Field(None, description="선정방법")
    benefits: Optional[List[str]] = Field(default_factory=list, description="지원혜택")
    website_url: Optional[str] = Field(None, description="웹사이트 URL")
    contact_department: Optional[str] = Field(None, description="담당부서")
    contact_phone: Optional[str] = Field(None, description="연락처")
    contact_email: Optional[str] = Field(None, description="이메일")


class Business(BaseDocument):
    """사업정보 MongoDB 문서 모델"""
    business_data: BusinessData
    source_url: Optional[str] = Field(None, description="원본 URL")
    is_active: bool = Field(True, description="활성 상태")
    
    class Config:
        collection = "businesses"


class BusinessCreate(BaseModel):
    """사업정보 생성 요청 모델"""
    business_data: BusinessData
    source_url: Optional[str] = None


class BusinessUpdate(BaseModel):
    """사업정보 수정 요청 모델"""
    business_data: Optional[BusinessData] = None
    source_url: Optional[str] = None
    is_active: Optional[bool] = None


class BusinessResponse(BaseModel):
    """사업정보 응답 모델"""
    id: str
    business_data: BusinessData
    source_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime