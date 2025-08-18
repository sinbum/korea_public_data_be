"""
Authentication and user management API routes.

Provides endpoints for local authentication, Google OAuth 2.0 login,
user profile management, and token operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
import logging
import time

from .models import (
    UserCreate, UserLogin, UserLoginRequest, UserUpdate, UserResponse, 
    TokenResponse, TokenRefresh, AccountLinkRequest
)
from .service import UserService
from ...shared.clients.google_oauth_client import google_oauth_client
from ...core.dependencies import get_service_dependency
from ...core.config import settings
from ...core.constants import HTTPStatusMessages, TokenConstants, OAuthConstants
from urllib.parse import urlparse
import secrets

# Router setup
router = APIRouter(
    prefix="/auth", 
    tags=["Authentication"],
    responses={
        400: {"description": "Bad request - validation error"},
        401: {"description": "Unauthorized - invalid credentials"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Not found - user not found"},
        409: {"description": "Conflict - user already exists"},
        422: {"description": "Validation error - invalid input data"},
        500: {"description": "Internal server error"}
    }
)
security_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

# Dependency injection
get_user_service = get_service_dependency(UserService)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    access_token_cookie: Optional[str] = Cookie(default=None, alias="access_token"),
    user_service: UserService = Depends(get_user_service)
):
    """Dependency to get current authenticated user (Authorization header or HttpOnly cookie)"""
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif access_token_cookie:
        token = access_token_cookie
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=HTTPStatusMessages.TOKEN_REQUIRED
        )

    return await user_service.get_current_user(token)


@router.post("/register", 
    response_model=TokenResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user with email and password authentication",
    responses={
        201: {"description": "User successfully registered", "model": TokenResponse},
        409: {"description": "User already exists with this email"},
        422: {"description": "Validation error - check password requirements"}
    }
)
async def register(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user with email and password
    
    **Required Fields:**
    - **email**: Valid email address (must be unique)
    - **name**: User's full name (2-50 characters, Korean/English supported)
    - **password**: Strong password meeting security requirements:
        - Minimum 8 characters, maximum 128 characters
        - Must include 3 of 4 character types: uppercase, lowercase, numbers, special characters
        - Cannot be common passwords (password, 12345678, etc.)
    - **consent_data_processing**: Must be true for GDPR compliance
    
    **Optional Fields:**
    - **consent_marketing**: Marketing email consent (default: false)
    
    **Returns:**
    - Access token (15 minutes validity)
    - Refresh token (7 days validity)
    - User profile information
    """
    try:
        result = await user_service.register_local_user(user_create)
        logger.info(f"User registered successfully: {user_create.email}")
        return result
    except ValidationError as e:
        logger.warning(f"Validation error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=HTTPStatusMessages.VALIDATION_ERROR
        ) from e  # Preserve exception chain for better debugging
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is to preserve status codes
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=HTTPStatusMessages.REGISTRATION_ERROR
        ) from e


@router.post("/login", 
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user with email and password",
    responses={
        200: {"description": "Login successful", "model": TokenResponse},
        401: {"description": "Invalid credentials"},
        404: {"description": "User not found"}
    }
)
async def login(
    user_login: UserLoginRequest,
    response: Response,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticate user with email and password
    
    **Required Fields:**
    - **email**: Registered email address
    - **password**: User's password
    - **remember**: Remember login (extends cookie expiration)
    
    **Security Features:**
    - Rate limiting protection
    - Secure HTTP-only cookies for web clients
    - JWT tokens for API clients
    - Automatic last login timestamp update
    
    **Returns:**
    - Access token (15 minutes validity)
    - Refresh token (7 days validity, 30 days if remember=true)
    - User profile information
    
    **Headers Set:**
    - Set-Cookie: access_token (HTTP-only, Secure)
    - Set-Cookie: refresh_token (HTTP-only, Secure)
    """
    # Extract client info once for better performance
    client_ip = getattr(request.client, 'host', 'unknown') if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Log login attempt (without password for security)
        logger.info(f"Login attempt: {user_login.email} from {client_ip}")
        
        # Create UserLogin object once to avoid redundant instantiation
        login_data = UserLogin(email=user_login.email, password=user_login.password)
        result = await user_service.login_local_user(login_data)
        
        # Set cookies and log success
        _set_auth_cookies(response, result.access_token, result.refresh_token, 
                         remember=user_login.remember)
        logger.info(f"Login successful: {user_login.email} from {client_ip}")
        return result
        
    except HTTPException as e:
        logger.warning(f"Login failed: {user_login.email} from {client_ip} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=HTTPStatusMessages.LOGIN_ERROR
        ) from e


@router.get("/google/login",
    summary="Google OAuth login",
    description="Initiate Google OAuth 2.0 authentication flow",
    responses={
        200: {
            "description": "OAuth URL generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
                        "state": "secure_random_state_token"
                    }
                }
            }
        },
        500: {"description": "OAuth initialization failed"}
    }
)
async def google_login(
    request: Request,
    redirect_to: Optional[str] = None,
    remember: Optional[int] = None,
):
    """
    Initiate Google OAuth 2.0 login flow
    
    **Parameters:**
    - **redirect_to**: Optional URL to redirect after successful authentication (relative paths only)
    - **remember**: Set to 1 for extended session (30 days instead of 7 days)
    
    **Security Features:**
    - CSRF protection via state parameter
    - Secure state storage with expiration
    - URL validation to prevent open redirect attacks
    
    **Returns:**
    - **authorization_url**: Google OAuth consent screen URL
    - **state**: CSRF protection token (store this for callback validation)
    
    **Usage:**
    1. Call this endpoint to get authorization URL
    2. Redirect user to the authorization URL
    3. Google will redirect back to /auth/google/callback with code and state
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Log OAuth initiation with detailed info
        logger.info(f"Google OAuth login initiated from {client_ip} | User-Agent: {user_agent[:100]}...")
        
        # Validate redirect_to parameter
        if redirect_to:
            parsed = urlparse(redirect_to)
            if parsed.scheme in ['http', 'https']:  # Prevent open redirects
                redirect_to = parsed.path or '/'
                logger.warning(f"OAuth redirect sanitized: {redirect_to}")
        
        # Generate OAuth data
        oauth_start_time = time.time()
        oauth_data = google_oauth_client.get_authorization_url(
            redirect_to=redirect_to,
            remember=(remember == 1) if remember is not None else None,
        )
        oauth_time = time.time() - oauth_start_time
        
        total_time = time.time() - start_time
        
        logger.info(f"Google OAuth URL generated successfully in {oauth_time:.3f}s (total: {total_time:.3f}s) for {client_ip}")
        
        return {
            "authorization_url": oauth_data["authorization_url"],
            "state": oauth_data["state"]
        }
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Google OAuth initialization failed after {total_time:.3f}s for {client_ip}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {e}")
        
        # Return more specific error information
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth 초기화 실패: {str(e)}"
        )


