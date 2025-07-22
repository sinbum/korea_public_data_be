"""
Rate Limiting and Throttling System - controls API request rates and quotas.

Provides rate limiting, throttling, and quota management to protect APIs
from abuse and ensure fair usage across different clients.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Types of rate limiting"""
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    BANDWIDTH_PER_SECOND = "bandwidth_per_second"
    CONCURRENT_REQUESTS = "concurrent_requests"


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    SLIDING_WINDOW_LOG = "sliding_window_log"


class RateLimit(BaseModel):
    """Rate limit configuration"""
    name: str = Field(..., description="Rate limit name")
    limit: int = Field(..., description="Request limit")
    window_seconds: int = Field(..., description="Time window in seconds")
    algorithm: RateLimitAlgorithm = Field(RateLimitAlgorithm.SLIDING_WINDOW, description="Algorithm to use")
    
    # Burst handling
    burst_limit: Optional[int] = Field(None, description="Burst limit (for token bucket)")
    
    # Scope configuration
    per_client: bool = Field(True, description="Apply per client")
    per_endpoint: bool = Field(False, description="Apply per endpoint")
    per_api_key: bool = Field(True, description="Apply per API key")
    
    # Response configuration
    include_headers: bool = Field(True, description="Include rate limit headers in response")
    retry_after_header: bool = Field(True, description="Include Retry-After header when limited")
    
    @property
    def key_components(self) -> List[str]:
        """Get components used for rate limit key generation"""
        components = []
        if self.per_client:
            components.append("client")
        if self.per_endpoint:
            components.append("endpoint") 
        if self.per_api_key:
            components.append("api_key")
        return components


class RateLimitResult(BaseModel):
    """Result of rate limit check"""
    allowed: bool = Field(..., description="Whether request is allowed")
    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: datetime = Field(..., description="When limit resets")
    retry_after: Optional[int] = Field(None, description="Retry after seconds")
    
    # Headers for HTTP response
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers to include")


class RateLimitStorage(ABC):
    """Abstract storage interface for rate limiting data"""
    
    @abstractmethod
    async def get_count(self, key: str) -> int:
        """Get current count for key"""
        pass
    
    @abstractmethod
    async def increment(self, key: str, window_seconds: int) -> int:
        """Increment count and return new value"""
        pass
    
    @abstractmethod
    async def set_count(self, key: str, count: int, ttl_seconds: int):
        """Set count with TTL"""
        pass
    
    @abstractmethod
    async def get_timestamps(self, key: str) -> List[float]:
        """Get timestamps for sliding window log"""
        pass
    
    @abstractmethod
    async def add_timestamp(self, key: str, timestamp: float, window_seconds: int):
        """Add timestamp for sliding window log"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self, key: str, before_timestamp: float):
        """Cleanup expired timestamps"""
        pass


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory storage for rate limiting (for development/testing)"""
    
    def __init__(self):
        self._counts: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def get_count(self, key: str) -> int:
        async with self._lock:
            data = self._counts.get(key, {})
            
            # Check if expired
            if 'expires_at' in data and time.time() > data['expires_at']:
                del self._counts[key]
                return 0
            
            return data.get('count', 0)
    
    async def increment(self, key: str, window_seconds: int) -> int:
        async with self._lock:
            now = time.time()
            data = self._counts.get(key, {'count': 0, 'expires_at': now + window_seconds})
            
            # Check if expired
            if now > data['expires_at']:
                data = {'count': 0, 'expires_at': now + window_seconds}
            
            data['count'] += 1
            self._counts[key] = data
            
            return data['count']
    
    async def set_count(self, key: str, count: int, ttl_seconds: int):
        async with self._lock:
            self._counts[key] = {
                'count': count,
                'expires_at': time.time() + ttl_seconds
            }
    
    async def get_timestamps(self, key: str) -> List[float]:
        async with self._lock:
            return self._timestamps.get(key, [])
    
    async def add_timestamp(self, key: str, timestamp: float, window_seconds: int):
        async with self._lock:
            if key not in self._timestamps:
                self._timestamps[key] = []
            
            self._timestamps[key].append(timestamp)
            
            # Cleanup old timestamps
            cutoff = timestamp - window_seconds
            self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]
    
    async def cleanup_expired(self, key: str, before_timestamp: float):
        async with self._lock:
            if key in self._timestamps:
                self._timestamps[key] = [t for t in self._timestamps[key] if t > before_timestamp]


