"""
Authentication and user management API routes.

Provides endpoints for local authentication, Google OAuth 2.0 login,
user profile management, and token operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import (
    UserCreate, UserLogin, UserUpdate, UserResponse, 
    TokenResponse, TokenRefresh, AccountLinkRequest
)
from .service import UserService
from ...shared.clients.google_oauth_client import google_oauth_client
from ...core.dependencies import get_service_dependency

# Router setup
router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer()

# Dependency injection
get_user_service = get_service_dependency(UserService)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    user_service: UserService = Depends(get_user_service)
):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    return await user_service.get_current_user(token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user with email and password
    
    - **email**: Valid email address
    - **name**: User's full name (2-50 characters)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, number)
    - **consent_data_processing**: Must be true for GDPR compliance
    - **consent_marketing**: Optional marketing consent
    """
    return await user_service.register_local_user(user_create)


@router.post("/login", response_model=TokenResponse)
async def login(
    user_login: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticate user with email and password
    
    - **email**: Registered email address
    - **password**: User's password
    
    Returns JWT access token (15 min) and refresh token (7 days)
    """
    return await user_service.login_local_user(user_login)


@router.get("/google/login")
async def google_login(
    redirect_url: Optional[str] = None
):
    """
    Initiate Google OAuth 2.0 login flow
    
    - **redirect_url**: Optional URL to redirect after authentication
    
    Redirects to Google OAuth consent screen
    """
    try:
        oauth_data = google_oauth_client.get_authorization_url(
            redirect_url=redirect_url
        )
        return {
            "authorization_url": oauth_data["authorization_url"],
            "state": oauth_data["state"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth 초기화 실패: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Handle Google OAuth 2.0 callback
    
    - **code**: Authorization code from Google
    - **state**: State parameter for CSRF protection
    
    Creates or authenticates user and returns JWT tokens
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code가 없습니다"
        )
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter가 없습니다"
        )
    
    return await user_service.google_oauth_login(code, state)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_refresh: TokenRefresh,
    user_service: UserService = Depends(get_user_service)
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token pair
    """
    return await user_service.refresh_token(token_refresh.refresh_token)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    refresh_token: Optional[str] = None,
    user_service: UserService = Depends(get_user_service)
):
    """
    Logout user by blacklisting tokens
    
    - **Authorization header**: Bearer access token
    - **refresh_token**: Optional refresh token to blacklist
    
    Adds tokens to blacklist to prevent further use
    """
    access_token = credentials.credentials
    success = await user_service.logout(access_token, refresh_token)
    
    if success:
        return {"message": "로그아웃되었습니다"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다"
        )


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user = Depends(get_current_user)
):
    """
    Get current user profile
    
    Requires valid access token in Authorization header
    """
    from .service import UserService
    user_service = UserService()
    return user_service._to_user_response(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user profile
    
    - **name**: Update user's name
    - **profile**: Update user profile information
    - **consent_marketing**: Update marketing consent
    
    Requires valid access token in Authorization header
    """
    return await user_service.update_user_profile(current_user.id, user_update)


@router.post("/link-google")
async def link_google_account(
    link_request: AccountLinkRequest,
    current_user = Depends(get_current_user)
):
    """
    Link Google account to existing local account
    
    - **password**: Current account password for security verification
    
    Requires valid access token and correct password
    """
    # Verify current password
    from ...core.security import verify_password
    if not current_user.password_hash or not verify_password(
        link_request.password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다"
        )
    
    # Generate Google OAuth URL for linking
    oauth_data = google_oauth_client.get_authorization_url(
        redirect_url="/auth/link-google/callback"
    )
    
    return {
        "authorization_url": oauth_data["authorization_url"],
        "state": oauth_data["state"],
        "message": "Google 계정 연결을 위해 인증을 진행해주세요"
    }


@router.delete("/unlink-google")
async def unlink_google_account(
    current_user = Depends(get_current_user)
):
    """
    Unlink Google account from current account
    
    Requires valid access token
    """
    # Check if user has Google account linked
    if not current_user.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="연결된 Google 계정이 없습니다"
        )
    
    # Unlink Google account
    user_service = UserService()
    success = user_service.user_repository.unlink_google_account(current_user.id)
    if success:
        return {"message": "Google 계정 연결이 해제되었습니다"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google 계정 연결 해제에 실패했습니다"
        )


@router.delete("/account")
async def delete_account(
    current_user = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete user account (GDPR compliance)
    
    Permanently deletes user account and all associated data
    Requires valid access token
    """
    success = await user_service.delete_user_account(current_user.id)
    if success:
        return {"message": "계정이 삭제되었습니다"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 삭제에 실패했습니다"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current authenticated user information
    
    Alias for /profile endpoint
    """
    from .service import UserService
    user_service = UserService()
    return user_service._to_user_response(current_user)


@router.get("/status")
async def auth_status():
    """
    Check authentication status without requiring token
    
    Returns authentication status and available auth methods
    """
    return {
        "authenticated": False,
        "available_methods": ["local", "google"],
        "google_oauth_enabled": bool(google_oauth_client.client_id),
        "endpoints": {
            "register": "/auth/register",
            "login": "/auth/login",
            "google_login": "/auth/google/login",
            "refresh": "/auth/refresh",
            "logout": "/auth/logout"
        }
    }


@router.post("/test-register")
async def test_register(data: dict):
    """Test endpoint to isolate the issue"""
    try:
        # Create a minimal UserCreate directly
        from pydantic import BaseModel, Field, EmailStr
        
        class TestUserCreate(BaseModel):
            email: EmailStr = Field(..., description="이메일 주소")
            name: str = Field(..., min_length=2, max_length=50, description="사용자 이름")
            password: str = Field(..., min_length=8, max_length=100, description="비밀번호")
            consent_data_processing: bool = Field(True, description="개인정보 처리 동의")
            consent_marketing: bool = Field(False, description="마케팅 수신 동의")
        
        # Try to create instance
        test_user = TestUserCreate(**data)
        
        return {
            "message": "Minimal UserCreate works",
            "data": test_user.model_dump()
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "type": type(e).__name__, "traceback": traceback.format_exc()}


@router.post("/test-simple")
async def test_simple(data: dict):
    """Test endpoint without Pydantic models"""
    return {"message": "Simple endpoint works", "received": data}

@router.post("/test-clean")
async def test_clean():
    """Completely clean endpoint with no dependencies"""
    return {"message": "Clean endpoint works", "timestamp": "2025-01-01T00:00:00Z"}