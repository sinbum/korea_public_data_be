"""
User domain models for authentication and user management.

Supports both local authentication and Google OAuth 2.0 social login.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"


class UserProfile(BaseModel):
    """User profile information"""
    industry_code: Optional[str] = Field(None, description="업종 코드")
    startup_stage: Optional[str] = Field(None, description="창업 단계")
    region_code: Optional[str] = Field(None, description="지역 코드") 
    interests: List[str] = Field(default_factory=list, description="관심 분야 태그")
    business_type: Optional[str] = Field(None, description="사업 유형")
    company_name: Optional[str] = Field(None, description="회사명")
    position: Optional[str] = Field(None, description="직책")
    phone_number: Optional[str] = Field(None, description="연락처")
    
    @field_validator('interests')
    def validate_interests(cls, v):
        """관심 분야는 최대 10개까지만 허용"""
        if len(v) > 10:
            raise ValueError("관심 분야는 최대 10개까지만 설정할 수 있습니다")
        return v


class User(BaseModel):
    """User model supporting both local and OAuth authentication"""
    id: Optional[str] = Field(None, description="사용자 ID")
    email: EmailStr = Field(..., description="이메일 주소")
    name: str = Field(..., description="사용자 이름")
    password_hash: Optional[str] = Field(None, description="암호화된 비밀번호 (로컬 인증 시)")
    
    # OAuth fields
    provider: AuthProvider = Field(AuthProvider.LOCAL, description="인증 제공자")
    external_id: Optional[str] = Field(None, description="외부 제공자 사용자 ID")
    profile_image_url: Optional[str] = Field(None, description="프로필 이미지 URL")
    
    # Profile information
    profile: UserProfile = Field(default_factory=UserProfile, description="사용자 프로필")
    
    # Status and metadata
    is_active: bool = Field(True, description="계정 활성화 상태")
    is_verified: bool = Field(False, description="이메일 인증 상태")
    is_premium: bool = Field(False, description="프리미엄 사용자 여부")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="계정 생성일")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="마지막 수정일")
    last_login: Optional[datetime] = Field(None, description="마지막 로그인 시간")
    
    # GDPR compliance
    consent_marketing: bool = Field(False, description="마케팅 수신 동의")
    consent_data_processing: bool = Field(True, description="개인정보 처리 동의")
    
    class Config:
        populate_by_name = True


class UserCreate(BaseModel):
    """User creation schema for local registration"""
    email: EmailStr = Field(..., description="이메일 주소")
    name: str = Field(..., min_length=2, max_length=50, description="사용자 이름")
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호")
    consent_data_processing: bool = Field(True, description="개인정보 처리 동의")
    consent_marketing: bool = Field(False, description="마케팅 수신 동의")
    
    @field_validator('password')
    def validate_password(cls, v):
        """비밀번호 복잡성 검증"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호에는 대문자가 포함되어야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호에는 소문자가 포함되어야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에는 숫자가 포함되어야 합니다")
        return v


class SocialUserCreate(BaseModel):
    """User creation schema for OAuth social login"""
    email: EmailStr = Field(..., description="이메일 주소")
    name: str = Field(..., description="사용자 이름")
    provider: AuthProvider = Field(..., description="인증 제공자")
    external_id: str = Field(..., description="외부 제공자 사용자 ID")
    profile_image_url: Optional[str] = Field(None, description="프로필 이미지 URL")
    consent_data_processing: bool = Field(True, description="개인정보 처리 동의")


class UserUpdate(BaseModel):
    """User update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="사용자 이름")
    profile: Optional[UserProfile] = Field(None, description="프로필 정보")
    consent_marketing: Optional[bool] = Field(None, description="마케팅 수신 동의")


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")


class UserLoginRequest(BaseModel):
    """User login schema with remember flag for cookie-based auth"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")
    remember: bool = Field(False, description="로그인 유지 여부(쿠키 수명 연장)")


class UserResponse(BaseModel):
    """User response schema (excluding sensitive data)"""
    id: str = Field(..., description="사용자 ID")
    email: EmailStr = Field(..., description="이메일 주소")
    name: str = Field(..., description="사용자 이름")
    provider: AuthProvider = Field(..., description="인증 제공자")
    profile_image_url: Optional[str] = Field(None, description="프로필 이미지 URL")
    profile: UserProfile = Field(..., description="사용자 프로필")
    is_verified: bool = Field(..., description="이메일 인증 상태")
    is_premium: bool = Field(..., description="프리미엄 사용자 여부")
    created_at: datetime = Field(..., description="계정 생성일")
    last_login: Optional[datetime] = Field(None, description="마지막 로그인 시간")


class TokenResponse(BaseModel):
    """JWT token response schema"""
    access_token: str = Field(..., description="액세스 토큰")
    refresh_token: str = Field(..., description="리프레시 토큰")
    token_type: str = Field("bearer", description="토큰 타입")
    expires_in: int = Field(..., description="토큰 만료 시간 (초)")
    user: UserResponse = Field(..., description="사용자 정보")


class TokenRefresh(BaseModel):
    """Token refresh request schema"""
    refresh_token: str = Field(..., description="리프레시 토큰")


class AccountLinkRequest(BaseModel):
    """Account linking request schema"""
    password: str = Field(..., description="현재 계정 비밀번호 (보안 확인)")


class GoogleOAuthState(BaseModel):
    """Google OAuth state parameter for CSRF protection"""
    state: str = Field(..., description="CSRF 방지용 상태 값")
    redirect_url: Optional[str] = Field(None, description="로그인 후 리디렉션할 URL")