@router.get("/google/callback",
    summary="Google OAuth callback",
    description="Handle Google OAuth 2.0 authorization callback",
    responses={
        302: {"description": "Successful authentication, redirect to frontend"},
        400: {"description": "Missing or invalid authorization code/state"},
        401: {"description": "OAuth authentication failed"},
        500: {"description": "OAuth processing error"}
    }
)
async def google_callback(
    code: str,
    state: str,
    response: Response,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Handle Google OAuth 2.0 callback and complete authentication
    
    **Query Parameters:**
    - **code**: Authorization code from Google (required)
    - **state**: CSRF protection token from initial request (required)
    
    **Process:**
    1. Validates authorization code and state parameter
    2. Exchanges code for Google access token
    3. Fetches user profile from Google
    4. Creates new user or authenticates existing user
    5. Sets secure HTTP-only cookies
    6. Redirects to frontend with authentication cookies
    
    **Security Features:**
    - CSRF protection via state validation
    - Secure cookie settings (HTTP-only, Secure, SameSite)
    - Open redirect protection
    - State parameter cleanup after use
    
    **Automatic Redirect:**
    - Redirects to frontend URL specified in initial request
    - Fallback to homepage if no redirect specified
    - Relative paths only for security
    """
    client_ip = request.client.host if request.client else "unknown"
    
    if not code:
        logger.warning(f"Google OAuth callback missing code from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code가 없습니다"
        )
    
    if not state:
        logger.warning(f"Google OAuth callback missing state from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter가 없습니다"
        )
    
    try:
        logger.info(f"Processing Google OAuth callback from {client_ip}")
    
        # Perform login
        token_result, state_data = await user_service.google_oauth_login(code, state)
        logger.info(f"Google OAuth login successful for user: {token_result.user.email}")

        # Choose cookie persistence by state.remember (default True for OAuth)
        remember_flag = True
        if state_data and isinstance(state_data, dict):
            remember_value = state_data.get("remember")
            if isinstance(remember_value, bool):
                remember_flag = remember_value

        # Determine redirect target (security: relative paths only)
        redirect_target = "/"
        if state_data and isinstance(state_data, dict):
            redirect_candidate = state_data.get("post_login_redirect")
            if isinstance(redirect_candidate, str) and len(redirect_candidate) > 0:
                redirect_target = redirect_candidate

        # Normalize redirect (prevent open redirect attacks)
        if isinstance(redirect_target, str) and redirect_target.startswith("http"):
            path = urlparse(redirect_target).path or "/"
            redirect_target = path
            logger.info(f"OAuth redirect sanitized to: {redirect_target}")

        # Build final redirect URL
        frontend_base = settings.frontend_url.rstrip("/") if isinstance(settings.frontend_url, str) else ""
        path_only = redirect_target if isinstance(redirect_target, str) and redirect_target.startswith("/") else f"/{redirect_target}"
        final_redirect_url = f"{frontend_base}{path_only}"

        from fastapi.responses import RedirectResponse
        redirect_response = RedirectResponse(url=final_redirect_url, status_code=302)
        _set_auth_cookies(redirect_response, token_result.access_token, token_result.refresh_token, remember=remember_flag)
        
        logger.info(f"Google OAuth redirect to: {final_redirect_url}")
        return redirect_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth 처리 중 오류가 발생했습니다"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_refresh: Optional[TokenRefresh] = None,
    request: Request = None,
    response: Response = None,
    user_service: UserService = Depends(get_user_service)
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token pair
    """
    refresh_token_str: Optional[str] = None
    if token_refresh and token_refresh.refresh_token:
        refresh_token_str = token_refresh.refresh_token
    else:
        refresh_token_str = request.cookies.get("refresh_token") if request else None

    if not refresh_token_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="리프레시 토큰이 없습니다")

    result = await user_service.refresh_token(refresh_token_str)
    _set_auth_cookies(response, result.access_token, result.refresh_token, remember=True)
    return result


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    refresh_token: Optional[str] = None,
    user_service: UserService = Depends(get_user_service)
):
    """
    Logout user by blacklisting tokens
    
    - **Authorization header**: Bearer access token
    - **refresh_token**: Optional refresh token to blacklist
    
    Adds tokens to blacklist to prevent further use
    """
    # Extract tokens once for better performance
    access_token = credentials.credentials if credentials else request.cookies.get("access_token")
    refresh_token_value = refresh_token or request.cookies.get("refresh_token")
    
    try:
        success = await user_service.logout(access_token, refresh_token_value)
        
        if success:
            _clear_auth_cookies(response)
            return {"message": HTTPStatusMessages.LOGOUT_SUCCESS}
        else:
            # Log the specific reason for logout failure
            logger.warning(f"Logout failed for token: {access_token[:10] if access_token else 'None'}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTPStatusMessages.INVALID_TOKEN
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=HTTPStatusMessages.LOGOUT_ERROR
        ) from e


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


