"""
Enhanced Redis caching layer with circuit breaker pattern and performance optimization.

Provides intelligent caching with fallback mechanisms, circuit breaker pattern,
and performance monitoring for improved application responsiveness.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps
import pickle
import hashlib

import redis.asyncio as aioredis
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from .config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: tuple = (ConnectionError, TimeoutError, RedisError)


class CircuitBreaker:
    """Circuit breaker implementation for Redis operations"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                raise ConnectionError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    async def async_call(self, func: Callable, *args, **kwargs):
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                raise ConnectionError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.config.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:  # Require 2 successes to fully close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker moved to CLOSED state")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker moved to OPEN state after {self.failure_count} failures")


class CacheManager:
    """Enhanced cache manager with circuit breaker and fallback mechanisms"""
    
    def __init__(self):
        self.sync_client: Optional[redis.Redis] = None
        self.async_client: Optional[aioredis.Redis] = None
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "circuit_open_count": 0,
            "memory_fallback_count": 0
        }
    
    def _get_redis_config(self) -> Dict[str, Any]:
        """Get optimized Redis connection configuration"""
        return {
            "socket_connect_timeout": 2.0,
            "socket_timeout": 3.0,
            "retry_on_timeout": True,
            "retry_on_error": [ConnectionError, TimeoutError],
            "max_connections": 20,
            "health_check_interval": 30,
            "decode_responses": False,  # Handle binary data
            "protocol": 3,  # Use RESP3 for better performance
        }
    
    def connect_sync(self) -> None:
        """Initialize synchronous Redis client"""
        try:
            config = self._get_redis_config()
            self.sync_client = redis.from_url(settings.redis_url, **config)
            
            # Test connection
            self.circuit_breaker.call(self.sync_client.ping)
            logger.info("Redis 동기 연결 성공 (circuit breaker 활성화)")
            
        except Exception as e:
            logger.error(f"Redis 동기 연결 실패: {e}")
            raise
    
    async def connect_async(self) -> None:
        """Initialize asynchronous Redis client"""
        try:
            config = self._get_redis_config()
            self.async_client = aioredis.from_url(settings.redis_url, **config)
            
            # Test connection
            await self.circuit_breaker.async_call(self.async_client.ping)
            logger.info("Redis 비동기 연결 성공 (circuit breaker 활성화)")
            
        except Exception as e:
            logger.error(f"Redis 비동기 연결 실패: {e}")
            raise
    
    def close_sync(self) -> None:
        """Close synchronous Redis connection"""
        if self.sync_client:
            self.sync_client.close()
            self.sync_client = None
            logger.info("Redis 동기 연결 종료")
    
    async def close_async(self) -> None:
        """Close asynchronous Redis connection"""
        if self.async_client:
            await self.async_client.close()
            self.async_client = None
            logger.info("Redis 비동기 연결 종료")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            # Try JSON first for simple types
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(value, ensure_ascii=False).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(value)
        except (TypeError, ValueError):
            # Fallback to pickle
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle
            return pickle.loads(data)
    
    def _memory_set(self, key: str, value: Any, ttl: int = 300):
        """Store in memory cache with TTL"""
        expire_time = time.time() + ttl
        self._memory_cache[key] = {
            "value": value,
            "expire_time": expire_time
        }
        self._cache_stats["memory_fallback_count"] += 1
    
    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from memory cache"""
        if key not in self._memory_cache:
            return None
        
        cache_entry = self._memory_cache[key]
        if time.time() > cache_entry["expire_time"]:
            del self._memory_cache[key]
            return None
        
        return cache_entry["value"]
    
    def _memory_delete(self, key: str) -> bool:
        """Delete from memory cache"""
        return self._memory_cache.pop(key, None) is not None
    
    def _cleanup_memory_cache(self):
        """Clean expired entries from memory cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if current_time > entry["expire_time"]
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (sync)"""
        try:
            if not self.sync_client:
                self.connect_sync()
            
            serialized_value = self._serialize_value(value)
            result = self.circuit_breaker.call(
                self.sync_client.setex, key, ttl, serialized_value
            )
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Redis set failed, using memory fallback: {e}")
            self._cache_stats["errors"] += 1
            if self.circuit_breaker.state == CircuitState.OPEN:
                self._cache_stats["circuit_open_count"] += 1
            
            # Fallback to memory cache
            self._memory_set(key, value, min(ttl, 300))  # Max 5 min in memory
            return True
    
    async def aset(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (async)"""
        try:
            if not self.async_client:
                await self.connect_async()
            
            serialized_value = self._serialize_value(value)
            result = await self.circuit_breaker.async_call(
                self.async_client.setex, key, ttl, serialized_value
            )
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Redis aset failed, using memory fallback: {e}")
            self._cache_stats["errors"] += 1
            if self.circuit_breaker.state == CircuitState.OPEN:
                self._cache_stats["circuit_open_count"] += 1
            
            # Fallback to memory cache
            self._memory_set(key, value, min(ttl, 300))  # Max 5 min in memory
            return True
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (sync)"""
        try:
            if not self.sync_client:
                self.connect_sync()
            
            data = self.circuit_breaker.call(self.sync_client.get, key)
            if data is None:
                # Check memory fallback
                memory_result = self._memory_get(key)
                if memory_result is not None:
                    self._cache_stats["hits"] += 1
                    return memory_result
                
                self._cache_stats["misses"] += 1
                return None
            
            self._cache_stats["hits"] += 1
            return self._deserialize_value(data)
            
        except Exception as e:
            logger.warning(f"Redis get failed, checking memory fallback: {e}")
            self._cache_stats["errors"] += 1
            if self.circuit_breaker.state == CircuitState.OPEN:
                self._cache_stats["circuit_open_count"] += 1
            
            # Fallback to memory cache
            memory_result = self._memory_get(key)
            if memory_result is not None:
                self._cache_stats["hits"] += 1
                return memory_result
            
            self._cache_stats["misses"] += 1
            return None
    
    async def aget(self, key: str) -> Optional[Any]:
        """Get value from cache (async)"""
        try:
            if not self.async_client:
                await self.connect_async()
            
            data = await self.circuit_breaker.async_call(self.async_client.get, key)
            if data is None:
                # Check memory fallback
                memory_result = self._memory_get(key)
                if memory_result is not None:
                    self._cache_stats["hits"] += 1
                    return memory_result
                
                self._cache_stats["misses"] += 1
                return None
            
            self._cache_stats["hits"] += 1
            return self._deserialize_value(data)
            
        except Exception as e:
            logger.warning(f"Redis aget failed, checking memory fallback: {e}")
            self._cache_stats["errors"] += 1
            if self.circuit_breaker.state == CircuitState.OPEN:
                self._cache_stats["circuit_open_count"] += 1
            
            # Fallback to memory cache
            memory_result = self._memory_get(key)
            if memory_result is not None:
                self._cache_stats["hits"] += 1
                return memory_result
            
            self._cache_stats["misses"] += 1
            return None
    
    def delete(self, key: str) -> bool:
        """Delete key from cache (sync)"""
        try:
            if not self.sync_client:
                self.connect_sync()
            
            result = self.circuit_breaker.call(self.sync_client.delete, key)
            # Also delete from memory cache
            self._memory_delete(key)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            self._cache_stats["errors"] += 1
            # Still try to delete from memory cache
            return self._memory_delete(key)
    
    async def adelete(self, key: str) -> bool:
        """Delete key from cache (async)"""
        try:
            if not self.async_client:
                await self.connect_async()
            
            result = await self.circuit_breaker.async_call(self.async_client.delete, key)
            # Also delete from memory cache
            self._memory_delete(key)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Redis adelete failed: {e}")
            self._cache_stats["errors"] += 1
            # Still try to delete from memory cache
            return self._memory_delete(key)
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (sync)"""
        try:
            if not self.sync_client:
                self.connect_sync()
            
            keys = self.circuit_breaker.call(self.sync_client.keys, pattern)
            if keys:
                result = self.circuit_breaker.call(self.sync_client.delete, *keys)
                return result
            return 0
            
        except Exception as e:
            logger.warning(f"Redis clear_pattern failed: {e}")
            self._cache_stats["errors"] += 1
            
            # Clear matching keys from memory cache
            import fnmatch
            matching_keys = [
                key for key in self._memory_cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            for key in matching_keys:
                del self._memory_cache[key]
            return len(matching_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        self._cleanup_memory_cache()
        
        stats = self._cache_stats.copy()
        stats.update({
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "memory_cache_size": len(self._memory_cache),
            "redis_connected": self.sync_client is not None or self.async_client is not None,
            "hit_rate": (
                stats["hits"] / (stats["hits"] + stats["misses"])
                if (stats["hits"] + stats["misses"]) > 0 else 0
            )
        })
        return stats
    
    def is_healthy(self) -> bool:
        """Check cache health"""
        try:
            if self.sync_client:
                self.circuit_breaker.call(self.sync_client.ping)
                return True
            return False
        except Exception:
            return self.circuit_breaker.state != CircuitState.OPEN


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set value in cache"""
    return cache_manager.set(key, value, ttl)

async def cache_aset(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set value in cache (async)"""
    return await cache_manager.aset(key, value, ttl)

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    return cache_manager.get(key)

async def cache_aget(key: str) -> Optional[Any]:
    """Get value from cache (async)"""
    return await cache_manager.aget(key)

def cache_delete(key: str) -> bool:
    """Delete key from cache"""
    return cache_manager.delete(key)

async def cache_adelete(key: str) -> bool:
    """Delete key from cache (async)"""
    return await cache_manager.adelete(key)


# Decorators for caching
def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def acached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching async function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_manager.aget(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.aset(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

@asynccontextmanager
async def get_cache_session():
    """Context manager for cache operations"""
    try:
        yield cache_manager
    finally:
        # Connection cleanup handled by connection pool
        pass