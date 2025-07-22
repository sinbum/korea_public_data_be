"""
Authentication-related exception classes.

Handles various authentication and authorization error scenarios.
"""

from .api_exceptions import KoreanPublicAPIError


class AuthenticationError(KoreanPublicAPIError):
    """Base authentication error"""
    
    def __init__(self, message: str = "Authentication failed", auth_type: str = "unknown"):
        super().__init__(message, status_code=401)
        self.auth_type = auth_type


class APIKeyError(AuthenticationError):
    """API key related errors"""
    
    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, auth_type="api_key")


class TokenExpiredError(AuthenticationError):
    """Token expiration error"""
    
    def __init__(self, message: str = "Authentication token has expired", token_type: str = "bearer"):
        super().__init__(message, auth_type="token")
        self.token_type = token_type


class InsufficientPermissionsError(KoreanPublicAPIError):
    """Insufficient permissions error"""
    
    def __init__(
        self, 
        message: str = "Insufficient permissions for this operation",
        required_permission: str = None
    ):
        super().__init__(message, status_code=403)
        self.required_permission = required_permission