@router.get("/settings")
async def get_user_settings(
    current_user = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current user's settings (notifications/interests/location)
    """
    return await user_service.get_user_settings(current_user.id)


@router.put("/settings")
async def update_user_settings(
    settings_update: dict,
    current_user = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update current user's settings
    """
    logger.info(f"📤 Settings update request for user {current_user.id}")
    logger.info(f"📋 Raw settings data: {settings_update}")
    
    try:
        from .models import UserSettingsUpdate
        update_model = UserSettingsUpdate(**settings_update)
        logger.info(f"✅ Parsed settings model: {update_model}")
        
        result = await user_service.update_user_settings(current_user.id, update_model)
        logger.info(f"🎯 Settings update result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Settings update failed: {e}")
        raise


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


# Helpers for cookie-based auth
def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, remember: bool = True):
    """Set authentication cookies with improved constants usage"""
    access_max_age = TokenConstants.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    refresh_max_age = (
        TokenConstants.REFRESH_TOKEN_REMEMBER_DAYS if remember 
        else TokenConstants.REFRESH_TOKEN_EXPIRE_DAYS
    ) * 24 * 60 * 60

    # Compute cookie attributes based on frontend URL (cross-site in prod)
    secure = False
    samesite = "lax"
    cookie_domain = None
    try:
        fe = str(settings.frontend_url)
        u = urlparse(fe)
        host = u.hostname
        if host and host not in TokenConstants.COOKIE_SECURE_HOSTS:
            secure = True
            samesite = "none"  # cross-site cookie for separate FE domain
            cookie_domain = host
    except Exception:
        pass
    # Set access token cookie
    response.set_cookie(
        key=TokenConstants.ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=access_max_age,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path=TokenConstants.COOKIE_PATH,
        domain=cookie_domain,
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key=TokenConstants.REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path=TokenConstants.COOKIE_PATH,
        domain=cookie_domain,
    )

    # CSRF 토큰 쿠키(옵션): 서버 설정에 따라 발급
    try:
        if getattr(settings, "csrf_enabled", False):
            csrf_token = secrets.token_urlsafe(32)
            response.set_cookie(
                key=getattr(settings, "csrf_cookie_name", "csrftoken"),
                value=csrf_token,
                max_age=refresh_max_age,
                httponly=False,  # 프론트에서 읽어 헤더 전송
                samesite=samesite,
                secure=secure,
                path="/",
                domain=cookie_domain,
            )
    except Exception:
        pass


def _clear_auth_cookies(response: Response):
    # Use same domain attributes as set
    cookie_domain = None
    try:
        fe = str(settings.frontend_url)
        u = urlparse(fe)
        host = u.hostname
        if host and host not in ("localhost", "127.0.0.1"):
            cookie_domain = host
    except Exception:
        pass
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key=key, path="/", domain=cookie_domain)


import os


@router.post("/test-register")
async def test_register(data: dict):
    """Test endpoint to isolate the issue"""
    # 노출 제한: 테스트/디버그 환경에서만 사용
    if not (os.getenv("TESTING") == "1" or settings.debug):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
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
    if not (os.getenv("TESTING") == "1" or settings.debug):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"message": "Simple endpoint works", "received": data}

@router.post("/test-clean")
async def test_clean():
    """Completely clean endpoint with no dependencies"""
    return {"message": "Clean endpoint works", "timestamp": "2025-01-01T00:00:00Z"}