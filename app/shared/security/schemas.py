"""
Security schemas for API authentication and authorization.

Defines FastAPI security schemas for future authentication implementation.
Currently documented for OpenAPI specification only.
"""

from fastapi import Header, Depends
from fastapi.security import HTTPBearer, HTTPBasic, APIKeyHeader, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AuthScope(str, Enum):
    """Available authentication scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FETCH = "fetch"  # For data collection operations


class APIKeyType(str, Enum):
    """API key types."""
    HEADER = "header"
    QUERY = "query"


# Security schemes for OpenAPI documentation
# These will be used when authentication is implemented

# JWT Bearer Token Authentication (planned)
jwt_bearer = HTTPBearer(
    scheme_name="JWT Bearer",
    description="""
    JWT Bearer Token 인증 (계획됨)
    
    **사용법:**
    1. `/auth/login` 엔드포인트로 로그인
    2. 받은 JWT 토큰을 Authorization 헤더에 포함
    3. 형식: `Authorization: Bearer <your-jwt-token>`
    
    **토큰 만료:** 24시간
    **갱신:** `/auth/refresh` 엔드포인트 사용
    """,
    auto_error=False  # Don't raise error automatically for documentation
)

# API Key Authentication (planned)
api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key",
    description="""
    API Key 인증 (계획됨)
    
    **사용법:**
    1. 관리자 페이지에서 API 키 발급
    2. HTTP 헤더에 포함: `X-API-Key: <your-api-key>`
    
    **권한:** 읽기 전용 액세스
    **Rate Limiting:** 시간당 1,000회 요청
    """,
    auto_error=False
)

# OAuth2 Password Flow (planned)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scheme_name="OAuth2 Password",
    description="""
    OAuth2 패스워드 플로우 (계획됨)
    
    **지원 스코프:**
    - `read`: 데이터 읽기 권한
    - `write`: 데이터 쓰기 권한  
    - `admin`: 관리자 권한
    - `fetch`: 데이터 수집 권한
    """,
    scopes={
        "read": "데이터 읽기 권한",
        "write": "데이터 생성/수정 권한",
        "admin": "시스템 관리 권한",
        "fetch": "외부 데이터 수집 권한"
    },
    auto_error=False
)

# Basic Authentication (for admin only, planned)
basic_auth = HTTPBasic(
    scheme_name="Basic Auth",
    description="""
    HTTP Basic 인증 (관리자 전용, 계획됨)
    
    **사용법:**
    - 관리자 계정으로만 접근 가능
    - 형식: `Authorization: Basic <base64(username:password)>`
    
    **제한사항:** 관리 API에서만 사용
    """,
    auto_error=False
)


class TokenData(BaseModel):
    """JWT token data model."""
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_token": "def502004f8c7c4...",
                "scope": ["read", "write"]
            }
        }
    }
    
    access_token: str = Field(
        ...,
        description="JWT 액세스 토큰",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="토큰 타입",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="토큰 만료 시간 (초)",
        example=86400
    )
    refresh_token: Optional[str] = Field(
        None,
        description="갱신 토큰",
        example="def502004f8c7c4..."
    )
    scope: list[str] = Field(
        [],
        description="허용된 권한 범위",
        example=["read", "write"]
    )


class UserCredentials(BaseModel):
    """User login credentials."""
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "password": "secure_password123"
            }
        }
    }
    
    username: str = Field(
        ...,
        description="사용자명",
        example="admin",
        min_length=3,
        max_length=50
    )
    password: str = Field(
        ...,
        description="비밀번호",
        example="secure_password123",
        min_length=8,
        max_length=100
    )


class APIKeyRequest(BaseModel):
    """API key creation request."""
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My App API Key",
                "description": "API key for my application integration",
                "scopes": ["read"],
                "expires_in_days": 365
            }
        }
    }
    
    name: str = Field(
        ...,
        description="API 키 이름",
        example="My App API Key",
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="API 키 설명",
        example="API key for my application integration",
        max_length=500
    )
    scopes: list[str] = Field(
        ["read"],
        description="허용할 권한 범위",
        example=["read"]
    )
    expires_in_days: Optional[int] = Field(
        365,
        description="만료 기간 (일)",
        example=365,
        ge=1,
        le=3650
    )


class APIKeyResponse(BaseModel):
    """API key creation response."""
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "key_12345678",
                "name": "My App API Key",
                "key": "sk-1234567890abcdef1234567890abcdef",
                "scopes": ["read"],
                "created_at": "2025-07-27T00:00:00Z",
                "expires_at": "2026-07-27T00:00:00Z",
                "is_active": True
            }
        }
    }
    
    id: str = Field(
        ...,
        description="API 키 ID",
        example="key_12345678"
    )
    name: str = Field(
        ...,
        description="API 키 이름",
        example="My App API Key"
    )
    key: str = Field(
        ...,
        description="API 키 값 (한 번만 표시)",
        example="sk-1234567890abcdef1234567890abcdef"
    )
    scopes: list[str] = Field(
        ...,
        description="허용된 권한 범위",
        example=["read"]
    )
    created_at: str = Field(
        ...,
        description="생성 일시",
        example="2025-07-27T00:00:00Z"
    )
    expires_at: Optional[str] = Field(
        None,
        description="만료 일시",
        example="2026-07-27T00:00:00Z"
    )
    is_active: bool = Field(
        True,
        description="활성 상태",
        example=True
    )


# Dependency functions for future authentication implementation
async def get_current_user_optional():
    """
    Optional authentication dependency.
    Returns None if no authentication provided.
    """
    # TODO: Implement when authentication is added
    return None


async def get_current_user():
    """
    Required authentication dependency.
    Raises 401 if no valid authentication provided.
    """
    # TODO: Implement when authentication is added
    # For now, allow all requests (development mode)
    return {"user_id": "anonymous", "scopes": ["read"]}


async def require_scope(required_scope: str):
    """
    Scope-based authorization dependency.
    """
    def scope_checker():
        # TODO: Implement when authentication is added
        return True
    return scope_checker


async def require_api_key():
    """
    API key authentication dependency.
    """
    # TODO: Implement when authentication is added
    return True


# Security configuration for OpenAPI schema
SECURITY_SCHEMES = {
    "JWT": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT Bearer Token 인증 (계획됨)"
    },
    "APIKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API Key 인증 (계획됨)"
    },
    "OAuth2": {
        "type": "oauth2",
        "flows": {
            "password": {
                "tokenUrl": "/auth/token",
                "scopes": {
                    "read": "데이터 읽기 권한",
                    "write": "데이터 생성/수정 권한",
                    "admin": "시스템 관리 권한",
                    "fetch": "외부 데이터 수집 권한"
                }
            }
        },
        "description": "OAuth2 패스워드 플로우 (계획됨)"
    },
    "Basic": {
        "type": "http",
        "scheme": "basic",
        "description": "HTTP Basic 인증 - 관리자 전용 (계획됨)"
    }
}