"""
Advanced rate limiting and request validation middleware.

Provides intelligent rate limiting with different strategies, request validation,
and DDoS protection for improved API security and performance.
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict, deque
import ipaddress
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from .cache import cache_manager
from .config import settings

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    ADAPTIVE = "adaptive"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests: int  # Number of requests
    window: int    # Time window in seconds
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_requests: Optional[int] = None  # For token bucket
    block_duration: int = 300  # Block duration in seconds when limit exceeded


@dataclass
class RequestMetrics:
    """Request metrics for adaptive rate limiting"""
    count: int = 0
    total_response_time: float = 0.0
    error_count: int = 0
    last_request_time: float = 0.0
    
    @property
    def avg_response_time(self) -> float:
        return self.total_response_time / self.count if self.count > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        return self.error_count / self.count if self.count > 0 else 0.0


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._memory_store: Dict[str, Any] = {}
        self._request_metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        self._blocked_clients: Dict[str, float] = {}  # client_id -> block_until_timestamp
        self._suspicious_ips: Dict[str, List[float]] = defaultdict(list)  # IP -> request timestamps
    
    def _get_cache_key(self, identifier: str, window_start: int = None) -> str:
        """Generate cache key for rate limiting"""
        if window_start is not None:
            return f"rate_limit:{identifier}:{window_start}"
        return f"rate_limit:{identifier}"
    
    def _get_current_window(self, timestamp: float = None) -> int:
        """Get current time window based on strategy"""
        if timestamp is None:
            timestamp = time.time()
        
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return int(timestamp // self.config.window)
        else:
            return int(timestamp)
    
    async def _check_fixed_window(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting"""
        current_window = self._get_current_window()
        cache_key = self._get_cache_key(identifier, current_window)
        
        try:
            # Try Redis first
            current_count = await cache_manager.aget(cache_key)
            if current_count is None:
                current_count = 0
            
            if current_count >= self.config.requests:
                return False, {
                    "current_requests": current_count,
                    "limit": self.config.requests,
                    "window": self.config.window,
                    "reset_time": (current_window + 1) * self.config.window
                }
            
            # Increment counter
            new_count = current_count + 1
            await cache_manager.aset(cache_key, new_count, self.config.window)
            
            return True, {
                "current_requests": new_count,
                "limit": self.config.requests,
                "remaining": self.config.requests - new_count,
                "window": self.config.window,
                "reset_time": (current_window + 1) * self.config.window
            }
            
        except Exception as e:
            logger.warning(f"Rate limiter cache error, using memory fallback: {e}")
            # Fallback to memory store
            if cache_key not in self._memory_store:
                self._memory_store[cache_key] = {"count": 0, "expires": time.time() + self.config.window}
            
            store_data = self._memory_store[cache_key]
            
            # Check if window expired
            if time.time() > store_data["expires"]:
                store_data = {"count": 0, "expires": time.time() + self.config.window}
                self._memory_store[cache_key] = store_data
            
            if store_data["count"] >= self.config.requests:
                return False, {
                    "current_requests": store_data["count"],
                    "limit": self.config.requests,
                    "window": self.config.window
                }
            
            store_data["count"] += 1
            
            return True, {
                "current_requests": store_data["count"],
                "limit": self.config.requests,
                "remaining": self.config.requests - store_data["count"],
                "window": self.config.window
            }
    
    async def _check_sliding_window(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting using Redis sorted sets"""
        current_time = time.time()
        window_start = current_time - self.config.window
        cache_key = self._get_cache_key(identifier)
        
        try:
            # Use Redis sorted set for sliding window
            if cache_manager.async_client:
                # Remove old entries
                await cache_manager.async_client.zremrangebyscore(
                    cache_key, 0, window_start
                )
                
                # Count current requests in window
                current_count = await cache_manager.async_client.zcard(cache_key)
                
                if current_count >= self.config.requests:
                    return False, {
                        "current_requests": current_count,
                        "limit": self.config.requests,
                        "window": self.config.window,
                        "retry_after": self.config.window
                    }
                
                # Add current request
                request_id = f"{current_time}:{hash(identifier)}"
                await cache_manager.async_client.zadd(cache_key, {request_id: current_time})
                await cache_manager.async_client.expire(cache_key, self.config.window + 1)
                
                return True, {
                    "current_requests": current_count + 1,
                    "limit": self.config.requests,
                    "remaining": self.config.requests - current_count - 1,
                    "window": self.config.window
                }
            
        except Exception as e:
            logger.warning(f"Sliding window rate limiter cache error: {e}")
        
        # Fallback to memory store with deque
        if cache_key not in self._memory_store:
            self._memory_store[cache_key] = deque()
        
        request_times = self._memory_store[cache_key]
        
        # Remove old requests
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        if len(request_times) >= self.config.requests:
            return False, {
                "current_requests": len(request_times),
                "limit": self.config.requests,
                "window": self.config.window,
                "retry_after": self.config.window - (current_time - request_times[0])
            }
        
        request_times.append(current_time)
        
        return True, {
            "current_requests": len(request_times),
            "limit": self.config.requests,
            "remaining": self.config.requests - len(request_times),
            "window": self.config.window
        }
    
    async def _check_token_bucket(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting"""
        current_time = time.time()
        cache_key = self._get_cache_key(identifier)
        
        try:
            bucket_data = await cache_manager.aget(cache_key)
            if bucket_data is None:
                bucket_data = {
                    "tokens": self.config.requests,
                    "last_refill": current_time
                }
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = current_time - bucket_data["last_refill"]
            tokens_to_add = (time_elapsed * self.config.requests) / self.config.window
            
            # Refill tokens (up to burst limit if configured)
            max_tokens = self.config.burst_requests or self.config.requests
            bucket_data["tokens"] = min(max_tokens, bucket_data["tokens"] + tokens_to_add)
            bucket_data["last_refill"] = current_time
            
            if bucket_data["tokens"] < 1:
                await cache_manager.aset(cache_key, bucket_data, self.config.window)
                return False, {
                    "current_tokens": bucket_data["tokens"],
                    "limit": self.config.requests,
                    "retry_after": self.config.window / self.config.requests
                }
            
            # Consume one token
            bucket_data["tokens"] -= 1
            await cache_manager.aset(cache_key, bucket_data, self.config.window)
            
            return True, {
                "current_tokens": bucket_data["tokens"],
                "limit": self.config.requests,
                "remaining": int(bucket_data["tokens"]),
                "refill_rate": self.config.requests / self.config.window
            }
            
        except Exception as e:
            logger.warning(f"Token bucket rate limiter cache error: {e}")
            # Fallback to fixed window
            return await self._check_fixed_window(identifier)
    
    async def _check_adaptive(self, identifier: str, response_time: float = None, 
                            is_error: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Adaptive rate limiting based on system performance"""
        metrics = self._request_metrics[identifier]
        current_time = time.time()
        
        # Update metrics
        metrics.count += 1
        if response_time is not None:
            metrics.total_response_time += response_time
        if is_error:
            metrics.error_count += 1
        metrics.last_request_time = current_time
        
        # Adjust limits based on performance
        base_limit = self.config.requests
        
        # Reduce limit if high error rate or slow responses
        if metrics.error_rate > 0.1:  # More than 10% errors
            adjusted_limit = int(base_limit * 0.5)
        elif metrics.avg_response_time > 2.0:  # Slow responses
            adjusted_limit = int(base_limit * 0.7)
        else:
            adjusted_limit = base_limit
        
        # Use sliding window with adjusted limit
        temp_config = RateLimitConfig(
            requests=adjusted_limit,
            window=self.config.window,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        temp_limiter = RateLimiter(temp_config)
        
        allowed, info = await temp_limiter._check_sliding_window(identifier)
        info["adaptive_limit"] = adjusted_limit
        info["original_limit"] = base_limit
        info["metrics"] = {
            "avg_response_time": metrics.avg_response_time,
            "error_rate": metrics.error_rate,
            "total_requests": metrics.count
        }
        
        return allowed, info
    
    async def check_rate_limit(self, identifier: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed based on configured strategy"""
        current_time = time.time()
        
        # Check if client is blocked
        if identifier in self._blocked_clients:
            if current_time < self._blocked_clients[identifier]:
                return False, {
                    "blocked": True,
                    "block_remaining": self._blocked_clients[identifier] - current_time,
                    "reason": "Client temporarily blocked due to rate limit violations"
                }
            else:
                # Block expired, remove from blocked list
                del self._blocked_clients[identifier]
        
        # Apply rate limiting based on strategy
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            allowed, info = await self._check_fixed_window(identifier)
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            allowed, info = await self._check_sliding_window(identifier)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            allowed, info = await self._check_token_bucket(identifier)
        elif self.config.strategy == RateLimitStrategy.ADAPTIVE:
            allowed, info = await self._check_adaptive(identifier, **kwargs)
        else:
            # Default to sliding window
            allowed, info = await self._check_sliding_window(identifier)
        
        # If rate limit exceeded, block client
        if not allowed:
            self._blocked_clients[identifier] = current_time + self.config.block_duration
            info["blocked_until"] = self._blocked_clients[identifier]
        
        return allowed, info
    
    def is_suspicious_behavior(self, client_ip: str) -> bool:
        """Detect suspicious behavior patterns"""
        current_time = time.time()
        window = 60  # 1 minute window
        
        # Clean old entries
        self._suspicious_ips[client_ip] = [
            timestamp for timestamp in self._suspicious_ips[client_ip]
            if current_time - timestamp < window
        ]
        
        # Add current request
        self._suspicious_ips[client_ip].append(current_time)
        
        # Check for suspicious patterns
        requests_in_window = len(self._suspicious_ips[client_ip])
        
        # More than 200 requests per minute is suspicious
        if requests_in_window > 200:
            logger.warning(f"Suspicious behavior detected from IP {client_ip}: {requests_in_window} requests/min")
            return True
        
        # Check for rapid burst (more than 50 requests in 10 seconds)
        recent_requests = [
            timestamp for timestamp in self._suspicious_ips[client_ip]
            if current_time - timestamp < 10
        ]
        
        if len(recent_requests) > 50:
            logger.warning(f"Burst pattern detected from IP {client_ip}: {len(recent_requests)} requests in 10s")
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        current_time = time.time()
        
        # Clean expired blocks
        expired_blocks = [
            client_id for client_id, block_until in self._blocked_clients.items()
            if current_time > block_until
        ]
        for client_id in expired_blocks:
            del self._blocked_clients[client_id]
        
        return {
            "strategy": self.config.strategy.value,
            "config": {
                "requests": self.config.requests,
                "window": self.config.window,
                "block_duration": self.config.block_duration
            },
            "stats": {
                "blocked_clients": len(self._blocked_clients),
                "memory_store_size": len(self._memory_store),
                "tracked_metrics": len(self._request_metrics),
                "suspicious_ips": len(self._suspicious_ips)
            }
        }


class RateLimitManager:
    """Manage multiple rate limiters for different endpoints"""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self.default_config = RateLimitConfig(
            requests=100,  # 100 requests
            window=3600,   # per hour
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
    
    def add_limiter(self, endpoint: str, config: RateLimitConfig) -> None:
        """Add rate limiter for specific endpoint"""
        self.limiters[endpoint] = RateLimiter(config)
    
    def get_limiter(self, endpoint: str) -> RateLimiter:
        """Get rate limiter for endpoint (create default if not exists)"""
        if endpoint not in self.limiters:
            self.limiters[endpoint] = RateLimiter(self.default_config)
        return self.limiters[endpoint]
    
    def get_client_identifier(self, request: Request) -> str:
        """Generate client identifier from request"""
        # Use X-Forwarded-For if present (behind proxy)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user agent for better identification
        user_agent = request.headers.get("User-Agent", "unknown")
        user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        
        # Check if it's an authenticated user
        auth_header = request.headers.get("Authorization", "")
        if auth_header:
            # Use hash of auth token for authenticated users
            auth_hash = hashlib.md5(auth_header.encode()).hexdigest()[:12]
            return f"user:{auth_hash}"
        
        return f"ip:{client_ip}:{user_agent_hash}"
    
    def is_whitelisted_ip(self, ip: str) -> bool:
        """Check if IP is whitelisted (should skip rate limiting)"""
        whitelist = getattr(settings, 'rate_limit_whitelist', [])
        
        try:
            client_ip = ipaddress.ip_address(ip)
            for whitelisted in whitelist:
                if "/" in whitelisted:
                    # CIDR notation
                    if client_ip in ipaddress.ip_network(whitelisted, strict=False):
                        return True
                else:
                    # Single IP
                    if client_ip == ipaddress.ip_address(whitelisted):
                        return True
        except Exception:
            # If IP parsing fails, check direct string match
            return ip in whitelist
        
        return False


# Global rate limit manager
rate_limit_manager = RateLimitManager()

# Configure default rate limiters
rate_limit_manager.add_limiter("auth", RateLimitConfig(
    requests=10,  # 10 login attempts
    window=900,   # per 15 minutes
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    block_duration=600  # Block for 10 minutes
))

rate_limit_manager.add_limiter("api", RateLimitConfig(
    requests=1000,  # 1000 API requests
    window=3600,    # per hour
    strategy=RateLimitStrategy.SLIDING_WINDOW
))

rate_limit_manager.add_limiter("data_fetch", RateLimitConfig(
    requests=100,  # 100 data fetch requests
    window=3600,   # per hour
    strategy=RateLimitStrategy.TOKEN_BUCKET,
    burst_requests=150  # Allow burst up to 150
))


# Middleware and decorators
def rate_limit(endpoint: str = "default", config: Optional[RateLimitConfig] = None):
    """Decorator for rate limiting functions"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                # No request object found, skip rate limiting
                return await func(*args, **kwargs)
            
            # Set up rate limiter
            if config is not None:
                rate_limit_manager.add_limiter(endpoint, config)
            
            limiter = rate_limit_manager.get_limiter(endpoint)
            client_id = rate_limit_manager.get_client_identifier(request)
            
            # Skip rate limiting for whitelisted IPs
            client_ip = client_id.split(":")[1] if ":" in client_id else client_id
            if rate_limit_manager.is_whitelisted_ip(client_ip):
                return await func(*args, **kwargs)
            
            # Check for suspicious behavior
            if limiter.is_suspicious_behavior(client_ip):
                logger.warning(f"Blocking suspicious IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Suspicious behavior detected. Access temporarily restricted."
                )
            
            # Check rate limit
            start_time = time.time()
            allowed, info = await limiter.check_rate_limit(client_id)
            
            if not allowed:
                logger.info(f"Rate limit exceeded for {client_id}: {info}")
                
                # Prepare response headers
                headers = {
                    "X-RateLimit-Limit": str(limiter.config.requests),
                    "X-RateLimit-Window": str(limiter.config.window),
                    "X-RateLimit-Remaining": "0"
                }
                
                if "retry_after" in info:
                    headers["Retry-After"] = str(int(info["retry_after"]))
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers=headers
                )
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Update metrics for adaptive rate limiting
                if limiter.config.strategy == RateLimitStrategy.ADAPTIVE:
                    await limiter.check_rate_limit(client_id, response_time=response_time, is_error=False)
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                
                # Update metrics for adaptive rate limiting
                if limiter.config.strategy == RateLimitStrategy.ADAPTIVE:
                    await limiter.check_rate_limit(client_id, response_time=response_time, is_error=True)
                
                raise e
        
        return wrapper
    return decorator


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting"""
    # Skip rate limiting for health checks and static files
    if request.url.path in ["/health", "/metrics", "/favicon.ico"] or request.url.path.startswith("/static"):
        return await call_next(request)
    
    # Determine endpoint for rate limiting
    endpoint = "api"  # Default endpoint
    
    if request.url.path.startswith("/auth"):
        endpoint = "auth"
    elif request.url.path.startswith("/api/data"):
        endpoint = "data_fetch"
    
    limiter = rate_limit_manager.get_limiter(endpoint)
    client_id = rate_limit_manager.get_client_identifier(request)
    
    # Skip rate limiting for whitelisted IPs
    client_ip = client_id.split(":")[1] if ":" in client_id else client_id
    if rate_limit_manager.is_whitelisted_ip(client_ip):
        return await call_next(request)
    
    # Check for suspicious behavior
    if limiter.is_suspicious_behavior(client_ip):
        logger.warning(f"Blocking suspicious IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Suspicious behavior detected. Access temporarily restricted."}
        )
    
    # Check rate limit
    start_time = time.time()
    allowed, info = await limiter.check_rate_limit(client_id)
    
    if not allowed:
        logger.info(f"Rate limit exceeded for {client_id} on {endpoint}: {info}")
        
        headers = {
            "X-RateLimit-Limit": str(limiter.config.requests),
            "X-RateLimit-Window": str(limiter.config.window),
            "X-RateLimit-Remaining": "0"
        }
        
        if "retry_after" in info:
            headers["Retry-After"] = str(int(info["retry_after"]))
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again later."},
            headers=headers
        )
    
    # Process request
    try:
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limiter.config.requests)
        response.headers["X-RateLimit-Window"] = str(limiter.config.window)
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        
        # Update metrics for adaptive rate limiting
        if limiter.config.strategy == RateLimitStrategy.ADAPTIVE:
            is_error = response.status_code >= 400
            await limiter.check_rate_limit(client_id, response_time=response_time, is_error=is_error)
        
        return response
        
    except Exception as e:
        response_time = time.time() - start_time
        
        # Update metrics for adaptive rate limiting
        if limiter.config.strategy == RateLimitStrategy.ADAPTIVE:
            await limiter.check_rate_limit(client_id, response_time=response_time, is_error=True)
        
        raise e


# Convenience functions
def get_rate_limit_stats() -> Dict[str, Any]:
    """Get comprehensive rate limiting statistics"""
    return {
        "limiters": {
            endpoint: limiter.get_stats()
            for endpoint, limiter in rate_limit_manager.limiters.items()
        },
        "total_limiters": len(rate_limit_manager.limiters)
    }