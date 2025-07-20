from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CustomHTTPException(HTTPException):
    """커스텀 HTTP 예외"""
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str = None,
        details: Any = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class DataNotFoundError(CustomHTTPException):
    """데이터를 찾을 수 없는 경우"""
    def __init__(self, resource: str = "리소스", resource_id: str = None):
        message = f"{resource}를 찾을 수 없습니다"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(
            status_code=404,
            message=message,
            error_code="DATA_NOT_FOUND"
        )


class ValidationError(CustomHTTPException):
    """데이터 검증 오류"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(
            status_code=400,
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ExternalAPIError(CustomHTTPException):
    """외부 API 호출 오류"""
    def __init__(self, service: str, message: str):
        super().__init__(
            status_code=502,
            message=f"{service} API 호출 중 오류가 발생했습니다: {message}",
            error_code="EXTERNAL_API_ERROR"
        )


class DatabaseError(CustomHTTPException):
    """데이터베이스 오류"""
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            message=f"데이터베이스 오류: {message}",
            error_code="DATABASE_ERROR"
        )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 예외 핸들러"""
    error_response = {
        "success": False,
        "message": exc.detail,
        "error_code": "HTTP_ERROR",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if isinstance(exc, CustomHTTPException):
        error_response.update({
            "error_code": exc.error_code,
            "details": exc.details
        })
    
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """검증 오류 핸들러"""
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = {
        "success": False,
        "message": "요청 데이터 검증에 실패했습니다",
        "error_code": "VALIDATION_ERROR",
        "details": error_details,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    logger.error(f"Validation Error: {error_details}")
    return JSONResponse(
        status_code=422,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    error_response = {
        "success": False,
        "message": "서버 내부 오류가 발생했습니다",
        "error_code": "INTERNAL_SERVER_ERROR",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    logger.error(f"Unhandled Exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=error_response
    )