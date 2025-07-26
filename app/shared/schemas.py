from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class APIResponse(BaseModel):
    """공통 API 응답 모델"""
    success: bool = Field(True, description="요청 성공 여부")
    message: str = Field("성공", description="응답 메시지")
    data: Optional[Any] = Field(None, description="응답 데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "성공",
                "data": {}
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = Field(False, description="요청 성공 여부")
    message: str = Field(description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")
    details: Optional[Dict[str, Any]] = Field(None, description="상세 에러 정보")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="에러 발생 시간")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "요청을 처리할 수 없습니다",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "잘못된 값입니다"},
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class PaginationMeta(BaseModel):
    """페이지네이션 메타데이터"""
    page: int = Field(description="현재 페이지")
    limit: int = Field(description="페이지당 항목 수")
    total: int = Field(description="전체 항목 수")
    total_pages: int = Field(description="전체 페이지 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
    has_previous: bool = Field(description="이전 페이지 존재 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "limit": 20,
                "total": 150,
                "total_pages": 8,
                "has_next": True,
                "has_previous": False
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답 모델"""
    success: bool = Field(True, description="요청 성공 여부")
    message: str = Field("성공", description="응답 메시지")
    data: List[T] = Field(description="응답 데이터 목록")
    meta: PaginationMeta = Field(description="페이지네이션 정보")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "성공",
                "data": [],
                "meta": {
                    "page": 1,
                    "limit": 20,
                    "total": 150,
                    "total_pages": 8,
                    "has_next": True,
                    "has_previous": False
                }
            }
        }


class FetchDataRequest(BaseModel):
    """데이터 수집 요청 모델"""
    page_no: int = Field(1, ge=1, description="페이지 번호 (1부터 시작)")
    num_of_rows: int = Field(10, ge=1, le=100, description="한 페이지당 결과 수 (최대 100)")
    
    class Config:
        schema_extra = {
            "example": {
                "page_no": 1,
                "num_of_rows": 10
            }
        }


class DataCollectionResult(BaseModel):
    """데이터 수집 결과 모델"""
    total_fetched: int = Field(description="수집된 총 데이터 수")
    new_items: int = Field(description="새로 추가된 데이터 수")
    updated_items: int = Field(description="업데이트된 데이터 수")
    skipped_items: int = Field(description="중복으로 스킵된 데이터 수")
    errors: List[str] = Field(default_factory=list, description="수집 중 발생한 오류 목록")
    collection_time: float = Field(description="수집 소요 시간(초)")
    
    class Config:
        schema_extra = {
            "example": {
                "total_fetched": 15,
                "new_items": 10,
                "updated_items": 3,
                "skipped_items": 2,
                "errors": [],
                "collection_time": 2.45
            }
        }