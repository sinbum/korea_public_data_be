"""
Business domain Pydantic schemas for API requests and responses.

Provides standardized data models for business-related operations
with proper validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class BusinessResponse(BaseModel):
    """Response schema for business data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )
    
    id: str = Field(..., description="사업 고유 ID")
    business_data: Dict[str, Any] = Field(..., description="사업 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")


class BusinessCreate(BaseModel):
    """Schema for creating new businesses."""
    
    business_data: Dict[str, Any] = Field(..., description="사업 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")


class BusinessUpdate(BaseModel):
    """Schema for updating existing businesses."""
    
    business_data: Optional[Dict[str, Any]] = Field(None, description="사업 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: Optional[bool] = Field(None, description="활성 상태")


class BusinessSummary(BaseModel):
    """Summary schema for business listings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="사업 고유 ID")
    business_name: Optional[str] = Field(None, description="사업명")
    business_field: Optional[str] = Field(None, description="사업분야")
    organization: Optional[str] = Field(None, description="주관기관")
    startup_stage: Optional[str] = Field(None, description="창업단계")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")


class BusinessStats(BaseModel):
    """Statistics schema for businesses."""
    
    total_count: int = Field(..., description="전체 사업 수")
    active_count: int = Field(..., description="활성 사업 수")
    by_field: Dict[str, int] = Field(..., description="분야별 사업 수")
    by_organization: Dict[str, int] = Field(..., description="기관별 사업 수")
    by_startup_stage: Dict[str, int] = Field(..., description="창업단계별 사업 수")
    recent_count: int = Field(..., description="최근 30일 사업 수")


class BusinessSearch(BaseModel):
    """Search parameters for businesses."""
    
    keyword: Optional[str] = Field(None, description="검색 키워드")
    business_field: Optional[str] = Field(None, description="사업분야 필터")
    organization: Optional[str] = Field(None, description="주관기관 필터")
    startup_stage: Optional[str] = Field(None, description="창업단계 필터")
    is_active: Optional[bool] = Field(None, description="활성 상태 필터")
    date_from: Optional[datetime] = Field(None, description="조회 시작 날짜")
    date_to: Optional[datetime] = Field(None, description="조회 종료 날짜")