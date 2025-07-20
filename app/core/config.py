from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()