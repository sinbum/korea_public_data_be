"""
Security utilities for JWT authentication and password handling.

Provides JWT token generation/verification and password hashing utilities
for both local and OAuth authentication flows.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
import redis
from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklist
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


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
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
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
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
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
        """Add token to blacklist (Redis)"""
        try:
            # Use token as key with expiration
            if expire_seconds is None:
                # Set expiration to match token expiration
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                expire_time = datetime.fromtimestamp(payload.get('exp', 0))
                expire_seconds = max(0, int((expire_time - datetime.utcnow()).total_seconds()))
            
            redis_client.setex(f"blacklist:{token}", expire_seconds, "1")
            return True
        except Exception:
            return False
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            return redis_client.exists(f"blacklist:{token}") > 0
        except Exception:
            return False
    
    def generate_state_token(self) -> str:
        """Generate a secure state token for OAuth CSRF protection"""
        return secrets.token_urlsafe(32)
    
    def store_oauth_state(self, state: str, data: Dict[str, Any], expire_seconds: int = 600) -> bool:
        """Store OAuth state data in Redis with expiration"""
        try:
            import json
            redis_client.setex(f"oauth_state:{state}", expire_seconds, json.dumps(data))
            return True
        except Exception:
            return False
    
    def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Retrieve and delete OAuth state data"""
        try:
            import json
            key = f"oauth_state:{state}"
            data = redis_client.get(key)
            if data:
                redis_client.delete(key)  # Use once only
                return json.loads(data)
            return None
        except Exception:
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