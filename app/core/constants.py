"""
Application-wide constants for improved maintainability.

Centralizes magic numbers, strings, and configuration values
used throughout the authentication and user management system.
"""

from enum import Enum


class HTTPStatusMessages:
    """HTTP status code messages for consistent error handling"""
    VALIDATION_ERROR = "입력 데이터 유효성 검사 실패"
    REGISTRATION_ERROR = "회원가입 처리 중 오류가 발생했습니다"
    LOGIN_ERROR = "로그인 처리 중 오류가 발생했습니다"
    LOGOUT_ERROR = "로그아웃 처리 중 오류가 발생했습니다"
    LOGOUT_SUCCESS = "로그아웃되었습니다"
    INVALID_TOKEN = "유효하지 않은 토큰입니다"
    TOKEN_REQUIRED = "인증 토큰이 없습니다"
    
    # OAuth specific messages
    OAUTH_INIT_ERROR = "Google OAuth 초기화 실패"
    OAUTH_CALLBACK_ERROR = "Google OAuth 처리 중 오류가 발생했습니다"
    OAUTH_CODE_MISSING = "Authorization code가 없습니다"
    OAUTH_STATE_MISSING = "State parameter가 없습니다"


class TokenConstants:
    """Token-related constants"""
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    REFRESH_TOKEN_REMEMBER_DAYS = 30
    TOKEN_TYPE = "bearer"
    
    # Cookie names
    ACCESS_TOKEN_COOKIE = "access_token"
    REFRESH_TOKEN_COOKIE = "refresh_token"
    
    # Cookie settings
    COOKIE_PATH = "/"
    COOKIE_SECURE_HOSTS = ["localhost", "127.0.0.1"]


class ValidationConstants:
    """Validation-related constants"""
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 50
    PASSWORD_COMPLEXITY_REQUIRED = 3  # Out of 4 character types
    
    # User profile limits
    MAX_INTERESTS = 10
    MAX_INTEREST_LENGTH = 50
    
    # Phone number pattern
    KOREAN_PHONE_PATTERN = r'^01[016789]-?\d{3,4}-?\d{4}$'


class OAuthConstants:
    """OAuth-related constants"""
    GOOGLE_PROVIDER = "google"
    LOCAL_PROVIDER = "local"
    
    # OAuth flow parameters
    OAUTH_STATE_EXPIRY_SECONDS = 600  # 10 minutes
    OAUTH_REDIRECT_TIMEOUT_SECONDS = 30


class LoggingConstants:
    """Logging-related constants"""
    MAX_LOG_LENGTH = 100  # For truncating sensitive data in logs
    SENSITIVE_FIELDS = ["password", "token", "secret", "key"]


class APIConstants:
    """API-related constants"""
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    API_VERSION = "v1"
    BASE_API_PREFIX = "/api/v1"
    
    # Rate limiting
    DEFAULT_RATE_LIMIT_PER_MINUTE = 60
    DEFAULT_RATE_LIMIT_PER_HOUR = 1000


class DatabaseConstants:
    """Database-related constants"""
    USER_COLLECTION = "users"
    TOKEN_BLACKLIST_COLLECTION = "token_blacklist"
    USER_SETTINGS_COLLECTION = "user_settings"


class SecurityConstants:
    """Security-related constants"""
    BCRYPT_ROUNDS = 12
    JWT_ALGORITHM = "HS256"
    
    # Password validation
    PASSWORD_COMMON_PATTERNS = [
        'password', '12345678', 'qwerty', 'admin', 'user'
    ]
    
    # Password complexity requirements
    class PasswordRequirement(Enum):
        UPPERCASE = "uppercase"
        LOWERCASE = "lowercase"
        DIGIT = "digit"
        SPECIAL = "special"


# Export commonly used constants for convenience
__all__ = [
    'HTTPStatusMessages',
    'TokenConstants', 
    'ValidationConstants',
    'OAuthConstants',
    'LoggingConstants',
    'APIConstants',
    'DatabaseConstants',
    'SecurityConstants'
]