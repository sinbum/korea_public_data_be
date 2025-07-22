"""
Shared exceptions for the Korea Public API platform.

Defines custom exception classes for different error scenarios.
"""

from .api_exceptions import *
from .auth_exceptions import *
from .data_exceptions import *

__all__ = [
    # API Exceptions
    'KoreanPublicAPIError',
    'APIClientError', 
    'APITimeoutError',
    'APIRateLimitError',
    'APIServerError',
    'APINotFoundError',
    'APIBadRequestError',
    'APIResponseError',
    
    # Authentication Exceptions
    'AuthenticationError',
    'APIKeyError',
    'TokenExpiredError',
    'InsufficientPermissionsError',
    
    # Data Exceptions
    'DataValidationError',
    'DataTransformationError',
    'DataParsingError',
    'DataSourceError'
]