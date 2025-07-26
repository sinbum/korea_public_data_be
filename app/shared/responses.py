"""
Standard HTTP response formats and status code system.

Provides consistent response structures and status code handling
for all API endpoints following RESTful best practices.
"""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from fastapi import status
from fastapi.responses import JSONResponse

# Type variable for generic responses
T = TypeVar('T')


class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel, Generic[T]):
    """
    Standard base response format for all API endpoints.
    
    Provides a consistent structure with success indicator,
    data payload, message, and optional metadata.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "Request processed successfully",
                "timestamp": "2024-01-25T12:00:00Z"
            }
        }
    )
    
    success: bool = Field(..., description="Indicates if the request was successful")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Response timestamp in ISO format"
    )
    status: ResponseStatus = Field(
        default=ResponseStatus.SUCCESS,
        description="Response status indicator"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata (request ID, version, etc.)"
    )


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field name for validation errors")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Used for all error responses including validation errors,
    business logic errors, and system errors.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "errors": [
                    {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid input data",
                        "field": "email",
                        "context": {"value": "invalid-email"}
                    }
                ],
                "message": "Request failed due to validation errors",
                "timestamp": "2024-01-25T12:00:00Z",
                "request_id": "req_123456"
            }
        }
    )
    
    success: bool = Field(default=False, description="Always false for errors")
    errors: List[ErrorDetail] = Field(..., description="List of error details")
    message: str = Field(..., description="Summary error message")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Error timestamp"
    )
    status: ResponseStatus = Field(
        default=ResponseStatus.ERROR,
        description="Always 'error' for error responses"
    )
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    error_type: Optional[str] = Field(None, description="Error classification")


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors."""
    error_type: str = Field(default="VALIDATION_ERROR")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    size: int = Field(..., description="Items per page", ge=1, le=100)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response format for list endpoints.
    
    Provides consistent pagination structure with items,
    pagination metadata, and standard response fields.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "items": [{"id": "1", "name": "Item 1"}],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "size": 20,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False
                },
                "message": "Items retrieved successfully",
                "timestamp": "2024-01-25T12:00:00Z"
            }
        }
    )
    
    success: bool = Field(default=True)
    items: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Applied filters for reference"
    )


class CreatedResponse(BaseModel, Generic[T]):
    """Response format for resource creation (201 Created)."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": "new_123", "name": "New Resource"},
                "message": "Resource created successfully",
                "location": "/api/v1/resources/new_123",
                "timestamp": "2024-01-25T12:00:00Z"
            }
        }
    )
    
    success: bool = Field(default=True)
    data: T = Field(..., description="Created resource data")
    message: str = Field(default="Resource created successfully")
    location: str = Field(..., description="Location of the created resource")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)


class UpdatedResponse(BaseModel, Generic[T]):
    """Response format for resource updates."""
    success: bool = Field(default=True)
    data: T = Field(..., description="Updated resource data")
    message: str = Field(default="Resource updated successfully")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    modified_fields: Optional[List[str]] = Field(
        None,
        description="List of fields that were modified"
    )


class DeletedResponse(BaseModel):
    """Response format for resource deletion."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Resource deleted successfully",
                "deleted_id": "123",
                "timestamp": "2024-01-25T12:00:00Z"
            }
        }
    )
    
    success: bool = Field(default=True)
    message: str = Field(default="Resource deleted successfully")
    deleted_id: str = Field(..., description="ID of the deleted resource")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)


class NoContentResponse(BaseModel):
    """Response format for 204 No Content (typically for updates/deletes)."""
    # This is typically empty but included for consistency
    pass


# HTTP Status Code Mapping
class HTTPStatusCodes:
    """
    Standard HTTP status code mappings for consistent API responses.
    
    Maps business logic outcomes to appropriate HTTP status codes
    following RESTful conventions.
    """
    
    # Success codes (2xx)
    OK = status.HTTP_200_OK  # GET success
    CREATED = status.HTTP_201_CREATED  # POST success
    ACCEPTED = status.HTTP_202_ACCEPTED  # Async operation accepted
    NO_CONTENT = status.HTTP_204_NO_CONTENT  # DELETE/PUT success with no body
    
    # Client error codes (4xx)
    BAD_REQUEST = status.HTTP_400_BAD_REQUEST  # Invalid request format
    UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED  # Missing/invalid auth
    FORBIDDEN = status.HTTP_403_FORBIDDEN  # Authenticated but not authorized
    NOT_FOUND = status.HTTP_404_NOT_FOUND  # Resource not found
    METHOD_NOT_ALLOWED = status.HTTP_405_METHOD_NOT_ALLOWED  # Wrong HTTP method
    CONFLICT = status.HTTP_409_CONFLICT  # Resource conflict (duplicate)
    UNPROCESSABLE_ENTITY = status.HTTP_422_UNPROCESSABLE_ENTITY  # Validation error
    TOO_MANY_REQUESTS = status.HTTP_429_TOO_MANY_REQUESTS  # Rate limit exceeded
    
    # Server error codes (5xx)
    INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR  # Generic server error
    NOT_IMPLEMENTED = status.HTTP_501_NOT_IMPLEMENTED  # Feature not implemented
    BAD_GATEWAY = status.HTTP_502_BAD_GATEWAY  # External service error
    SERVICE_UNAVAILABLE = status.HTTP_503_SERVICE_UNAVAILABLE  # Service down
    GATEWAY_TIMEOUT = status.HTTP_504_GATEWAY_TIMEOUT  # External service timeout


