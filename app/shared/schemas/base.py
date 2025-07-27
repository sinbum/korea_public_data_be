"""
Base Pydantic schemas for common API response patterns.

Provides standardized response models used across all API endpoints
with comprehensive validation and OpenAPI documentation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum

# Generic type for data content
T = TypeVar('T')


class ResponseStatus(str, Enum):
    """API response status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper for all endpoints.
    
    Provides consistent response structure across the entire API.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "status": "success",
                "data": {},
                "message": "작업이 성공적으로 완료되었습니다.",
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="요청 성공 여부",
        example=True
    )
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="응답 상태 (success, error, warning)",
        example="success"
    )
    data: Optional[T] = Field(
        None,
        description="응답 데이터 (성공 시)"
    )
    message: str = Field(
        ...,
        description="응답 메시지",
        example="작업이 성공적으로 완료되었습니다."
    )
    timestamp: str = Field(
        ...,
        description="응답 생성 시각 (ISO 8601 형식)",
        example="2025-07-27T00:00:00Z"
    )


class ErrorDetail(BaseModel):
    """Error detail information."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "email",
                "code": "invalid_format",
                "message": "올바른 이메일 형식이 아닙니다.",
                "input_value": "invalid-email"
            }
        }
    )
    
    field: Optional[str] = Field(
        None,
        description="오류가 발생한 필드명",
        example="email"
    )
    code: str = Field(
        ...,
        description="오류 코드",
        example="invalid_format"
    )
    message: str = Field(
        ...,
        description="오류 메시지",
        example="올바른 이메일 형식이 아닙니다."
    )
    input_value: Optional[Any] = Field(
        None,
        description="입력된 값",
        example="invalid-email"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response for all endpoints.
    
    Used for HTTP 4xx and 5xx responses.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "ValidationError",
                    "message": "입력 데이터 검증에 실패했습니다.",
                    "details": [
                        {
                            "field": "email",
                            "code": "invalid_format",
                            "message": "올바른 이메일 형식이 아닙니다.",
                            "input_value": "invalid-email"
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(
        False,
        description="요청 성공 여부 (항상 False)",
        example=False
    )
    status: ResponseStatus = Field(
        ResponseStatus.ERROR,
        description="응답 상태 (error)",
        example="error"
    )
    error: Dict[str, Any] = Field(
        ...,
        description="오류 정보",
        example={
            "type": "ValidationError",
            "message": "입력 데이터 검증에 실패했습니다.",
            "details": []
        }
    )
    timestamp: str = Field(
        ...,
        description="응답 생성 시각 (ISO 8601 형식)",
        example="2025-07-27T00:00:00Z"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 1250,
                "pages": 63,
                "has_prev": False,
                "has_next": True,
                "prev_page": None,
                "next_page": 2
            }
        }
    )
    
    page: int = Field(
        ...,
        description="현재 페이지 번호 (1부터 시작)",
        example=1,
        ge=1
    )
    per_page: int = Field(
        ...,
        description="페이지당 항목 수",
        example=20,
        ge=1,
        le=100
    )
    total: int = Field(
        ...,
        description="전체 항목 수",
        example=1250,
        ge=0
    )
    pages: int = Field(
        ...,
        description="전체 페이지 수",
        example=63,
        ge=0
    )
    has_prev: bool = Field(
        ...,
        description="이전 페이지 존재 여부",
        example=False
    )
    has_next: bool = Field(
        ...,
        description="다음 페이지 존재 여부",
        example=True
    )
    prev_page: Optional[int] = Field(
        None,
        description="이전 페이지 번호",
        example=None
    )
    next_page: Optional[int] = Field(
        None,
        description="다음 페이지 번호",
        example=2
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper for list endpoints.
    
    Provides consistent pagination structure across all list APIs.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "status": "success",
                "data": {
                    "items": [],
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "total": 1250,
                        "pages": 63,
                        "has_prev": False,
                        "has_next": True,
                        "prev_page": None,
                        "next_page": 2
                    }
                },
                "message": "데이터를 성공적으로 조회했습니다.",
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="요청 성공 여부",
        example=True
    )
    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS,
        description="응답 상태",
        example="success"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="페이지네이션된 데이터",
        example={
            "items": [],
            "pagination": {}
        }
    )
    message: str = Field(
        ...,
        description="응답 메시지",
        example="데이터를 성공적으로 조회했습니다."
    )
    timestamp: str = Field(
        ...,
        description="응답 생성 시각 (ISO 8601 형식)",
        example="2025-07-27T00:00:00Z"
    )


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-07-27T00:00:00Z",
                "database": "connected",
                "version": "1.0.0",
                "uptime": 3600,
                "environment": "development"
            }
        }
    )
    
    status: str = Field(
        ...,
        description="서비스 상태 (healthy, unhealthy, degraded)",
        example="healthy"
    )
    timestamp: str = Field(
        ...,
        description="응답 생성 시각",
        example="2025-07-27T00:00:00Z"
    )
    database: str = Field(
        ...,
        description="데이터베이스 연결 상태",
        example="connected"
    )
    version: str = Field(
        ...,
        description="API 버전",
        example="1.0.0"
    )
    uptime: Optional[int] = Field(
        None,
        description="서버 가동 시간 (초)",
        example=3600
    )
    environment: Optional[str] = Field(
        None,
        description="실행 환경",
        example="development"
    )


class ValidationErrorResponse(BaseModel):
    """
    Validation error response for HTTP 422 responses.
    
    Used when request data validation fails.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "ValidationError",
                    "message": "입력 데이터 검증 실패",
                    "details": [
                        {
                            "field": "email",
                            "code": "value_error.email",
                            "message": "field required",
                            "input_value": None
                        },
                        {
                            "field": "age",
                            "code": "value_error.number.not_ge",
                            "message": "ensure this value is greater than or equal to 0",
                            "input_value": -5
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(
        False,
        description="요청 성공 여부 (항상 False)",
        example=False
    )
    status: ResponseStatus = Field(
        ResponseStatus.ERROR,
        description="응답 상태 (error)",
        example="error"
    )
    error: Dict[str, Any] = Field(
        ...,
        description="검증 오류 정보",
        example={
            "type": "ValidationError",
            "message": "입력 데이터 검증 실패",
            "details": []
        }
    )
    timestamp: str = Field(
        ...,
        description="응답 생성 시각",
        example="2025-07-27T00:00:00Z"
    )


# Utility functions for creating standard responses
def create_success_response(
    data: Any = None,
    message: str = "작업이 성공적으로 완료되었습니다."
) -> BaseResponse:
    """Create a standard success response."""
    return BaseResponse(
        success=True,
        status=ResponseStatus.SUCCESS,
        data=data,
        message=message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def create_error_response(
    message: str,
    error_type: str = "Error",
    details: Optional[List[ErrorDetail]] = None
) -> ErrorResponse:
    """Create a standard error response."""
    return ErrorResponse(
        success=False,
        status=ResponseStatus.ERROR,
        error={
            "type": error_type,
            "message": message,
            "details": details or []
        },
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def create_paginated_response(
    items: List[Any],
    pagination: PaginationMeta,
    message: str = "데이터를 성공적으로 조회했습니다."
) -> PaginatedResponse:
    """Create a standard paginated response."""
    return PaginatedResponse(
        success=True,
        status=ResponseStatus.SUCCESS,
        data={
            "items": items,
            "pagination": pagination.model_dump()
        },
        message=message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )