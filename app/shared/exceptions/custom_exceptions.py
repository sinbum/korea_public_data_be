"""
Custom exception classes for standardized error handling.

Extends FastAPI's HTTPException with structured error responses
that integrate with the standard response format system.
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status
from ..responses import ErrorDetail, HTTPStatusCodes


class BaseAPIException(HTTPException):
    """
    Base exception class for all API exceptions.
    
    Provides structured error information that integrates
    with the standard error response format.
    """
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        errors: Optional[List[ErrorDetail]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize base API exception.
        
        Args:
            status_code: HTTP status code
            error_code: Machine-readable error code
            message: Human-readable error message
            errors: List of detailed errors
            headers: Optional HTTP headers
            **kwargs: Additional error context
        """
        self.error_code = error_code
        self.errors = errors or []
        self.context = kwargs
        
        super().__init__(
            status_code=status_code,
            detail=message,
            headers=headers
        )
    
    def to_error_detail(self) -> ErrorDetail:
        """Convert exception to ErrorDetail object."""
        return ErrorDetail(
            code=self.error_code,
            message=self.detail,
            context=self.context
        )


class ValidationException(BaseAPIException):
    """Exception for validation errors (422)."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        error_details = []
        if errors:
            for error in errors:
                error_details.append(ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=error.get("message", "Invalid value"),
                    field=error.get("field"),
                    context=error.get("context")
                ))
        
        super().__init__(
            status_code=HTTPStatusCodes.UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=message,
            errors=error_details,
            **kwargs
        )


class NotFoundException(BaseAPIException):
    """Exception for resource not found errors (404)."""
    
    def __init__(
        self,
        resource: str,
        resource_id: Union[str, int],
        message: Optional[str] = None,
        **kwargs
    ):
        default_message = f"{resource} with id '{resource_id}' not found"
        
        super().__init__(
            status_code=HTTPStatusCodes.NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            message=message or default_message,
            resource=resource,
            resource_id=str(resource_id),
            **kwargs
        )


class ConflictException(BaseAPIException):
    """Exception for resource conflicts (409)."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflict_field: Optional[str] = None,
        conflict_value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs
        if conflict_field:
            context["conflict_field"] = conflict_field
        if conflict_value:
            context["conflict_value"] = conflict_value
        
        super().__init__(
            status_code=HTTPStatusCodes.CONFLICT,
            error_code="RESOURCE_CONFLICT",
            message=message,
            **context
        )


class BadRequestException(BaseAPIException):
    """Exception for bad request errors (400)."""
    
    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        **kwargs
    ):
        super().__init__(
            status_code=HTTPStatusCodes.BAD_REQUEST,
            error_code=error_code,
            message=message,
            **kwargs
        )


class UnauthorizedException(BaseAPIException):
    """Exception for unauthorized access (401)."""
    
    def __init__(
        self,
        message: str = "Unauthorized access",
        **kwargs
    ):
        super().__init__(
            status_code=HTTPStatusCodes.UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
            **kwargs
        )


class ForbiddenException(BaseAPIException):
    """Exception for forbidden access (403)."""
    
    def __init__(
        self,
        message: str = "Access forbidden",
        required_permission: Optional[str] = None,
        **kwargs
    ):
        context = kwargs
        if required_permission:
            context["required_permission"] = required_permission
        
        super().__init__(
            status_code=HTTPStatusCodes.FORBIDDEN,
            error_code="FORBIDDEN",
            message=message,
            **context
        )


class RateLimitException(BaseAPIException):
    """Exception for rate limit exceeded (429)."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            kwargs["retry_after"] = retry_after
        
        super().__init__(
            status_code=HTTPStatusCodes.TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            headers=headers,
            **kwargs
        )


class InternalServerException(BaseAPIException):
    """Exception for internal server errors (500)."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        error_id: Optional[str] = None,
        **kwargs
    ):
        context = kwargs
        if error_id:
            context["error_id"] = error_id
        
        super().__init__(
            status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
            **context
        )


class ServiceUnavailableException(BaseAPIException):
    """Exception for service unavailable errors (503)."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        headers = {}
        context = kwargs
        
        if retry_after:
            headers["Retry-After"] = str(retry_after)
            context["retry_after"] = retry_after
        
        if service_name:
            context["service_name"] = service_name
        
        super().__init__(
            status_code=HTTPStatusCodes.SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            headers=headers,
            **context
        )


class ExternalServiceException(BaseAPIException):
    """Exception for external service errors (502)."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: str = "external",
        original_error: Optional[str] = None,
        **kwargs
    ):
        context = kwargs
        context["service_name"] = service_name
        if original_error:
            context["original_error"] = original_error
        
        super().__init__(
            status_code=HTTPStatusCodes.BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            message=message,
            **context
        )


class NotImplementedException(BaseAPIException):
    """Exception for not implemented features (501)."""
    
    def __init__(
        self,
        message: str = "Feature not implemented",
        feature: Optional[str] = None,
        **kwargs
    ):
        context = kwargs
        if feature:
            context["feature"] = feature
        
        super().__init__(
            status_code=HTTPStatusCodes.NOT_IMPLEMENTED,
            error_code="NOT_IMPLEMENTED",
            message=message,
            **context
        )


# Business logic exceptions that map to HTTP errors
class BusinessLogicException(BaseAPIException):
    """Base exception for business logic errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_LOGIC_ERROR",
        status_code: int = HTTPStatusCodes.BAD_REQUEST,
        **kwargs
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            **kwargs
        )


class InvalidOperationException(BusinessLogicException):
    """Exception for invalid business operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        reason: Optional[str] = None,
        **kwargs
    ):
        context = kwargs
        context["operation"] = operation
        if reason:
            context["reason"] = reason
        
        super().__init__(
            message=message,
            error_code="INVALID_OPERATION",
            **context
        )


class ResourceLockedException(BusinessLogicException):
    """Exception for locked resource access attempts."""
    
    def __init__(
        self,
        resource: str,
        resource_id: str,
        locked_by: Optional[str] = None,
        locked_until: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource} '{resource_id}' is currently locked"
        context = kwargs
        context.update({
            "resource": resource,
            "resource_id": resource_id
        })
        
        if locked_by:
            context["locked_by"] = locked_by
        if locked_until:
            context["locked_until"] = locked_until
        
        super().__init__(
            message=message,
            error_code="RESOURCE_LOCKED",
            status_code=HTTPStatusCodes.CONFLICT,
            **context
        )


# Exception helper functions
def raise_not_found(resource: str, resource_id: Union[str, int]) -> None:
    """Convenience function to raise NotFoundException."""
    raise NotFoundException(resource=resource, resource_id=resource_id)


def raise_validation_error(
    message: str = "Validation failed",
    errors: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Convenience function to raise ValidationException."""
    raise ValidationException(message=message, errors=errors)


def raise_conflict(
    message: str,
    conflict_field: Optional[str] = None,
    conflict_value: Optional[Any] = None
) -> None:
    """Convenience function to raise ConflictException."""
    raise ConflictException(
        message=message,
        conflict_field=conflict_field,
        conflict_value=conflict_value
    )