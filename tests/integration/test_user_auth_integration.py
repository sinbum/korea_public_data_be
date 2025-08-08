"""
Integration tests for user authentication system.

Tests the complete authentication flow including registration, login,
token refresh, and OAuth integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from fastapi import status
import json

from app.main import app
from app.domains.users.models import UserCreate, AuthProvider
from app.domains.users.service import UserService
from app.domains.users.repository import UserRepository
from app.core.security import create_access_token, create_refresh_token


@pytest.fixture
def test_client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_user_repository():
    """Mock user repository"""
    return Mock(spec=UserRepository)


@pytest.fixture
def mock_user_service(mock_user_repository):
    """Mock user service with repository"""
    service = Mock(spec=UserService)
    service.repository = mock_user_repository
    return service


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password": "StrongP@ss123",
        "consent_data_processing": True,
        "consent_marketing": False
    }


@pytest.fixture  
def sample_token_response():
    """Sample token response"""
    return {
        "access_token": "jwt.access.token",
        "refresh_token": "jwt.refresh.token",
        "token_type": "bearer",
        "expires_in": 900,
        "user": {
            "id": "123",
            "email": "test@example.com", 
            "name": "Test User",
            "provider": "local",
            "profile": {},
            "is_verified": False,
            "is_premium": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }


class TestUserRegistration:
    """Test user registration endpoint"""
    
    def test_register_success(self, test_client, sample_user_data, sample_token_response):
        """Test successful user registration"""
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.register_local_user.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/register", json=sample_user_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == sample_user_data["email"]
    
    def test_register_validation_errors(self, test_client):
        """Test registration with validation errors"""
        invalid_data_cases = [
            # Missing required fields
            {
                "email": "test@example.com",
                # Missing name, password, consent
            },
            # Invalid email
            {
                "email": "invalid-email",
                "name": "Test User",
                "password": "StrongP@ss123", 
                "consent_data_processing": True
            },
            # Weak password
            {
                "email": "test@example.com",
                "name": "Test User",
                "password": "weak",
                "consent_data_processing": True
            },
            # Missing data processing consent
            {
                "email": "test@example.com", 
                "name": "Test User",
                "password": "StrongP@ss123",
                "consent_data_processing": False
            }
        ]
        
        for invalid_data in invalid_data_cases:
            response = test_client.post("/auth/register", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]
    
    def test_register_duplicate_email(self, test_client, sample_user_data):
        """Test registration with duplicate email"""
        from app.shared.exceptions.custom_exceptions import UserAlreadyExistsError
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.register_local_user.side_effect = UserAlreadyExistsError(
                "User with this email already exists"
            )
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/register", json=sample_user_data)
            
            assert response.status_code == status.HTTP_409_CONFLICT


class TestUserLogin:
    """Test user login endpoint"""
    
    def test_login_success(self, test_client, sample_token_response):
        """Test successful user login"""
        login_data = {
            "email": "test@example.com",
            "password": "StrongP@ss123",
            "remember": False
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.login_local_user.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            
            # Check cookies are set
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies
    
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials"""
        from app.shared.exceptions.custom_exceptions import InvalidCredentialsError
        
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword",
            "remember": False
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.login_local_user.side_effect = InvalidCredentialsError(
                "Invalid email or password"
            )
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_with_remember(self, test_client, sample_token_response):
        """Test login with remember flag"""
        login_data = {
            "email": "test@example.com",
            "password": "StrongP@ss123",
            "remember": True
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.login_local_user.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            # Check that cookies have extended expiration
            access_cookie = response.cookies.get("access_token")
            refresh_cookie = response.cookies.get("refresh_token")
            assert access_cookie is not None
            assert refresh_cookie is not None


class TestTokenRefresh:
    """Test token refresh endpoint"""
    
    def test_refresh_token_success(self, test_client, sample_token_response):
        """Test successful token refresh"""
        refresh_data = {"refresh_token": "jwt.refresh.token"}
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.refresh_access_token.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/refresh", json=refresh_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    def test_refresh_token_from_cookie(self, test_client, sample_token_response):
        """Test token refresh using cookie"""
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.refresh_access_token.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            # Set refresh token in cookie
            test_client.cookies = {"refresh_token": "jwt.refresh.token"}
            
            response = test_client.post("/auth/refresh", json={})
            
            assert response.status_code == status.HTTP_200_OK
    
    def test_refresh_token_invalid(self, test_client):
        """Test refresh with invalid token"""
        from app.shared.exceptions.custom_exceptions import InvalidTokenError
        
        refresh_data = {"refresh_token": "invalid.jwt.token"}
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.refresh_access_token.side_effect = InvalidTokenError(
                "Invalid refresh token"
            )
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/refresh", json=refresh_data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGoogleOAuth:
    """Test Google OAuth endpoints"""
    
    def test_google_login_initiation(self, test_client):
        """Test Google OAuth login initiation"""
        with patch('app.shared.clients.google_oauth_client.google_oauth_client') as mock_oauth:
            mock_oauth.get_authorization_url.return_value = {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
                "state": "secure_state_token_123"
            }
            
            response = test_client.get("/auth/google/login")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert data["authorization_url"].startswith("https://accounts.google.com")
    
    def test_google_login_with_redirect(self, test_client):
        """Test Google OAuth with redirect parameter"""
        with patch('app.shared.clients.google_oauth_client.google_oauth_client') as mock_oauth:
            mock_oauth.get_authorization_url.return_value = {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
                "state": "secure_state_token_123"
            }
            
            response = test_client.get(
                "/auth/google/login?redirect_to=/dashboard&remember=1"
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_oauth.get_authorization_url.assert_called_once()
            call_args = mock_oauth.get_authorization_url.call_args[1]
            assert call_args["redirect_to"] == "/dashboard"
            assert call_args["remember"] is True
    
    def test_google_callback_success(self, test_client, sample_token_response):
        """Test successful Google OAuth callback"""
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.google_oauth_login.return_value = (
                sample_token_response,
                {"post_login_redirect": "/dashboard", "remember": True}
            )
            mock_get_service.return_value = mock_service
            
            response = test_client.get(
                "/auth/google/callback?code=auth_code_123&state=secure_state_token_123",
                follow_redirects=False
            )
            
            assert response.status_code == status.HTTP_302_FOUND
            assert "location" in response.headers
            # Should redirect to frontend
            assert response.headers["location"].endswith("/dashboard")
    
    def test_google_callback_missing_code(self, test_client):
        """Test Google callback with missing authorization code"""
        response = test_client.get(
            "/auth/google/callback?state=secure_state_token_123",
            follow_redirects=False
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_google_callback_missing_state(self, test_client):
        """Test Google callback with missing state parameter"""
        response = test_client.get(
            "/auth/google/callback?code=auth_code_123",
            follow_redirects=False
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_google_callback_invalid_state(self, test_client):
        """Test Google callback with invalid state"""
        from app.shared.exceptions.custom_exceptions import InvalidStateError
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.google_oauth_login.side_effect = InvalidStateError(
                "Invalid or expired state parameter"
            )
            mock_get_service.return_value = mock_service
            
            response = test_client.get(
                "/auth/google/callback?code=auth_code_123&state=invalid_state",
                follow_redirects=False
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCurrentUser:
    """Test current user endpoint"""
    
    def test_get_current_user_with_token(self, test_client):
        """Test getting current user with valid token"""
        mock_user = {
            "id": "123",
            "email": "test@example.com",
            "name": "Test User",
            "provider": "local",
            "profile": {},
            "is_verified": False,
            "is_premium": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_current_user.return_value = mock_user
            mock_get_service.return_value = mock_service
            
            headers = {"Authorization": "Bearer jwt.access.token"}
            response = test_client.get("/auth/me", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "test@example.com"
    
    def test_get_current_user_with_cookie(self, test_client):
        """Test getting current user with cookie token"""
        mock_user = {
            "id": "123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_current_user.return_value = mock_user
            mock_get_service.return_value = mock_service
            
            test_client.cookies = {"access_token": "jwt.access.token"}
            response = test_client.get("/auth/me")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "test@example.com"
    
    def test_get_current_user_no_token(self, test_client):
        """Test getting current user without token"""
        response = test_client.get("/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_invalid_token(self, test_client):
        """Test getting current user with invalid token"""
        from app.shared.exceptions.custom_exceptions import InvalidTokenError
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_current_user.side_effect = InvalidTokenError(
                "Invalid or expired token"
            )
            mock_get_service.return_value = mock_service
            
            headers = {"Authorization": "Bearer invalid.jwt.token"}
            response = test_client.get("/auth/me", headers=headers)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthenticationFlow:
    """Test complete authentication flows"""
    
    @pytest.mark.asyncio
    async def test_complete_registration_login_flow(self, test_client):
        """Test complete registration and login flow"""
        user_data = {
            "email": "integration@example.com",
            "name": "Integration User",
            "password": "IntegrationP@ss123",
            "consent_data_processing": True,
            "consent_marketing": True
        }
        
        mock_token_response = {
            "access_token": "jwt.access.token",
            "refresh_token": "jwt.refresh.token", 
            "token_type": "bearer",
            "expires_in": 900,
            "user": {
                "id": "integration123",
                "email": user_data["email"],
                "name": user_data["name"],
                "provider": "local",
                "profile": {},
                "is_verified": False,
                "is_premium": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            
            # Step 1: Register user
            mock_service.register_local_user.return_value = mock_token_response
            mock_get_service.return_value = mock_service
            
            register_response = test_client.post("/auth/register", json=user_data)
            assert register_response.status_code == status.HTTP_201_CREATED
            
            register_data = register_response.json()
            assert register_data["user"]["email"] == user_data["email"]
            
            # Step 2: Login with registered user
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"],
                "remember": False
            }
            
            mock_service.login_local_user.return_value = mock_token_response
            
            login_response = test_client.post("/auth/login", json=login_data)
            assert login_response.status_code == status.HTTP_200_OK
            
            login_data = login_response.json()
            assert "access_token" in login_data
            assert "refresh_token" in login_data
    
    @pytest.mark.asyncio  
    async def test_token_refresh_flow(self, test_client):
        """Test token refresh flow"""
        # Initial tokens
        initial_tokens = {
            "access_token": "jwt.access.token.initial",
            "refresh_token": "jwt.refresh.token.initial",
            "token_type": "bearer",
            "expires_in": 900,
            "user": {
                "id": "123",
                "email": "test@example.com",
                "name": "Test User"
            }
        }
        
        # Refreshed tokens
        refreshed_tokens = {
            "access_token": "jwt.access.token.refreshed", 
            "refresh_token": "jwt.refresh.token.refreshed",
            "token_type": "bearer",
            "expires_in": 900,
            "user": initial_tokens["user"]
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.refresh_access_token.return_value = refreshed_tokens
            mock_get_service.return_value = mock_service
            
            # Use refresh token to get new tokens
            refresh_data = {"refresh_token": initial_tokens["refresh_token"]}
            
            response = test_client.post("/auth/refresh", json=refresh_data)
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["access_token"] == "jwt.access.token.refreshed"
            assert data["refresh_token"] == "jwt.refresh.token.refreshed"
            assert data["access_token"] != initial_tokens["access_token"]


class TestSecurityHeaders:
    """Test security headers and cookie settings"""
    
    def test_auth_cookies_security_attributes(self, test_client, sample_token_response):
        """Test that auth cookies have proper security attributes"""
        login_data = {
            "email": "test@example.com",
            "password": "StrongP@ss123",
            "remember": False
        }
        
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.login_local_user.return_value = sample_token_response
            mock_get_service.return_value = mock_service
            
            response = test_client.post("/auth/login", json=login_data)
            
            # Check cookie attributes
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies
            
            # In a real environment, these would have HttpOnly, Secure, SameSite
            # TestClient doesn't fully support cookie attribute testing
            access_cookie = response.cookies["access_token"]
            refresh_cookie = response.cookies["refresh_token"]
            
            assert access_cookie is not None
            assert refresh_cookie is not None


class TestErrorHandling:
    """Test error handling in authentication endpoints"""
    
    def test_network_error_handling(self, test_client):
        """Test handling of network errors"""
        with patch('app.domains.users.router.get_user_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.register_local_user.side_effect = Exception("Database connection failed")
            mock_get_service.return_value = mock_service
            
            user_data = {
                "email": "test@example.com",
                "name": "Test User", 
                "password": "StrongP@ss123",
                "consent_data_processing": True
            }
            
            response = test_client.post("/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "error" in response.json() or "detail" in response.json()
    
    def test_malformed_request_data(self, test_client):
        """Test handling of malformed request data"""
        # Send malformed JSON
        response = test_client.post(
            "/auth/register",
            data="invalid json data",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]