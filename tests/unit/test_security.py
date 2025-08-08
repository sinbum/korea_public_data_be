"""
Unit tests for security module functionality.

Tests JWT token operations, password hashing, OAuth state management,
and security utilities.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from jose import jwt

from app.core.security import (
    SecurityManager, security, get_password_hash, verify_password,
    create_access_token, create_refresh_token, verify_token,
    blacklist_token, create_token_pair
)
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)"""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token operations"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        user_data = {"user_id": "123", "email": "test@example.com"}
        token = create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        
        # Decode without verification to check structure
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["user_id"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload  # JWT ID for tracking
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_data = {"user_id": "123", "email": "test@example.com"}
        token = create_refresh_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["user_id"] == "123"
        assert payload["type"] == "refresh"
        assert "jti" in payload
    
    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration"""
        user_data = {"user_id": "123"}
        custom_delta = timedelta(minutes=30)
        
        token = create_access_token(user_data, expires_delta=custom_delta)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Check that expiry is roughly 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        
        assert 29 * 60 < time_diff.total_seconds() < 31 * 60  # ~30 minutes
    
    def test_verify_valid_token(self):
        """Test verification of valid token"""
        user_data = {"user_id": "123", "email": "test@example.com"}
        token = create_access_token(user_data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        invalid_token = "invalid.jwt.token"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test verification of expired token"""
        user_data = {"user_id": "123"}
        # Create token that expires in 1 second
        token = create_access_token(user_data, expires_delta=timedelta(seconds=1))
        
        # Wait for expiration
        time.sleep(2)
        
        payload = verify_token(token)
        assert payload is None
    
    def test_create_token_pair(self):
        """Test creation of token pair (access + refresh)"""
        user_data = {"user_id": "123", "email": "test@example.com"}
        
        tokens = create_token_pair(user_data)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == settings.jwt_access_token_expire_minutes * 60
        
        # Verify both tokens are valid
        access_payload = verify_token(tokens["access_token"])
        refresh_payload = verify_token(tokens["refresh_token"])
        
        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"


class TestSecurityManager:
    """Test SecurityManager class"""
    
    def test_security_manager_initialization(self):
        """Test SecurityManager initialization"""
        manager = SecurityManager()
        
        assert manager.algorithm == settings.jwt_algorithm
        assert manager.secret_key == settings.jwt_secret_key
        assert manager.access_token_expire_minutes == settings.jwt_access_token_expire_minutes
        assert manager.refresh_token_expire_days == settings.jwt_refresh_token_expire_days
    
    def test_generate_state_token(self):
        """Test OAuth state token generation"""
        manager = SecurityManager()
        
        state1 = manager.generate_state_token()
        state2 = manager.generate_state_token()
        
        assert len(state1) > 30  # URL-safe tokens are long
        assert len(state2) > 30
        assert state1 != state2  # Should be unique
        assert all(c.isalnum() or c in '-_' for c in state1)  # URL-safe characters


@pytest.mark.asyncio
class TestOAuthStateManagement:
    """Test OAuth state management with Redis fallback"""
    
    @patch('app.core.security.redis_client')
    def test_store_oauth_state_redis_success(self, mock_redis):
        """Test OAuth state storage in Redis"""
        mock_redis.setex.return_value = True
        
        manager = SecurityManager()
        state = "test_state_123"
        data = {"user_id": "123", "redirect": "/dashboard"}
        
        result = manager.store_oauth_state(state, data, 600)
        
        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"oauth_state:{state}"
        assert call_args[0][1] == 600  # TTL
    
    @patch('app.core.security.redis_client')
    def test_store_oauth_state_redis_failure_fallback_to_memory(self, mock_redis):
        """Test OAuth state falls back to memory when Redis fails"""
        mock_redis.setex.side_effect = Exception("Redis connection failed")
        
        manager = SecurityManager()
        state = "test_state_123"
        data = {"user_id": "123", "redirect": "/dashboard"}
        
        # Clear any existing memory state
        from app.core.security import _oauth_state_memory_store, _oauth_state_memory_expiry
        _oauth_state_memory_store.clear()
        _oauth_state_memory_expiry.clear()
        
        result = manager.store_oauth_state(state, data, 600)
        
        assert result is True
        assert state in _oauth_state_memory_store
        assert state in _oauth_state_memory_expiry
        assert _oauth_state_memory_store[state] == data
    
    @patch('app.core.security.redis_client')
    def test_get_oauth_state_redis_success(self, mock_redis):
        """Test OAuth state retrieval from Redis"""
        import json
        test_data = {"user_id": "123", "redirect": "/dashboard"}
        mock_redis.get.return_value = json.dumps(test_data)
        mock_redis.delete.return_value = True
        
        manager = SecurityManager()
        state = "test_state_123"
        
        result = manager.get_oauth_state(state)
        
        assert result == test_data
        mock_redis.get.assert_called_once_with(f"oauth_state:{state}")
        mock_redis.delete.assert_called_once_with(f"oauth_state:{state}")
    
    @patch('app.core.security.redis_client')
    def test_get_oauth_state_redis_failure_fallback_to_memory(self, mock_redis):
        """Test OAuth state retrieval falls back to memory when Redis fails"""
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        # Setup memory store
        from app.core.security import _oauth_state_memory_store, _oauth_state_memory_expiry
        state = "test_state_123"
        test_data = {"user_id": "123", "redirect": "/dashboard"}
        current_time = time.time()
        
        _oauth_state_memory_store[state] = test_data
        _oauth_state_memory_expiry[state] = current_time + 600  # Not expired
        
        manager = SecurityManager()
        result = manager.get_oauth_state(state)
        
        assert result == test_data
        # State should be removed after retrieval (use-once)
        assert state not in _oauth_state_memory_store
        assert state not in _oauth_state_memory_expiry
    
    def test_get_oauth_state_memory_expired(self):
        """Test that expired OAuth state in memory returns None"""
        from app.core.security import _oauth_state_memory_store, _oauth_state_memory_expiry
        
        state = "test_state_expired"
        test_data = {"user_id": "123"}
        expired_time = time.time() - 10  # 10 seconds ago
        
        _oauth_state_memory_store[state] = test_data
        _oauth_state_memory_expiry[state] = expired_time
        
        manager = SecurityManager()
        result = manager.get_oauth_state(state)
        
        assert result is None
        # Expired state should be cleaned up
        assert state not in _oauth_state_memory_store
        assert state not in _oauth_state_memory_expiry


@pytest.mark.asyncio
class TestTokenBlacklist:
    """Test token blacklisting functionality"""
    
    @patch('app.core.security.redis_client')
    def test_blacklist_token_success(self, mock_redis):
        """Test successful token blacklisting"""
        mock_redis.setex.return_value = True
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        result = blacklist_token(token)
        
        assert result is True
        mock_redis.setex.assert_called_once()
    
    @patch('app.core.security.redis_client')
    def test_blacklist_token_redis_failure(self, mock_redis):
        """Test token blacklisting when Redis fails"""
        mock_redis.setex.side_effect = Exception("Redis connection failed")
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        result = blacklist_token(token)
        
        assert result is False  # Should fail gracefully
    
    @patch('app.core.security.redis_client')
    def test_is_token_blacklisted_true(self, mock_redis):
        """Test checking if token is blacklisted (true case)"""
        mock_redis.exists.return_value = 1  # Token exists in blacklist
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        manager = SecurityManager()
        result = manager.is_token_blacklisted(token)
        
        assert result is True
    
    @patch('app.core.security.redis_client')
    def test_is_token_blacklisted_false(self, mock_redis):
        """Test checking if token is blacklisted (false case)"""
        mock_redis.exists.return_value = 0  # Token not in blacklist
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        manager = SecurityManager()
        result = manager.is_token_blacklisted(token)
        
        assert result is False
    
    @patch('app.core.security.redis_client')
    def test_is_token_blacklisted_redis_failure_fail_open(self, mock_redis):
        """Test that blacklist check fails open when Redis is unavailable"""
        mock_redis.exists.side_effect = Exception("Redis connection failed")
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        manager = SecurityManager()
        result = manager.is_token_blacklisted(token)
        
        # Should fail open (return False) for availability
        assert result is False
    
    @patch('app.core.security.redis_client')
    def test_verify_token_with_blacklisted_token(self, mock_redis):
        """Test that blacklisted tokens are rejected"""
        mock_redis.exists.return_value = 1  # Token is blacklisted
        
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        result = verify_token(token)
        
        assert result is None  # Should be rejected due to blacklist


class TestSecurityUtilities:
    """Test security utility functions"""
    
    def test_timezone_aware_timestamps(self):
        """Test that tokens use timezone-aware timestamps"""
        user_data = {"user_id": "123"}
        token = create_access_token(user_data)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Check that timestamps are present
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expires at
        
        # Verify timestamps are reasonable (within last minute and future)
        now = datetime.now(timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        
        assert (now - iat).total_seconds() < 60  # Issued within last minute
        assert exp > now  # Expires in future
    
    def test_jwt_id_uniqueness(self):
        """Test that JWT IDs are unique for tracking"""
        user_data = {"user_id": "123"}
        
        token1 = create_access_token(user_data)
        token2 = create_access_token(user_data)
        
        payload1 = jwt.decode(token1, options={"verify_signature": False})
        payload2 = jwt.decode(token2, options={"verify_signature": False})
        
        assert "jti" in payload1
        assert "jti" in payload2
        assert payload1["jti"] != payload2["jti"]  # Should be unique