class RedisRateLimitStorage(RateLimitStorage):
    """Redis storage for rate limiting (for production)"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_count(self, key: str) -> int:
        count = await self.redis.get(f"rl:{key}")
        return int(count) if count else 0
    
    async def increment(self, key: str, window_seconds: int) -> int:
        pipe = self.redis.pipeline()
        pipe.incr(f"rl:{key}")
        pipe.expire(f"rl:{key}", window_seconds)
        results = await pipe.execute()
        return results[0]
    
    async def set_count(self, key: str, count: int, ttl_seconds: int):
        await self.redis.setex(f"rl:{key}", ttl_seconds, count)
    
    async def get_timestamps(self, key: str) -> List[float]:
        timestamps = await self.redis.lrange(f"rl:ts:{key}", 0, -1)
        return [float(ts) for ts in timestamps]
    
    async def add_timestamp(self, key: str, timestamp: float, window_seconds: int):
        pipe = self.redis.pipeline()
        pipe.lpush(f"rl:ts:{key}", timestamp)
        pipe.expire(f"rl:ts:{key}", window_seconds + 1)
        await pipe.execute()
    
    async def cleanup_expired(self, key: str, before_timestamp: float):
        # Use Lua script for atomic cleanup
        script = """
        local key = KEYS[1]
        local cutoff = ARGV[1]
        local values = redis.call('lrange', key, 0, -1)
        redis.call('del', key)
        for i, v in ipairs(values) do
            if tonumber(v) > tonumber(cutoff) then
                redis.call('lpush', key, v)
            end
        end
        """
        await self.redis.eval(script, 1, f"rl:ts:{key}", before_timestamp)


class RateLimitAlgorithmImpl(ABC):
    """Base class for rate limiting algorithm implementations"""
    
    @abstractmethod
    async def check_limit(
        self, 
        key: str, 
        limit: RateLimit, 
        storage: RateLimitStorage
    ) -> RateLimitResult:
        """Check if request should be allowed"""
        pass


class TokenBucketAlgorithm(RateLimitAlgorithmImpl):
    """Token bucket rate limiting algorithm"""
    
    async def check_limit(
        self, 
        key: str, 
        limit: RateLimit, 
        storage: RateLimitStorage
    ) -> RateLimitResult:
        now = time.time()
        bucket_key = f"tb:{key}"
        
        # Get current bucket state
        current_tokens = await storage.get_count(bucket_key)
        max_tokens = limit.burst_limit or limit.limit
        
        # Calculate tokens to add
        last_refill_key = f"tb:last:{key}"
        last_refill = await storage.get_count(last_refill_key)
        if last_refill == 0:
            last_refill = now
        
        # Add tokens based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = int(time_elapsed * (limit.limit / limit.window_seconds))
        current_tokens = min(max_tokens, current_tokens + tokens_to_add)
        
        # Check if request can be served
        if current_tokens >= 1:
            current_tokens -= 1
            allowed = True
            remaining = current_tokens
        else:
            allowed = False
            remaining = 0
        
        # Update storage
        await storage.set_count(bucket_key, current_tokens, limit.window_seconds * 2)
        await storage.set_count(last_refill_key, int(now), limit.window_seconds * 2)
        
        # Calculate reset time
        if remaining == 0:
            reset_time = datetime.fromtimestamp(now + (1.0 / (limit.limit / limit.window_seconds)))
        else:
            reset_time = datetime.fromtimestamp(now + limit.window_seconds)
        
        return RateLimitResult(
            allowed=allowed,
            limit=limit.limit,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=1 if not allowed else None
        )


class SlidingWindowAlgorithm(RateLimitAlgorithmImpl):
    """Sliding window rate limiting algorithm"""
    
    async def check_limit(
        self, 
        key: str, 
        limit: RateLimit, 
        storage: RateLimitStorage
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - limit.window_seconds
        
        # Get current window count
        current_window_key = f"sw:{key}:{int(now // limit.window_seconds)}"
        prev_window_key = f"sw:{key}:{int(now // limit.window_seconds) - 1}"
        
        current_count = await storage.get_count(current_window_key)
        prev_count = await storage.get_count(prev_window_key)
        
        # Calculate weighted count
        time_in_current_window = now % limit.window_seconds
        weight = time_in_current_window / limit.window_seconds
        estimated_count = int(prev_count * (1 - weight) + current_count)
        
        # Check limit
        if estimated_count >= limit.limit:
            allowed = False
            remaining = 0
            retry_after = int(limit.window_seconds - time_in_current_window) + 1
        else:
            allowed = True
            remaining = limit.limit - estimated_count - 1
            retry_after = None
            
            # Increment current window
            await storage.increment(current_window_key, limit.window_seconds * 2)
        
        reset_time = datetime.fromtimestamp(
            (int(now // limit.window_seconds) + 1) * limit.window_seconds
        )
        
        return RateLimitResult(
            allowed=allowed,
            limit=limit.limit,
            remaining=max(0, remaining),
            reset_time=reset_time,
            retry_after=retry_after
        )


class SlidingWindowLogAlgorithm(RateLimitAlgorithmImpl):
    """Sliding window log rate limiting algorithm"""
    
    async def check_limit(
        self, 
        key: str, 
        limit: RateLimit, 
        storage: RateLimitStorage
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - limit.window_seconds
        
        # Cleanup old timestamps
        await storage.cleanup_expired(key, window_start)
        
        # Get current timestamps
        timestamps = await storage.get_timestamps(key)
        current_count = len(timestamps)
        
        # Check limit
        if current_count >= limit.limit:
            allowed = False
            remaining = 0
            # Calculate retry after based on oldest timestamp
            oldest_timestamp = min(timestamps) if timestamps else now
            retry_after = int(oldest_timestamp + limit.window_seconds - now) + 1
        else:
            allowed = True
            remaining = limit.limit - current_count - 1
            retry_after = None
            
            # Add current timestamp
            await storage.add_timestamp(key, now, limit.window_seconds)
        
        # Calculate reset time (when oldest entry expires)
        if timestamps:
            reset_time = datetime.fromtimestamp(min(timestamps) + limit.window_seconds)
        else:
            reset_time = datetime.fromtimestamp(now + limit.window_seconds)
        
        return RateLimitResult(
            allowed=allowed,
            limit=limit.limit,
            remaining=max(0, remaining),
            reset_time=reset_time,
            retry_after=retry_after
        )


class QuotaManager:
    """Manages long-term quotas (daily, monthly, etc.)"""
    
    def __init__(self, storage: RateLimitStorage):
        self.storage = storage
        self._quotas: Dict[str, Dict[str, Any]] = {}
    
    def add_quota(
        self, 
        name: str, 
        limit: int, 
        period_seconds: int, 
        client_patterns: Optional[List[str]] = None
    ):
        """
        Add a quota configuration.
        
        Args:
            name: Quota name
            limit: Request limit
            period_seconds: Period in seconds
            client_patterns: Client patterns to apply quota to
        """
        self._quotas[name] = {
            'limit': limit,
            'period_seconds': period_seconds,
            'client_patterns': client_patterns or ['*']
        }
    
    async def check_quota(self, client_id: str, quota_name: str) -> RateLimitResult:
        """
        Check if client is within quota.
        
        Args:
            client_id: Client identifier
            quota_name: Quota name to check
            
        Returns:
            Rate limit result
        """
        if quota_name not in self._quotas:
            # No quota configured, allow request
            return RateLimitResult(
                allowed=True,
                limit=float('inf'),
                remaining=float('inf'),
                reset_time=datetime.fromtimestamp(time.time() + 86400)
            )
        
        quota = self._quotas[quota_name]
        period_start = int(time.time() // quota['period_seconds']) * quota['period_seconds']
        
        key = f"quota:{quota_name}:{client_id}:{period_start}"
        current_usage = await self.storage.get_count(key)
        
        if current_usage >= quota['limit']:
            reset_time = datetime.fromtimestamp(period_start + quota['period_seconds'])
            return RateLimitResult(
                allowed=False,
                limit=quota['limit'],
                remaining=0,
                reset_time=reset_time,
                retry_after=int(reset_time.timestamp() - time.time())
            )
        
        # Increment usage
        await self.storage.increment(key, quota['period_seconds'])
        
        reset_time = datetime.fromtimestamp(period_start + quota['period_seconds'])
        return RateLimitResult(
            allowed=True,
            limit=quota['limit'],
            remaining=quota['limit'] - current_usage - 1,
            reset_time=reset_time
        )


class RateLimiter:
    """
    Main rate limiter class that coordinates different algorithms and storage.
    
    Provides rate limiting functionality with multiple algorithms and storage backends.
    """
    
    def __init__(self, storage: Optional[RateLimitStorage] = None):
        self.storage = storage or MemoryRateLimitStorage()
        self.quota_manager = QuotaManager(self.storage)
        
        # Algorithm implementations
        self._algorithms = {
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketAlgorithm(),
            RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowAlgorithm(),
            RateLimitAlgorithm.SLIDING_WINDOW_LOG: SlidingWindowLogAlgorithm()
        }
        
        # Rate limit configurations
        self._rate_limits: Dict[str, RateLimit] = {}
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'start_time': datetime.utcnow()
        }
    
    def add_rate_limit(self, rate_limit: RateLimit):
        """
        Add a rate limit configuration.
        
        Args:
            rate_limit: Rate limit configuration
        """
        self._rate_limits[rate_limit.name] = rate_limit
        logger.info(f"Added rate limit: {rate_limit.name}")
    
    def get_rate_limit(self, name: str) -> Optional[RateLimit]:
        """Get rate limit configuration by name"""
        return self._rate_limits.get(name)
    
    def list_rate_limits(self) -> List[str]:
        """List all rate limit names"""
        return list(self._rate_limits.keys())
    
    async def check_limit(
        self, 
        client_id: str, 
        endpoint: str = "", 
        api_key: str = "", 
        rate_limit_name: str = "default"
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Args:
            client_id: Client identifier
            endpoint: API endpoint
            api_key: API key
            rate_limit_name: Rate limit configuration to use
            
        Returns:
            Rate limit check result
        """
        self._stats['total_requests'] += 1
        
        rate_limit = self._rate_limits.get(rate_limit_name)
        if not rate_limit:
            # No rate limit configured, allow request
            self._stats['allowed_requests'] += 1
            return RateLimitResult(
                allowed=True,
                limit=float('inf'),
                remaining=float('inf'),
                reset_time=datetime.fromtimestamp(time.time() + 3600)
            )
        
        # Generate rate limit key
        key_parts = []
        if rate_limit.per_client:
            key_parts.append(f"client:{client_id}")
        if rate_limit.per_endpoint:
            key_parts.append(f"endpoint:{endpoint}")
        if rate_limit.per_api_key and api_key:
            key_parts.append(f"api_key:{api_key}")
        
        key = ":".join(key_parts) if key_parts else f"global:{rate_limit_name}"
        
        # Check rate limit using configured algorithm
        algorithm = self._algorithms[rate_limit.algorithm]
        result = await algorithm.check_limit(key, rate_limit, self.storage)
        
        # Add HTTP headers if configured
        if rate_limit.include_headers:
            result.headers.update({
                'X-RateLimit-Limit': str(result.limit),
                'X-RateLimit-Remaining': str(result.remaining),
                'X-RateLimit-Reset': str(int(result.reset_time.timestamp()))
            })
            
            if not result.allowed and rate_limit.retry_after_header and result.retry_after:
                result.headers['Retry-After'] = str(result.retry_after)
        
        # Update statistics
        if result.allowed:
            self._stats['allowed_requests'] += 1
        else:
            self._stats['blocked_requests'] += 1
        
        return result
    
    async def check_quota(self, client_id: str, quota_name: str = "default") -> RateLimitResult:
        """
        Check client quota.
        
        Args:
            client_id: Client identifier
            quota_name: Quota name to check
            
        Returns:
            Quota check result
        """
        return await self.quota_manager.check_quota(client_id, quota_name)
    
    def add_quota(
        self, 
        name: str, 
        limit: int, 
        period_seconds: int, 
        client_patterns: Optional[List[str]] = None
    ):
        """Add quota configuration"""
        self.quota_manager.add_quota(name, limit, period_seconds, client_patterns)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        uptime = datetime.utcnow() - self._stats['start_time']
        
        stats = self._stats.copy()
        stats.update({
            'uptime_seconds': uptime.total_seconds(),
            'configured_rate_limits': len(self._rate_limits),
            'rate_limit_names': list(self._rate_limits.keys()),
            'block_rate': (
                self._stats['blocked_requests'] / self._stats['total_requests'] * 100
                if self._stats['total_requests'] > 0 else 0
            )
        })
        
        return stats


# Pre-configured rate limiters
def create_default_rate_limiter() -> RateLimiter:
    """Create rate limiter with default configurations"""
    limiter = RateLimiter()
    
    # Add default rate limits
    limiter.add_rate_limit(RateLimit(
        name="default",
        limit=100,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    limiter.add_rate_limit(RateLimit(
        name="strict",
        limit=10,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW_LOG
    ))
    
    limiter.add_rate_limit(RateLimit(
        name="burst",
        limit=50,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst_limit=100
    ))
    
    # Add default quotas
    limiter.add_quota("daily", 10000, 86400)  # 10k requests per day
    limiter.add_quota("hourly", 1000, 3600)   # 1k requests per hour
    
    return limiter


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = create_default_rate_limiter()
    return _rate_limiter


def setup_rate_limiter(storage: Optional[RateLimitStorage] = None) -> RateLimiter:
    """Setup and return the global rate limiter"""
    global _rate_limiter
    _rate_limiter = RateLimiter(storage)
    return _rate_limiter