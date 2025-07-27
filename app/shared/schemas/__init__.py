"""
Shared Pydantic schemas package.

Provides common response models and utilities used across all API endpoints.
"""

from .base import (
    BaseResponse,
    ErrorResponse,
    ErrorDetail,
    PaginatedResponse,
    PaginationMeta,
    HealthCheckResponse,
    ValidationErrorResponse,
    ResponseStatus,
    create_success_response,
    create_error_response,
    create_paginated_response
)

from .data import (
    DataCollectionResult
)

from .http_responses import (
    BadRequestResponse,
    UnauthorizedResponse,
    ForbiddenResponse,
    NotFoundResponse,
    ConflictResponse,
    RateLimitResponse,
    InternalServerErrorResponse,
    ServiceUnavailableResponse,
    COMMON_HTTP_RESPONSES,
    READ_ONLY_HTTP_RESPONSES,
    WRITE_HTTP_RESPONSES
)

__all__ = [
    # Base models
    "BaseResponse",
    "ErrorResponse", 
    "ErrorDetail",
    "PaginatedResponse",
    "PaginationMeta",
    "HealthCheckResponse",
    "ValidationErrorResponse",
    "ResponseStatus",
    
    # Legacy schemas
    "DataCollectionResult",
    
    # Utility functions
    "create_success_response",
    "create_error_response",
    "create_paginated_response",
    
    # HTTP specific responses
    "BadRequestResponse",
    "UnauthorizedResponse",
    "ForbiddenResponse",
    "NotFoundResponse",
    "ConflictResponse",
    "RateLimitResponse",
    "InternalServerErrorResponse",
    "ServiceUnavailableResponse",
    
    # Response dictionaries
    "COMMON_HTTP_RESPONSES",
    "READ_ONLY_HTTP_RESPONSES",
    "WRITE_HTTP_RESPONSES"
]