"""
In-memory caching module for API responses.

Provides a simple LRU cache implementation for caching frequently
accessed data to reduce database load and improve response times.
"""

import time
import json
import hashlib
from typing import Any, Optional, Dict, Callable
from collections import OrderedDict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU (Least Recently Used) cache implementation"""
    
    def __init__(self, max_size: int = 128, ttl: int = 300):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live in seconds (default 5 minutes)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
            
        if self._is_expired(key):
            self.delete(key)
            return None
            
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)
        
        self.cache[key] = value
        self.cache.move_to_end(key)
        self.timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": self.size(),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "keys": list(self.cache.keys())[:10]  # Show first 10 keys
        }


# Global cache instances for different purposes
announcement_cache = LRUCache(max_size=256, ttl=60)  # 1 minute TTL for announcements
detail_cache = LRUCache(max_size=128, ttl=300)  # 5 minutes TTL for details
search_cache = LRUCache(max_size=64, ttl=30)  # 30 seconds TTL for search results


def cache_key_generator(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = {
        "args": args,
        "kwargs": kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(cache_instance: LRUCache, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        cache_instance: Cache instance to use
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{cache_key_generator(*args, **kwargs)}"
            
            # Check cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache_instance.set(cache_key, result)
            logger.debug(f"Cache miss for {func.__name__}, cached with key {cache_key}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{cache_key_generator(*args, **kwargs)}"
            
            # Check cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result)
            logger.debug(f"Cache miss for {func.__name__}, cached with key {cache_key}")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_announcement_cache():
    """Invalidate announcement-related caches"""
    announcement_cache.clear()
    search_cache.clear()
    logger.info("Announcement caches invalidated")


def invalidate_detail_cache(announcement_id: str = None):
    """Invalidate detail cache for specific announcement or all"""
    if announcement_id:
        # Remove specific announcement from cache
        keys_to_remove = [
            key for key in detail_cache.cache.keys() 
            if announcement_id in key
        ]
        for key in keys_to_remove:
            detail_cache.delete(key)
        logger.info(f"Detail cache invalidated for announcement {announcement_id}")
    else:
        detail_cache.clear()
        logger.info("All detail caches invalidated")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    return {
        "announcement_cache": announcement_cache.stats(),
        "detail_cache": detail_cache.stats(),
        "search_cache": search_cache.stats()
    }