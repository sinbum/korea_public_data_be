"""
API-related exception classes for Korean Public Data APIs.

Provides hierarchical exception structure for different API error scenarios.
"""

from typing import Optional, Dict, Any
import httpx


class KoreanPublicAPIError(Exception):
    """Base exception for all Korean Public API errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class APIClientError(KoreanPublicAPIError):
    """General API client error"""
    pass


class APITimeoutError(APIClientError):
    """API request timeout error"""
    
    def __init__(self, message: str = "API request timed out", timeout_duration: Optional[float] = None):
        super().__init__(message, status_code=408)
        self.timeout_duration = timeout_duration


class APIRateLimitError(APIClientError):
    """API rate limit exceeded error"""
    
    def __init__(
        self, 
        message: str = "API rate limit exceeded", 
        retry_after: Optional[int] = None,
        limit_type: str = "requests"
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        self.limit_type = limit_type


class APIServerError(APIClientError):
    """API server error (5xx status codes)"""
    
    def __init__(self, message: str, status_code: int = 500, is_retryable: bool = True):
        super().__init__(message, status_code=status_code)
        self.is_retryable = is_retryable


class APINotFoundError(APIClientError):
    """API endpoint or resource not found (404)"""
    
    def __init__(self, message: str = "API endpoint not found", endpoint: Optional[str] = None):
        super().__init__(message, status_code=404)
        self.endpoint = endpoint


class APIBadRequestError(APIClientError):
    """Bad request error (400)"""
    
    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400)
        self.validation_errors = validation_errors or {}


class APIResponseError(APIClientError):
    """Error in API response format or content"""
    
    def __init__(
        self, 
        message: str, 
        response_content: Optional[str] = None,
        expected_format: Optional[str] = None
    ):
        super().__init__(message)
        self.response_content = response_content
        self.expected_format = expected_format


class NetworkError(APIClientError):
    """Network connectivity error"""
    
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


def create_api_exception_from_response(response: httpx.Response) -> KoreanPublicAPIError:
    """
    Create appropriate exception from httpx Response.
    
    Args:
        response: httpx Response object
        
    Returns:
        Appropriate API exception based on status code
    """
    status_code = response.status_code
    content = response.text[:500]  # Limit content for logging
    
    if status_code == 400:
        return APIBadRequestError(f"Bad request: {content}")
    elif status_code == 401:
        from .auth_exceptions import AuthenticationError
        return AuthenticationError(f"Authentication failed: {content}")
    elif status_code == 403:
        from .auth_exceptions import InsufficientPermissionsError
        return InsufficientPermissionsError(f"Insufficient permissions: {content}")
    elif status_code == 404:
        return APINotFoundError(f"Resource not found: {content}")
    elif status_code == 408:
        return APITimeoutError(f"Request timeout: {content}")
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
        return APIRateLimitError(f"Rate limit exceeded: {content}", retry_after=retry_after_int)
    elif 500 <= status_code < 600:
        is_retryable = status_code in [500, 502, 503, 504]  # Retryable server errors
        return APIServerError(f"Server error: {content}", status_code=status_code, is_retryable=is_retryable)
    else:
        return APIClientError(f"HTTP {status_code}: {content}", status_code=status_code)


def create_network_exception_from_httpx_error(error: Exception) -> NetworkError:
    """
    Create NetworkError from httpx exceptions.
    
    Args:
        error: Original httpx exception
        
    Returns:
        NetworkError with appropriate message
    """
    error_type = type(error).__name__
    
    if isinstance(error, httpx.TimeoutException):
        return NetworkError(f"Request timed out: {str(error)}", error)
    elif isinstance(error, httpx.ConnectError):
        return NetworkError(f"Connection failed: {str(error)}", error)
    elif isinstance(error, httpx.ReadTimeout):
        return NetworkError(f"Read timeout: {str(error)}", error)
    elif isinstance(error, httpx.WriteTimeout):
        return NetworkError(f"Write timeout: {str(error)}", error)
    elif isinstance(error, httpx.PoolTimeout):
        return NetworkError(f"Connection pool timeout: {str(error)}", error)
    else:
        return NetworkError(f"Network error ({error_type}): {str(error)}", error)