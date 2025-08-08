"""
User domain models for authentication and user management.

Supports both local authentication and Google OAuth 2.0 social login.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import re
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
    
    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        """한국 휴대폰 번호 형식 검증"""
        if v is None:
            return v
        # 한국 휴대폰 번호 패턴 (010-XXXX-XXXX 또는 01XXXXXXXXX)
        phone_pattern = r'^01[016789]-?\d{3,4}-?\d{4}$'
        if not re.match(phone_pattern, v.replace(' ', '').replace('-', '')):
            raise ValueError("올바른 휴대폰 번호 형식이 아닙니다 (010-XXXX-XXXX)")
        return v.replace(' ', '').replace('-', '')  # 정규화
    
    @field_validator('interests')
    def validate_interests(cls, v):
        """관심 분야는 최대 10개까지만 허용"""
        if len(v) > 10:
            raise ValueError("관심 분야는 최대 10개까지만 설정할 수 있습니다")
        # 각 관심 분야는 공백 제거 및 길이 제한
        cleaned = []
        for interest in v:
            if isinstance(interest, str):
                cleaned_interest = interest.strip()
                if len(cleaned_interest) > 50:
                    raise ValueError("각 관심 분야는 50자를 초과할 수 없습니다")
                if cleaned_interest:  # 빈 문자열 제거
                    cleaned.append(cleaned_interest)
        return cleaned


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
    
    # Timestamps (timezone-aware)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="계정 생성일")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="마지막 수정일")
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
    password: str = Field(..., min_length=8, max_length=128, description="비밀번호")
    consent_data_processing: bool = Field(True, description="개인정보 처리 동의")
    consent_marketing: bool = Field(False, description="마케팅 수신 동의")
    
    @field_validator('name')
    def validate_name(cls, v):
        """사용자 이름 검증"""
        if not v.strip():
            raise ValueError("사용자 이름은 공백만으로 구성될 수 없습니다")
        # 특수문자 제한 (한글, 영문, 숫자, 일부 특수문자만 허용)
        if not re.match(r'^[가-힣a-zA-Z0-9\s._-]+$', v):
            raise ValueError("사용자 이름에 허용되지 않는 문자가 포함되어 있습니다")
        return v.strip()
    
    @field_validator('consent_data_processing')
    def validate_required_consent(cls, v):
        """필수 동의사항 검증"""
        if not v:
            raise ValueError("개인정보 처리에 동의해야 회원가입이 가능합니다")
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        """비밀번호 보안 검증 (OWASP 가이드라인 기반)"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        if len(v) > 128:
            raise ValueError("비밀번호는 128자를 초과할 수 없습니다")
            
        # 기본적인 복잡성 요구사항 (너무 엄격하지 않게 조정)
        complexity_count = 0
        if any(c.isupper() for c in v):
            complexity_count += 1
        if any(c.islower() for c in v):
            complexity_count += 1
        if any(c.isdigit() for c in v):
            complexity_count += 1
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            complexity_count += 1
            
        if complexity_count < 3:  # 4가지 중 3가지 이상
            raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자 중 최소 3가지를 포함해야 합니다")
            
        # 일반적인 패턴 검사
        if v.lower() in ['password', '12345678', 'qwerty', 'admin', 'user']:
            raise ValueError("일반적인 패스워드는 사용할 수 없습니다")
            
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


# ===== User Settings (FE 요구 스키마와 정합) =====
class UserNotificationSettings(BaseModel):
    new_announcements: bool = Field(True, description="신규 공고 알림")
    deadline_reminder: bool = Field(True, description="마감 임박 알림")
    status_updates: bool = Field(True, description="상태 변경 알림")
    weekly_digest: bool = Field(False, description="주간 요약 메일")


class UserInterestSettings(BaseModel):
    primary_interest: Optional[str] = Field(None, description="주 관심 분야")
    additional_interests: List[str] = Field(default_factory=list, description="추가 관심 목록")


class UserLocationSettings(BaseModel):
    province: Optional[str] = Field(None, description="광역자치단체")
    city: Optional[str] = Field(None, description="기초자치단체")


class UserSettings(BaseModel):
    notifications: UserNotificationSettings = Field(default_factory=UserNotificationSettings)
    interests: UserInterestSettings = Field(default_factory=UserInterestSettings)
    location: UserLocationSettings = Field(default_factory=UserLocationSettings)


class UserSettingsUpdate(BaseModel):
    name: Optional[str] = Field(None, description="사용자 이름(선택, 프로필 동시 업데이트용)")
    notifications: Optional[UserNotificationSettings] = None
    interests: Optional[UserInterestSettings] = None
    location: Optional[UserLocationSettings] = None


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