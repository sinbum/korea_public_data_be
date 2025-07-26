"""
Statistics domain Pydantic schemas for API requests and responses.

Provides standardized data models for statistics-related operations
with proper validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class StatisticsResponse(BaseModel):
    """Response schema for statistics data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )
    
    id: str = Field(..., description="통계 고유 ID")
    statistical_data: Dict[str, Any] = Field(..., description="통계 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: datetime = Field(..., description="수정 일시")


class StatisticsCreate(BaseModel):
    """Schema for creating new statistics."""
    
    statistical_data: Dict[str, Any] = Field(..., description="통계 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: bool = Field(True, description="활성 상태")


class StatisticsUpdate(BaseModel):
    """Schema for updating existing statistics."""
    
    statistical_data: Optional[Dict[str, Any]] = Field(None, description="통계 상세 데이터")
    source_url: Optional[str] = Field(None, description="원본 데이터 URL")
    is_active: Optional[bool] = Field(None, description="활성 상태")


class StatisticsSummary(BaseModel):
    """Summary schema for statistics listings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="통계 고유 ID")
    stat_type: Optional[str] = Field(None, description="통계 유형")
    period: Optional[str] = Field(None, description="기간")
    year: Optional[int] = Field(None, description="연도")
    month: Optional[int] = Field(None, description="월")
    total_count: Optional[int] = Field(None, description="총 건수")
    success_rate: Optional[float] = Field(None, description="성공률")
    is_active: bool = Field(True, description="활성 상태")
    created_at: datetime = Field(..., description="생성 일시")


class StatisticsOverview(BaseModel):
    """Overview schema for statistics."""
    
    total_count: int = Field(..., description="전체 통계 수")
    active_count: int = Field(..., description="활성 통계 수")
    by_type: Dict[str, int] = Field(..., description="타입별 통계 수")
    by_year: Dict[str, int] = Field(..., description="연도별 통계 수")
    by_period: Dict[str, int] = Field(..., description="기간별 통계 수")
    avg_success_rate: float = Field(..., description="평균 성공률")
    recent_count: int = Field(..., description="최근 30일 통계 수")


class MonthlyReport(BaseModel):
    """Monthly report schema."""
    
    year: int = Field(..., description="연도")
    month: int = Field(..., description="월")
    total_count: int = Field(..., description="총 건수")
    success_count: int = Field(..., description="성공 건수")
    success_rate: float = Field(..., description="성공률")
    by_type: Dict[str, int] = Field(..., description="타입별 통계")
    comparison_with_previous: Dict[str, float] = Field(..., description="전월 대비 증감")


class YearlyReport(BaseModel):
    """Yearly report schema."""
    
    year: int = Field(..., description="연도")
    total_count: int = Field(..., description="총 건수")
    success_count: int = Field(..., description="성공 건수")
    success_rate: float = Field(..., description="성공률")
    by_month: Dict[str, int] = Field(..., description="월별 통계")
    by_type: Dict[str, int] = Field(..., description="타입별 통계")
    comparison_with_previous: Dict[str, float] = Field(..., description="전년 대비 증감")


class AggregatedMetrics(BaseModel):
    """Aggregated metrics schema."""
    
    total_records: int = Field(..., description="총 레코드 수")
    avg_success_rate: float = Field(..., description="평균 성공률")
    max_value: Optional[float] = Field(None, description="최대 값")
    min_value: Optional[float] = Field(None, description="최소 값")
    median_value: Optional[float] = Field(None, description="중간 값")
    by_category: Dict[str, Any] = Field(..., description="카테고리별 지표")


class StatisticsSearch(BaseModel):
    """Search parameters for statistics."""
    
    keyword: Optional[str] = Field(None, description="검색 키워드")
    stat_type: Optional[str] = Field(None, description="통계 유형 필터")
    period: Optional[str] = Field(None, description="기간 필터")
    year: Optional[int] = Field(None, description="연도 필터")
    month: Optional[int] = Field(None, ge=1, le=12, description="월 필터")
    min_total_count: Optional[int] = Field(None, description="최소 총 건수")
    min_success_rate: Optional[float] = Field(None, description="최소 성공률")
    is_active: Optional[bool] = Field(None, description="활성 상태 필터")
    date_from: Optional[datetime] = Field(None, description="조회 시작 날짜")
    date_to: Optional[datetime] = Field(None, description="조회 종료 날짜")