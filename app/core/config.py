from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "korea_public_api"
    
    # API Keys
    public_data_api_key: str
    
    # API Settings
    api_base_url: str = "https://apis.data.go.kr/B552735/kisedKstartupService01"
    api_version: str = "1.0.0"
    
    # App Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    
    # JWT Authentication
    jwt_secret_key: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # Google OAuth 2.0
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    google_scope: str = "openid email profile"
    
    # Frontend CORS
    frontend_url: str = "http://localhost:3000"
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://192.168.0.5:*",
        "http://192.168.0.7:*",
        "http://localhost:*"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()