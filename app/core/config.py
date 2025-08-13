from typing import Optional
import secrets
from pydantic import Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    mongodb_url: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    database_name: str = Field(default="korea_public_api", min_length=1, description="MongoDB database name")
    
    # API Keys
    public_data_api_key: str = Field(..., min_length=10, description="Public data API key")
    
    # API Settings
    api_base_url: str = "https://apis.data.go.kr/B552735/kisedKstartupService01"
    api_version: str = "1.0.0"
    
    # App Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limit
    rl_per_minute: int = Field(default=60, gt=0, le=10000, description="Requests per minute limit")
    rl_per_hour: int = Field(default=1000, gt=0, le=100000, description="Requests per hour limit")
    
    # Logging
    log_level: str = "INFO"
    
    # JWT Authentication  
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), min_length=32, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", pattern=r"^HS256|HS384|HS512|RS256|RS384|RS512$", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=120, gt=0, le=1440, description="JWT access token expiry in minutes")
    jwt_refresh_token_expire_days: int = Field(default=7, gt=0, le=30, description="JWT refresh token expiry in days")
    
    # Google OAuth 2.0
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    # 개발/도커 경로는 API prefix(`/api/v1`) 포함 콜백 사용
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    google_scope: str = "openid email profile"
    
    # Frontend CORS
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend application URL")
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ],
        description="Allowed CORS origins (wildcards removed for security)"
    )
    
    # Development CORS (wildcards only in dev mode)
    cors_allow_dev_wildcards: bool = Field(default=True, description="Allow wildcard CORS patterns in development")
    # 보안 정책 토글: 블랙리스트 조회 실패 시 토큰 허용/거부
    # 환경변수와 연동 (없으면 기본 False)
    fail_close_on_blacklist_error: bool = Field(
        default_factory=lambda: (str(__import__('os').environ.get('FAIL_CLOSE_ON_BLACKLIST_ERROR', 'false')).lower() == 'true'),
        description="If true, deny tokens when blacklist check fails"
    )
    
    # CSRF 보호(더블 서브밋 토큰) 설정 - 기본 비활성화하여 FE 영향 없음
    csrf_enabled: bool = Field(
        default_factory=lambda: (str(__import__('os').environ.get('CSRF_ENABLED', 'false')).lower() == 'true'),
        description="Enable CSRF protection for state-changing requests"
    )
    csrf_cookie_name: str = Field(default="csrftoken", description="Cookie name for CSRF token")
    csrf_header_name: str = Field(default="X-CSRF-Token", description="Header name to carry CSRF token")

    # Alerts/Notifications Feature Flags & Config
    alerts_enabled: bool = Field(
        default_factory=lambda: (str(__import__('os').environ.get('ALERTS_ENABLED', 'false')).lower() == 'true'),
        description="Enable alerts/notifications feature (guards runtime impact)"
    )
    alerts_match_queue: str = Field(
        default_factory=lambda: str(__import__('os').environ.get('ALERTS_MATCH_QUEUE', 'alerts.match')),
        description="Celery queue name for matching tasks"
    )
    alerts_notify_queue: str = Field(
        default_factory=lambda: str(__import__('os').environ.get('ALERTS_NOTIFY_QUEUE', 'alerts.notify')),
        description="Celery queue name for delivery tasks"
    )
    alerts_digest_queue: str = Field(
        default_factory=lambda: str(__import__('os').environ.get('ALERTS_DIGEST_QUEUE', 'alerts.digest')),
        description="Celery queue name for digest tasks"
    )
    alerts_user_daily_cap: int = Field(
        default_factory=lambda: int(__import__('os').environ.get('ALERTS_USER_DAILY_CAP', '50')),
        gt=0,
        le=10000,
        description="Per-user daily delivery cap to protect system load"
    )
    alerts_global_rps: int = Field(
        default_factory=lambda: int(__import__('os').environ.get('ALERTS_GLOBAL_RPS', '20')),
        gt=0,
        le=10000,
        description="Global notifications send rate per second"
    )
    
    @validator('allowed_origins')
    def validate_origins(cls, v, values):
        """Validate CORS origins - no wildcards in production"""
        debug = values.get('debug', True)
        if not debug:
            # In production, reject wildcard patterns
            for origin in v:
                if '*' in origin:
                    raise ValueError(f"Wildcard CORS origins not allowed in production: {origin}")
        return v
    
    @validator('public_data_api_key')
    def validate_api_key(cls, v):
        """Validate API key format"""
        if not v or len(v.strip()) < 10:
            raise ValueError("API key must be at least 10 characters")
        return v.strip()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()