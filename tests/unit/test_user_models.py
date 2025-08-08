"""
Unit tests for user models and validation.

Tests Pydantic model validation, field constraints, and business logic
for user-related data structures.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.domains.users.models import (
    User, UserCreate, SocialUserCreate, UserUpdate, UserLogin, UserLoginRequest,
    UserProfile, AuthProvider, UserResponse, TokenResponse, TokenRefresh,
    UserSettings, UserNotificationSettings, UserInterestSettings, UserLocationSettings
)


class TestUserProfile:
    """Test UserProfile model validation"""
    
    def test_user_profile_valid(self):
        """Test valid user profile creation"""
        profile = UserProfile(
            industry_code="IT001",
            startup_stage="growth",
            region_code="SEOUL01",
            interests=["AI", "blockchain", "fintech"],
            business_type="B2B",
            company_name="Test Corp",
            position="CTO",
            phone_number="01012345678"
        )
        
        assert profile.industry_code == "IT001"
        assert len(profile.interests) == 3
        assert profile.phone_number == "01012345678"
    
    def test_user_profile_interests_validation(self):
        """Test interests field validation"""
        # Valid case: under limit
        profile = UserProfile(interests=["AI", "blockchain"])
        assert len(profile.interests) == 2
        
        # Invalid case: too many interests
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(interests=[f"interest{i}" for i in range(15)])  # 15 > 10 limit
        
        assert "최대 10개까지만" in str(exc_info.value)
    
    def test_user_profile_interests_cleaning(self):
        """Test interests are cleaned and validated"""
        # Test with whitespace and empty strings
        profile = UserProfile(interests=["  AI  ", "", "blockchain", "   ", "fintech"])
        
        # Should clean whitespace and remove empty strings
        assert "AI" in profile.interests
        assert "blockchain" in profile.interests
        assert "fintech" in profile.interests
        assert "" not in profile.interests
        assert "   " not in profile.interests
    
    def test_user_profile_interests_length_limit(self):
        """Test individual interest length limit"""
        # Valid case
        profile = UserProfile(interests=["AI"])
        assert profile.interests == ["AI"]
        
        # Invalid case: interest too long
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(interests=["a" * 60])  # 60 > 50 limit
        
        assert "50자를 초과할 수 없습니다" in str(exc_info.value)
    
    def test_user_profile_phone_validation(self):
        """Test Korean phone number validation"""
        # Valid phone numbers
        valid_phones = [
            "01012345678",
            "010-1234-5678",
            "010 1234 5678",
            "01087654321",
            "01612345678",
            "01712345678",
            "01812345678",
            "01912345678"
        ]
        
        for phone in valid_phones:
            profile = UserProfile(phone_number=phone)
            # Should normalize to digits only
            assert profile.phone_number == phone.replace("-", "").replace(" ", "")
        
        # Invalid phone numbers
        invalid_phones = [
            "02012345678",  # Not mobile
            "01012",        # Too short
            "010123456789", # Too long
            "abc1234567",   # Contains letters
            "011123456789"  # Invalid prefix
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                UserProfile(phone_number=phone)


class TestUserCreate:
    """Test UserCreate model validation"""
    
    def test_user_create_valid(self):
        """Test valid user creation data"""
        user_data = UserCreate(
            email="test@example.com",
            name="홍길동",
            password="StrongP@ss123",
            consent_data_processing=True,
            consent_marketing=False
        )
        
        assert user_data.email == "test@example.com"
        assert user_data.name == "홍길동"
        assert user_data.consent_data_processing is True
    
    def test_user_create_name_validation(self):
        """Test user name validation"""
        # Valid names
        valid_names = ["홍길동", "John Doe", "김영희", "Test User_123", "사용자-이름"]
        
        for name in valid_names:
            user_data = UserCreate(
                email="test@example.com",
                name=name,
                password="StrongP@ss123",
                consent_data_processing=True
            )
            assert user_data.name == name.strip()
        
        # Invalid names
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com", 
                name="   ",  # Only whitespace
                password="StrongP@ss123",
                consent_data_processing=True
            )
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                name="Name@#$%",  # Invalid characters
                password="StrongP@ss123", 
                consent_data_processing=True
            )
    
    def test_user_create_password_validation(self):
        """Test password validation rules"""
        base_data = {
            "email": "test@example.com",
            "name": "Test User",
            "consent_data_processing": True
        }
        
        # Valid passwords (meet 3 of 4 criteria)
        valid_passwords = [
            "StrongP@ss123",    # All 4 criteria
            "Password123",      # Upper, lower, number (3 criteria)
            "password123!",     # Lower, number, special (3 criteria)
            "PASSWORD123!",     # Upper, number, special (3 criteria)
            "StrongPassword!",  # Upper, lower, special (3 criteria)
        ]
        
        for password in valid_passwords:
            user_data = UserCreate(**base_data, password=password)
            assert user_data.password == password
        
        # Invalid passwords
        invalid_passwords = [
            "short",            # Too short
            "password",         # Only lowercase
            "PASSWORD",         # Only uppercase
            "12345678",         # Only numbers
            "!@#$%^&*",         # Only special chars
            "Pass1",            # Only 2 criteria
            "password123",      # Only 2 criteria  
            "PASSWORD!",        # Only 2 criteria
            "a" * 130,          # Too long
            "password",         # Common password
            "12345678",         # Common password
            "qwerty",           # Common password
            "admin",            # Common password
            "user"              # Common password
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValidationError) as exc_info:
                UserCreate(**base_data, password=password)
            # Check that error message is meaningful
            assert len(str(exc_info.value)) > 0
    
    def test_user_create_consent_validation(self):
        """Test consent validation"""
        base_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password": "StrongP@ss123"
        }
        
        # Valid: consent given
        user_data = UserCreate(**base_data, consent_data_processing=True)
        assert user_data.consent_data_processing is True
        
        # Invalid: consent not given
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**base_data, consent_data_processing=False)
        
        assert "동의해야 회원가입이 가능합니다" in str(exc_info.value)


class TestSocialUserCreate:
    """Test SocialUserCreate model validation"""
    
    def test_social_user_create_valid(self):
        """Test valid social user creation"""
        user_data = SocialUserCreate(
            email="test@gmail.com",
            name="Test User",
            provider=AuthProvider.GOOGLE,
            external_id="google_123456789",
            profile_image_url="https://lh3.googleusercontent.com/abc123",
            consent_data_processing=True
        )
        
        assert user_data.provider == AuthProvider.GOOGLE
        assert user_data.external_id == "google_123456789"
        assert user_data.consent_data_processing is True
    
    def test_social_user_auth_provider_enum(self):
        """Test AuthProvider enum validation"""
        # Valid providers
        for provider in [AuthProvider.LOCAL, AuthProvider.GOOGLE]:
            user_data = SocialUserCreate(
                email="test@example.com",
                name="Test User", 
                provider=provider,
                external_id="ext_123",
                consent_data_processing=True
            )
            assert user_data.provider == provider


class TestUser:
    """Test User model"""
    
    def test_user_creation_with_timezone_aware_dates(self):
        """Test that user timestamps are timezone-aware"""
        user = User(
            email="test@example.com",
            name="Test User",
            provider=AuthProvider.LOCAL
        )
        
        # Timestamps should be timezone-aware UTC
        assert user.created_at.tzinfo == timezone.utc
        assert user.updated_at.tzinfo == timezone.utc
    
    def test_user_defaults(self):
        """Test user model defaults"""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        
        assert user.provider == AuthProvider.LOCAL
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_premium is False
        assert user.consent_marketing is False
        assert user.consent_data_processing is True
        assert user.profile is not None
        assert user.last_login is None


class TestUserLogin:
    """Test login models"""
    
    def test_user_login_basic(self):
        """Test basic user login model"""
        login_data = UserLogin(
            email="test@example.com",
            password="password123"
        )
        
        assert login_data.email == "test@example.com"
        assert login_data.password == "password123"
    
    def test_user_login_request_with_remember(self):
        """Test login request with remember flag"""
        login_data = UserLoginRequest(
            email="test@example.com", 
            password="password123",
            remember=True
        )
        
        assert login_data.remember is True


class TestTokenModels:
    """Test token-related models"""
    
    def test_token_response(self):
        """Test token response model"""
        user = User(email="test@example.com", name="Test User")
        
        token_response = TokenResponse(
            access_token="jwt.access.token",
            refresh_token="jwt.refresh.token",
            expires_in=900,
            user=UserResponse(
                id="123",
                email=user.email,
                name=user.name,
                provider=user.provider,
                profile=user.profile,
                is_verified=user.is_verified,
                is_premium=user.is_premium,
                created_at=user.created_at
            )
        )
        
        assert token_response.token_type == "bearer"
        assert token_response.expires_in == 900
        assert token_response.user.email == "test@example.com"
    
    def test_token_refresh(self):
        """Test token refresh model"""
        refresh_data = TokenRefresh(refresh_token="jwt.refresh.token")
        assert refresh_data.refresh_token == "jwt.refresh.token"


class TestUserSettings:
    """Test user settings models"""
    
    def test_user_notification_settings(self):
        """Test notification settings with defaults"""
        settings = UserNotificationSettings()
        
        assert settings.new_announcements is True
        assert settings.deadline_reminder is True
        assert settings.status_updates is True
        assert settings.weekly_digest is False
    
    def test_user_interest_settings(self):
        """Test interest settings"""
        settings = UserInterestSettings(
            primary_interest="AI/ML",
            additional_interests=["blockchain", "fintech", "healthtech"]
        )
        
        assert settings.primary_interest == "AI/ML"
        assert len(settings.additional_interests) == 3
    
    def test_user_location_settings(self):
        """Test location settings"""
        settings = UserLocationSettings(
            province="서울특별시",
            city="강남구"
        )
        
        assert settings.province == "서울특별시"
        assert settings.city == "강남구"
    
    def test_user_settings_complete(self):
        """Test complete user settings model"""
        settings = UserSettings(
            notifications=UserNotificationSettings(
                weekly_digest=True
            ),
            interests=UserInterestSettings(
                primary_interest="AI/ML"
            ),
            location=UserLocationSettings(
                province="경기도",
                city="성남시"
            )
        )
        
        assert settings.notifications.weekly_digest is True
        assert settings.interests.primary_interest == "AI/ML"
        assert settings.location.province == "경기도"


class TestModelSerialization:
    """Test model serialization and data conversion"""
    
    def test_user_response_excludes_sensitive_data(self):
        """Test that UserResponse excludes sensitive information"""
        user = User(
            email="test@example.com",
            name="Test User",
            password_hash="$2b$12$hashed_password"
        )
        
        user_response = UserResponse(
            id="123",
            email=user.email,
            name=user.name,
            provider=user.provider,
            profile=user.profile,
            is_verified=user.is_verified,
            is_premium=user.is_premium,
            created_at=user.created_at
        )
        
        # Should not contain sensitive data
        response_dict = user_response.model_dump()
        assert "password_hash" not in response_dict
        assert "external_id" not in response_dict or response_dict["external_id"] is None
        assert "consent_marketing" not in response_dict
        assert "consent_data_processing" not in response_dict
    
    def test_model_json_serialization(self):
        """Test that models can be properly JSON serialized"""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        
        # Should be able to convert to dict and back
        user_dict = user.model_dump()
        assert isinstance(user_dict, dict)
        assert user_dict["email"] == "test@example.com"
        
        # Timestamps should be serializable
        assert isinstance(user_dict["created_at"], datetime)
        assert isinstance(user_dict["updated_at"], datetime)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_and_whitespace_handling(self):
        """Test handling of empty strings and whitespace"""
        # Test that whitespace in names is trimmed
        user_data = UserCreate(
            email="test@example.com",
            name="  Test User  ",
            password="StrongP@ss123",
            consent_data_processing=True
        )
        
        assert user_data.name == "Test User"
    
    def test_unicode_and_international_names(self):
        """Test support for international characters"""
        international_names = [
            "김민수",           # Korean
            "José María",      # Spanish
            "François",        # French  
            "Müller",          # German
            "Александр",       # Russian
            "田中太郎",          # Japanese
            "张伟"             # Chinese
        ]
        
        for name in international_names:
            user_data = UserCreate(
                email="test@example.com",
                name=name,
                password="StrongP@ss123", 
                consent_data_processing=True
            )
            assert user_data.name == name
    
    def test_extreme_values(self):
        """Test extreme but valid values"""
        # Maximum length name
        max_name = "a" * 50
        user_data = UserCreate(
            email="test@example.com",
            name=max_name,
            password="StrongP@ss123",
            consent_data_processing=True
        )
        assert len(user_data.name) == 50
        
        # Maximum length password  
        max_password = "Strong1!" + "a" * 120  # 128 chars total
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            password=max_password,
            consent_data_processing=True
        )
        assert len(user_data.password) == 128