"""
Security utilities for JWT authentication and password handling.

Provides JWT token generation/verification and password hashing utilities
for both local and OAuth authentication flows.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
import time
import threading
import json
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
import redis
import logging
from .config import settings

logger = logging.getLogger(__name__)

# Thread-safe in-memory fallback store for OAuth state when Redis is unavailable
_oauth_state_memory_store: dict[str, dict[str, Any]] = {}
_oauth_state_memory_expiry: dict[str, float] = {}
_oauth_memory_lock = threading.RLock()

# Cleanup task for memory store
def _cleanup_expired_oauth_states():
    """Clean up expired OAuth states from memory store"""
    current_time = time.time()
    with _oauth_memory_lock:
        expired_keys = [
            key for key, exp_time in _oauth_state_memory_expiry.items() 
            if current_time > exp_time
        ]
        for key in expired_keys:
            _oauth_state_memory_store.pop(key, None)
            _oauth_state_memory_expiry.pop(key, None)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired OAuth states from memory")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklist (tuned for fast-fail if Redis is down)
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=2.0,  # Increased from 0.5s
    socket_timeout=2.0,          # Increased from 0.5s
    retry_on_timeout=True,
    max_connections=10,
    health_check_interval=30
)


class SecurityManager:
    """Centralized security management for authentication"""
    
    def __init__(self):
        self.algorithm = settings.jwt_algorithm
        self.secret_key = settings.jwt_secret_key
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "type": "access",
            "jti": secrets.token_hex(16)  # JWT ID for better token tracking
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "type": "refresh",
            "jti": secrets.token_hex(16)  # JWT ID for better token tracking
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                return None
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def blacklist_token(self, token: str, expire_seconds: Optional[int] = None) -> bool:
        """Add token to blacklist (Redis with fallback)"""
        try:
            # Use token JTI if available, otherwise full token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_id = payload.get('jti', token)  # Use JTI for smaller keys
            
            if expire_seconds is None:
                # Set expiration to match token expiration
                expire_time = datetime.fromtimestamp(payload.get('exp', 0), timezone.utc)
                expire_seconds = max(0, int((expire_time - datetime.now(timezone.utc)).total_seconds()))
            
            redis_client.setex(f"blacklist:{token_id}", expire_seconds, "1")
            logger.info(f"Token blacklisted successfully: {token_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            # Extract JTI from token for lookup
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_id = payload.get('jti', token)
            return redis_client.exists(f"blacklist:{token_id}") > 0
        except Exception as e:
            logger.warning(f"Failed to check blacklist, allowing token: {str(e)}")
            return False  # Fail open for availability
    
    def generate_state_token(self) -> str:
        """Generate a secure state token for OAuth CSRF protection"""
        return secrets.token_urlsafe(32)
    
    def store_oauth_state(self, state: str, data: Dict[str, Any], expire_seconds: int = 600) -> bool:
        """Store OAuth state data in Redis with expiration. Falls back to in-memory store if Redis is unavailable."""
        try:
            redis_client.setex(f"oauth_state:{state}", expire_seconds, json.dumps(data))
            logger.debug(f"OAuth state stored in Redis: {state[:8]}...")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory fallback: {str(e)}")
            # Fallback: store in process memory with TTL (thread-safe)
            try:
                with _oauth_memory_lock:
                    _oauth_state_memory_store[state] = data
                    _oauth_state_memory_expiry[state] = time.time() + float(expire_seconds)
                    # Clean up expired entries periodically
                    if len(_oauth_state_memory_store) % 10 == 0:  # Every 10th store
                        _cleanup_expired_oauth_states()
                logger.debug(f"OAuth state stored in memory: {state[:8]}...")
                return True
            except Exception as mem_e:
                logger.error(f"Failed to store OAuth state in memory: {str(mem_e)}")
                return False
    
    def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Retrieve and delete OAuth state data. Supports in-memory fallback."""
        # Try Redis first
        try:
            key = f"oauth_state:{state}"
            data = redis_client.get(key)
            if data:
                redis_client.delete(key)  # Use once only
                logger.debug(f"OAuth state retrieved from Redis: {state[:8]}...")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis lookup failed, trying memory fallback: {str(e)}")

        # Fallback to memory store (thread-safe)
        try:
            with _oauth_memory_lock:
                exp = _oauth_state_memory_expiry.get(state)
                if exp is None:
                    return None
                    
                current_time = time.time()
                if current_time > exp:
                    # Expired; cleanup
                    _oauth_state_memory_expiry.pop(state, None)
                    _oauth_state_memory_store.pop(state, None)
                    logger.debug(f"OAuth state expired in memory: {state[:8]}...")
                    return None
                    
                data = _oauth_state_memory_store.pop(state, None)
                _oauth_state_memory_expiry.pop(state, None)
                logger.debug(f"OAuth state retrieved from memory: {state[:8]}...")
                # Ensure dict is returned
                return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error(f"Memory store lookup failed: {str(e)}")
            return None


# Global security manager instance
security = SecurityManager()


def get_password_hash(password: str) -> str:
    """Convenience function for password hashing"""
    return security.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Convenience function for password verification"""
    return security.verify_password(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Convenience function for access token creation"""
    return security.create_access_token(data, expires_delta)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Convenience function for refresh token creation"""
    return security.create_refresh_token(data, expires_delta)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Convenience function for token verification"""
    return security.verify_token(token)


def blacklist_token(token: str, expire_seconds: Optional[int] = None) -> bool:
    """Convenience function for token blacklisting"""
    return security.blacklist_token(token, expire_seconds)


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """Create both access and refresh tokens for a user"""
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data=user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60
    }