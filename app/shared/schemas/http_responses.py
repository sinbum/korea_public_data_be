"""
HTTP status code specific response schemas.

Defines standardized response models for each HTTP status code
used throughout the API for comprehensive OpenAPI documentation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from .base import ErrorResponse, ErrorDetail, ResponseStatus, ValidationErrorResponse


class BadRequestResponse(BaseModel):
    """HTTP 400 Bad Request response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "BadRequest",
                    "message": "잘못된 요청입니다. 요청 파라미터를 확인해주세요.",
                    "details": [
                        {
                            "field": "page_no",
                            "code": "value_error.number.not_ge",
                            "message": "페이지 번호는 1 이상이어야 합니다.",
                            "input_value": 0
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Bad Request 오류 정보",
        example={
            "type": "BadRequest",
            "message": "잘못된 요청입니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class UnauthorizedResponse(BaseModel):
    """HTTP 401 Unauthorized response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "Unauthorized",
                    "message": "인증이 필요합니다. 유효한 토큰을 제공해주세요.",
                    "details": [
                        {
                            "code": "missing_token",
                            "message": "Authorization 헤더가 없습니다.",
                            "input_value": None
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="인증 오류 정보",
        example={
            "type": "Unauthorized",
            "message": "인증이 필요합니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class ForbiddenResponse(BaseModel):
    """HTTP 403 Forbidden response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "Forbidden",
                    "message": "접근 권한이 없습니다. 관리자 권한이 필요합니다.",
                    "details": [
                        {
                            "code": "insufficient_permissions",
                            "message": "admin 스코프가 필요합니다.",
                            "input_value": "read"
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="권한 오류 정보",
        example={
            "type": "Forbidden",
            "message": "접근 권한이 없습니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class NotFoundResponse(BaseModel):
    """HTTP 404 Not Found response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "NotFound",
                    "message": "요청한 리소스를 찾을 수 없습니다.",
                    "details": [
                        {
                            "field": "announcement_id",
                            "code": "not_found",
                            "message": "ID '65f1a2b3c4d5e6f7a8b9c0d1'에 해당하는 사업공고를 찾을 수 없습니다.",
                            "input_value": "65f1a2b3c4d5e6f7a8b9c0d1"
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Not Found 오류 정보",
        example={
            "type": "NotFound",
            "message": "요청한 리소스를 찾을 수 없습니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class ConflictResponse(BaseModel):
    """HTTP 409 Conflict response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "Conflict",
                    "message": "리소스 충돌이 발생했습니다. 동일한 데이터가 이미 존재합니다.",
                    "details": [
                        {
                            "field": "announcement_id",
                            "code": "duplicate_entry",
                            "message": "동일한 공고 ID가 이미 존재합니다.",
                            "input_value": "174329"
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Conflict 오류 정보",
        example={
            "type": "Conflict",
            "message": "리소스 충돌이 발생했습니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class RateLimitResponse(BaseModel):
    """HTTP 429 Too Many Requests response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "RateLimitExceeded",
                    "message": "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                    "details": [
                        {
                            "code": "rate_limit_exceeded",
                            "message": "분당 최대 5회 호출 가능합니다.",
                            "input_value": "6th_request"
                        }
                    ]
                },
                "retry_after": 60,
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Rate Limit 오류 정보",
        example={
            "type": "RateLimitExceeded",
            "message": "API 호출 한도를 초과했습니다.",
            "details": []
        }
    )
    retry_after: Optional[int] = Field(
        None,
        description="재시도 가능한 시간(초)",
        example=60
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class InternalServerErrorResponse(BaseModel):
    """HTTP 500 Internal Server Error response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "InternalServerError",
                    "message": "서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    "details": [
                        {
                            "code": "database_connection_error",
                            "message": "데이터베이스 연결에 실패했습니다.",
                            "input_value": None
                        }
                    ]
                },
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Internal Server Error 정보",
        example={
            "type": "InternalServerError",
            "message": "서버 내부 오류가 발생했습니다.",
            "details": []
        }
    )
    timestamp: str = Field(..., description="응답 생성 시각")


class ServiceUnavailableResponse(BaseModel):
    """HTTP 503 Service Unavailable response schema."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "status": "error",
                "error": {
                    "type": "ServiceUnavailable",
                    "message": "서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
                    "details": [
                        {
                            "code": "external_api_unavailable",
                            "message": "공공데이터 API 서버가 응답하지 않습니다.",
                            "input_value": "apis.data.go.kr"
                        }
                    ]
                },
                "retry_after": 300,
                "timestamp": "2025-07-27T00:00:00Z"
            }
        }
    )
    
    success: bool = Field(False, description="요청 성공 여부")
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    error: Dict[str, Any] = Field(
        ...,
        description="Service Unavailable 오류 정보",
        example={
            "type": "ServiceUnavailable",
            "message": "서비스를 일시적으로 사용할 수 없습니다.",
            "details": []
        }
    )
    retry_after: Optional[int] = Field(
        None,
        description="재시도 권장 시간(초)",
        example=300
    )
    timestamp: str = Field(..., description="응답 생성 시각")


# 공통 HTTP 응답 모델 딕셔너리 (라우터에서 재사용 가능)
COMMON_HTTP_RESPONSES = {
    400: {
        "model": BadRequestResponse,
        "description": "잘못된 요청 - 요청 파라미터 오류 또는 형식 불일치"
    },
    401: {
        "model": UnauthorizedResponse,
        "description": "인증 필요 - 유효한 인증 토큰이 필요함"
    },
    403: {
        "model": ForbiddenResponse,
        "description": "접근 금지 - 충분한 권한이 없음"
    },
    404: {
        "model": NotFoundResponse,
        "description": "리소스를 찾을 수 없음 - 요청한 데이터가 존재하지 않음"
    },
    409: {
        "model": ConflictResponse,
        "description": "리소스 충돌 - 중복 데이터 또는 비즈니스 규칙 위반"
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "입력 데이터 검증 오류 - 필수 필드 누락 또는 형식 오류"
    },
    429: {
        "model": RateLimitResponse,
        "description": "요청 한도 초과 - Rate Limiting에 의한 일시적 차단"
    },
    500: {
        "model": InternalServerErrorResponse,
        "description": "서버 내부 오류 - 예상치 못한 서버 오류 발생"
    },
    503: {
        "model": ServiceUnavailableResponse,
        "description": "서비스 일시 중단 - 외부 의존성 오류 또는 점검 중"
    }
}


# 읽기 전용 API용 HTTP 응답 (GET 엔드포인트)
READ_ONLY_HTTP_RESPONSES = {
    400: COMMON_HTTP_RESPONSES[400],
    401: COMMON_HTTP_RESPONSES[401],
    403: COMMON_HTTP_RESPONSES[403],
    404: COMMON_HTTP_RESPONSES[404],
    429: COMMON_HTTP_RESPONSES[429],
    500: COMMON_HTTP_RESPONSES[500],
    503: COMMON_HTTP_RESPONSES[503]
}


# 쓰기 가능 API용 HTTP 응답 (POST, PUT, DELETE 엔드포인트)
WRITE_HTTP_RESPONSES = {
    **READ_ONLY_HTTP_RESPONSES,
    409: COMMON_HTTP_RESPONSES[409],
    422: COMMON_HTTP_RESPONSES[422]
}