# Response factory functions
def success_response(
    data: Any = None,
    message: str = "Request processed successfully",
    status_code: int = HTTPStatusCodes.OK,
    **kwargs
) -> JSONResponse:
    """
    Create a standard success response.
    
    Args:
        data: Response data payload
        message: Success message
        status_code: HTTP status code (default 200)
        **kwargs: Additional response fields
        
    Returns:
        JSONResponse with standard format
    """
    response = BaseResponse(
        success=True,
        data=data,
        message=message,
        status=ResponseStatus.SUCCESS,
        **kwargs
    )
    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=status_code
    )


def error_response(
    errors: List[Union[ErrorDetail, Dict[str, Any]]],
    message: str = "Request failed",
    status_code: int = HTTPStatusCodes.BAD_REQUEST,
    **kwargs
) -> JSONResponse:
    """
    Create a standard error response.
    
    Args:
        errors: List of error details
        message: Error summary message
        status_code: HTTP status code (default 400)
        **kwargs: Additional response fields
        
    Returns:
        JSONResponse with error format
    """
    # Convert dict errors to ErrorDetail objects
    error_details = []
    for error in errors:
        if isinstance(error, dict):
            error_details.append(ErrorDetail(**error))
        else:
            error_details.append(error)
    
    response = ErrorResponse(
        success=False,
        errors=error_details,
        message=message,
        status=ResponseStatus.ERROR,
        **kwargs
    )
    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=status_code
    )


def validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed"
) -> JSONResponse:
    """
    Create a validation error response.
    
    Args:
        errors: List of validation errors
        message: Validation error message
        
    Returns:
        JSONResponse with 422 status
    """
    return error_response(
        errors=errors,
        message=message,
        status_code=HTTPStatusCodes.UNPROCESSABLE_ENTITY,
        error_type="VALIDATION_ERROR"
    )


def not_found_response(
    resource: str,
    resource_id: str,
    message: Optional[str] = None
) -> JSONResponse:
    """
    Create a not found error response.
    
    Args:
        resource: Resource type (e.g., "announcement")
        resource_id: Resource identifier
        message: Custom message (optional)
        
    Returns:
        JSONResponse with 404 status
    """
    default_message = f"{resource} with id '{resource_id}' not found"
    return error_response(
        errors=[{
            "code": "RESOURCE_NOT_FOUND",
            "message": message or default_message,
            "context": {"resource": resource, "id": resource_id}
        }],
        message=message or default_message,
        status_code=HTTPStatusCodes.NOT_FOUND,
        error_type="NOT_FOUND"
    )


def created_response(
    data: Any,
    location: str,
    message: str = "Resource created successfully"
) -> JSONResponse:
    """
    Create a resource creation success response.
    
    Args:
        data: Created resource data
        location: Location of the created resource
        message: Success message
        
    Returns:
        JSONResponse with 201 status
    """
    response = CreatedResponse(
        data=data,
        location=location,
        message=message
    )
    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=HTTPStatusCodes.CREATED,
        headers={"Location": location}
    )


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    size: int,
    message: str = "Items retrieved successfully",
    **kwargs
) -> JSONResponse:
    """
    Create a paginated list response.
    
    Args:
        items: List of items
        total: Total count of items
        page: Current page number
        size: Items per page
        message: Success message
        **kwargs: Additional response fields
        
    Returns:
        JSONResponse with pagination metadata
    """
    total_pages = (total + size - 1) // size if size > 0 else 0
    
    pagination_meta = PaginationMeta(
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    response = PaginatedResponse(
        items=items,
        pagination=pagination_meta,
        message=message,
        **kwargs
    )
    
    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        status_code=HTTPStatusCodes.OK
    )