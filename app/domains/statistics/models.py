from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...shared.models import BaseDocument


class StatisticalData(BaseModel):
    """통계 개별 데이터 모델"""
    stat_id: Optional[str] = Field(None, description="통계 ID")
    stat_name: Optional[str] = Field(None, description="통계명")
    stat_type: Optional[str] = Field(None, description="통계 유형")
    period: Optional[str] = Field(None, description="집계 기간")
    year: Optional[int] = Field(None, description="연도")
    month: Optional[int] = Field(None, description="월")
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="지표 데이터")
    total_count: Optional[int] = Field(None, description="총 건수")
    success_count: Optional[int] = Field(None, description="성공 건수") 
    success_rate: Optional[float] = Field(None, description="성공률")


class Statistics(BaseDocument):
    """통계 MongoDB 문서 모델"""
    statistical_data: StatisticalData
    source_url: Optional[str] = Field(None, description="원본 URL")
    is_active: bool = Field(True, description="활성 상태")
    
    class Config:
        collection = "statistics"


class StatisticsCreate(BaseModel):
    """통계 생성 요청 모델"""
    statistical_data: StatisticalData
    source_url: Optional[str] = None


class StatisticsUpdate(BaseModel):
    """통계 수정 요청 모델"""
    statistical_data: Optional[StatisticalData] = None
    source_url: Optional[str] = None
    is_active: Optional[bool] = None


class StatisticsResponse(BaseModel):
    """통계 응답 모델"""
    id: str
    statistical_data: StatisticalData
    source_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime