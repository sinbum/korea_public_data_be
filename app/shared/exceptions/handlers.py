"""
Enhanced exception handlers for FastAPI application.

Provides comprehensive exception handling with standardized response formats,
proper logging, and integration with the custom exception system.
"""

import logging
import traceback
from datetime import datetime
from typing import Union, Dict, Any, List
from uuid import uuid4

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..responses import (
    error_response,
    validation_error_response,
    ErrorDetail,
    HTTPStatusCodes
)
from .api_exceptions import KoreanPublicAPIError
from .data_exceptions import DataValidationError
from .custom_exceptions import BaseAPIException

logger = logging.getLogger(__name__)


def _generate_request_id() -> str:
    """Generate a unique request ID for error tracking."""
    return f"req_{uuid4().hex[:12]}"


def _extract_validation_errors(exc: RequestValidationError) -> List[Dict[str, Any]]:
    """
    Extract and format validation errors from RequestValidationError.
    
    Args:
        exc: RequestValidationError instance
        
    Returns:
        List of formatted error dictionaries
    """
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        errors.append({
            "code": "VALIDATION_ERROR",
            "message": error["msg"],
            "field": field_path or "unknown",
            "context": {
                "type": error["type"],
                "value": error.get("input")
            }
        })
    return errors


async def base_api_exception_handler(
    request: Request,
    exc: BaseAPIException
) -> JSONResponse:
    """
    Handle custom BaseAPIException and its subclasses.
    
    This handler processes our custom exceptions that already have
    structured error information.
    """
    request_id = _generate_request_id()
    
    # Log the exception with context
    logger.error(
        f"API Exception [{request_id}]: {exc.error_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "context": exc.context
        }
    )
    
    # Build error list
    errors = exc.errors if exc.errors else [exc.to_error_detail()]
    
    return error_response(
        errors=errors,
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id,
        error_type=exc.error_code,
        path=str(request.url.path),
        method=request.method,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


async def http_exception_handler(
    request: Request,
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """
    Handle standard HTTP exceptions from FastAPI/Starlette.
    
    Converts standard HTTP exceptions to our standardized error format.
    """
    request_id = _generate_request_id()
    
    # Log the exception
    logger.error(
        f"HTTP Exception [{request_id}]: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    
    errors = [
        ErrorDetail(
            code=error_code,
            message=str(exc.detail) if exc.detail else "An error occurred",
            context={"status_code": exc.status_code}
        )
    ]
    
    return error_response(
        errors=errors,
        message=str(exc.detail) if exc.detail else f"HTTP {exc.status_code} Error",
        status_code=exc.status_code,
        request_id=request_id,
        error_type=error_code,
        path=str(request.url.path),
        method=request.method
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation exceptions.
    
    Provides detailed field-level validation error information
    in a standardized format.
    """
    request_id = _generate_request_id()
    
    # Log validation errors
    logger.warning(
        f"Validation Error [{request_id}]: {len(exc.errors())} validation errors",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    # Extract and format validation errors
    errors = _extract_validation_errors(exc)
    
    return validation_error_response(
        errors=errors,
        message=f"Validation failed for {len(errors)} field(s)"
    )


async def korean_api_exception_handler(
    request: Request,
    exc: KoreanPublicAPIError
) -> JSONResponse:
    """
    Handle Korean Public API specific exceptions.
    
    These are exceptions from external API calls that need
    special handling and formatting.
    """
    request_id = _generate_request_id()
    
    # Log the API error
    logger.error(
        f"Korean API Error [{request_id}]: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
    
    errors = [
        ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            context=exc.details or {}
        )
    ]
    
    # Map to appropriate HTTP status code
    status_code = exc.status_code or HTTPStatusCodes.BAD_GATEWAY
    
    return error_response(
        errors=errors,
        message=exc.message,
        status_code=status_code,
        request_id=request_id,
        error_type="EXTERNAL_API_ERROR",
        path=str(request.url.path),
        method=request.method
    )


async def data_validation_exception_handler(
    request: Request,
    exc: DataValidationError
) -> JSONResponse:
    """
    Handle data validation exceptions.
    
    These are business logic validation errors that occur
    during data processing.
    """
    request_id = _generate_request_id()
    
    # Log the validation error
    logger.warning(
        f"Data Validation Error [{request_id}]: {exc.field_name} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "field": exc.field_name
        }
    )
    
    errors = [
        ErrorDetail(
            code="DATA_VALIDATION_ERROR",
            message=str(exc),
            field=exc.field_name,
            context={"validation_type": "business_logic"}
        )
    ]
    
    return error_response(
        errors=errors,
        message="Data validation failed",
        status_code=HTTPStatusCodes.BAD_REQUEST,
        request_id=request_id,
        error_type="DATA_VALIDATION_ERROR",
        path=str(request.url.path),
        method=request.method
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle all unhandled exceptions.
    
    This is the catch-all handler for any exceptions not caught
    by specific handlers. Logs full stack trace for debugging.
    """
    request_id = _generate_request_id()
    
    # Log the full exception with stack trace
    logger.exception(
        f"Unhandled Exception [{request_id}]: {type(exc).__name__}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    # Don't expose internal error details in production
    message = "An unexpected error occurred"
    if logger.isEnabledFor(logging.DEBUG):
        message = f"{type(exc).__name__}: {str(exc)}"
    
    errors = [
        ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message=message,
            context={
                "exception_type": type(exc).__name__,
                "request_id": request_id
            }
        )
    ]
    
    return error_response(
        errors=errors,
        message="Internal server error",
        status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
        request_id=request_id,
        error_type="INTERNAL_SERVER_ERROR",
        path=str(request.url.path),
        method=request.method
    )


# Export handlers for easy import
__all__ = [
    "base_api_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "korean_api_exception_handler",
    "data_validation_exception_handler",
    "general_exception_handler"
]