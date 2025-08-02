"""
User service for authentication and user management.

Handles both local authentication and Google OAuth 2.0 integration,
providing unified user management capabilities.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status

from .models import (
    User, UserCreate, SocialUserCreate, UserUpdate, UserLogin,
    UserResponse, TokenResponse, AuthProvider
)
from .repository import UserRepository
from ...core.security import (
    verify_password, get_password_hash, create_token_pair,
    verify_token, blacklist_token
)
from ...shared.clients.google_oauth_client import google_oauth_client


class UserService:
    """Service layer for user authentication and management"""

    def __init__(self, user_repository: UserRepository = None):
        self.user_repository = user_repository or UserRepository()

    async def register_local_user(self, user_create: UserCreate) -> TokenResponse:
        """
        Register a new local user with email and password

        Args:
            user_create: User registration data

        Returns:
            JWT tokens and user information

        Raises:
            HTTPException: If email already exists or registration fails
        """
        # Check if email already exists
        existing_user = self.user_repository.get_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일 주소입니다"
            )

        # Hash password
        password_hash = get_password_hash(user_create.password)

        # Create user
        user = self.user_repository.create_local_user(user_create, password_hash)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="사용자 등록에 실패했습니다"
            )

        # Generate tokens
        user_data = {"sub": user.id, "email": user.email, "provider": user.provider.value}
        tokens = create_token_pair(user_data)

        # Update last login
        self.user_repository.update_last_login(user.id)

        return TokenResponse(
            **tokens,
            user=self._to_user_response(user)
        )

    async def login_local_user(self, user_login: UserLogin) -> TokenResponse:
        """
        Authenticate local user with email and password

        Args:
            user_login: Login credentials

        Returns:
            JWT tokens and user information

        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user by email
        user = self.user_repository.get_by_email(user_login.email)
        if not user or user.provider != AuthProvider.LOCAL:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )

        # Verify password
        if not user.password_hash or not verify_password(user_login.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다"
            )

        # Generate tokens
        user_data = {"sub": user.id, "email": user.email, "provider": user.provider.value}
        tokens = create_token_pair(user_data)

        # Update last login
        self.user_repository.update_last_login(user.id)

        return TokenResponse(
            **tokens,
            user=self._to_user_response(user)
        )

    async def google_oauth_login(self, code: str, state: str) -> TokenResponse:
        """
        Handle Google OAuth login callback

        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection

        Returns:
            JWT tokens and user information

        Raises:
            HTTPException: If OAuth flow fails
        """
        try:
            # Exchange code for tokens and user info
            oauth_data = await google_oauth_client.exchange_code_for_tokens(code, state)
            if not oauth_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google 인증에 실패했습니다"
                )

            user_info = oauth_data["user_info"]

            # Check if user already exists by Google ID
            existing_user = self.user_repository.get_by_provider_and_external_id(
                AuthProvider.GOOGLE, user_info["external_id"]
            )

            if existing_user:
                # Existing Google user - update info and login
                user = await self._update_google_user_info(existing_user, user_info)
            else:
                # Check if user exists with same email (different provider)
                email_user = self.user_repository.get_by_email(user_info["email"])
                if email_user and email_user.provider == AuthProvider.LOCAL:
                    # Link Google account to existing local account
                    success = self.user_repository.link_google_account(
                        email_user.id,
                        user_info["external_id"],
                        user_info.get("picture")
                    )
                    if not success:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="계정 연결에 실패했습니다"
                        )
                    user = self.user_repository.get_by_id(email_user.id)
                else:
                    # Create new Google user
                    user = await self._create_google_user(user_info)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="사용자 생성에 실패했습니다"
                )

            # Generate tokens
            user_data = {"sub": user.id, "email": user.email, "provider": user.provider.value}
            tokens = create_token_pair(user_data)

            # Update last login
            self.user_repository.update_last_login(user.id)

            return TokenResponse(
                **tokens,
                user=self._to_user_response(user)
            )

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="로그인 처리 중 오류가 발생했습니다"
            )

    async def _create_google_user(self, user_info: Dict[str, Any]) -> Optional[User]:
        """Create new user from Google OAuth info"""
        social_user = SocialUserCreate(
            email=user_info["email"],
            name=user_info["name"],
            provider=AuthProvider.GOOGLE,
            external_id=user_info["external_id"],
            profile_image_url=user_info.get("picture"),
            consent_data_processing=True
        )

        return self.user_repository.create_social_user(social_user)

    async def _update_google_user_info(self, user: User, user_info: Dict[str, Any]) -> User:
        """Update existing user's Google profile info"""
        # Update user info if needed
        update_data = {}

        if user.name != user_info["name"]:
            update_data["name"] = user_info["name"]

        if user.profile_image_url != user_info.get("picture"):
            update_data["profile_image_url"] = user_info.get("picture")

        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            from bson import ObjectId
            self.user_repository.collection.update_one(
                {"_id": ObjectId(user.id)},
                {"$set": update_data}
            )
            # Refresh user data
            return self.user_repository.get_by_id(user.id)

        return user

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New JWT tokens

        Raises:
            HTTPException: If refresh token is invalid
        """
        # Verify refresh token
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 리프레시 토큰입니다"
            )

        # Get user
        user_id = payload.get("sub")
        user = self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )

        # Generate new tokens
        user_data = {"sub": user.id, "email": user.email, "provider": user.provider.value}
        tokens = create_token_pair(user_data)

        # Blacklist old refresh token
        blacklist_token(refresh_token)

        return TokenResponse(
            **tokens,
            user=self._to_user_response(user)
        )

    async def logout(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Logout user by blacklisting tokens

        Args:
            access_token: Access token to blacklist
            refresh_token: Optional refresh token to blacklist

        Returns:
            True if logout successful
        """
        try:
            # Blacklist access token
            blacklist_token(access_token)

            # Blacklist refresh token if provided
            if refresh_token:
                blacklist_token(refresh_token)

            return True
        except Exception:
            return False

    async def get_current_user(self, token: str) -> User:
        """
        Get current user from JWT token

        Args:
            token: JWT access token

        Returns:
            Current user

        Raises:
            HTTPException: If token is invalid or user not found
        """
        # Verify token
        payload = verify_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 액세스 토큰입니다"
            )

        # Get user
        user_id = payload.get("sub")
        user = self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )

        return user

    async def update_user_profile(self, user_id: str, user_update: UserUpdate) -> UserResponse:
        """
        Update user profile

        Args:
            user_id: User ID
            user_update: Profile update data

        Returns:
            Updated user information

        Raises:
            HTTPException: If update fails
        """
        user = self.user_repository.update_user(user_id, user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )

        return self._to_user_response(user)

    async def delete_user_account(self, user_id: str) -> bool:
        """
        Delete user account (GDPR compliance)

        Args:
            user_id: User ID to delete

        Returns:
            True if deletion successful
        """
        return self.user_repository.delete_user(user_id)

    def _to_user_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse (exclude sensitive data)"""
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            provider=user.provider,
            profile_image_url=user.profile_image_url,
            profile=user.profile,
            is_verified=user.is_verified,
            is_premium=user.is_premium,
            created_at=user.created_at,
            last_login=user.last_login
        )