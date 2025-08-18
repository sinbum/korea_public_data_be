"""
Redis 캐싱 서비스 for Announcements
"""
import json
import hashlib
from typing import Optional, Any, Dict
from datetime import timedelta
import redis
import logging
from ...core.config import settings

logger = logging.getLogger(__name__)

class AnnouncementCacheService:
    """Redis 기반 공고 캐싱 서비스"""
    
    def __init__(self):
        """Redis 클라이언트 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # 연결 테스트
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache service initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis_client = None
            self.enabled = False
    
    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        # 파라미터를 정렬하여 일관된 키 생성
        sorted_params = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
        return f"{prefix}:{param_hash}"
    
    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """캐시된 응답 조회"""
        if not self.enabled:
            return None
            
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for key: {cache_key}")
                return json.loads(cached_data)
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None
    
    def set_cached_response(
        self, 
        cache_key: str, 
        data: Dict, 
        ttl_seconds: int = 60
    ) -> bool:
        """응답 캐싱"""
        if not self.enabled:
            return False
            
        try:
            serialized_data = json.dumps(data, ensure_ascii=False, default=str)
            self.redis_client.setex(
                cache_key,
                ttl_seconds,
                serialized_data
            )
            logger.debug(f"Cached response for key: {cache_key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def invalidate_cache(self, pattern: str = "announcements:*") -> int:
        """캐시 무효화"""
        if not self.enabled:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0
    
    def get_announcements_list_cache(
        self, 
        page: int, 
        size: int,
        **filters
    ) -> Optional[Dict]:
        """공고 목록 캐시 조회"""
        params = {
            "page": page,
            "size": size,
            **filters
        }
        cache_key = self._generate_cache_key("announcements:list", params)
        return self.get_cached_response(cache_key)
    
    def set_announcements_list_cache(
        self,
        page: int,
        size: int,
        data: Dict,
        ttl_seconds: int = 60,
        **filters
    ) -> bool:
        """공고 목록 캐싱"""
        params = {
            "page": page,
            "size": size,
            **filters
        }
        cache_key = self._generate_cache_key("announcements:list", params)
        return self.set_cached_response(cache_key, data, ttl_seconds)
    
    def get_announcement_detail_cache(self, announcement_id: str) -> Optional[Dict]:
        """공고 상세 캐시 조회"""
        cache_key = f"announcements:detail:{announcement_id}"
        return self.get_cached_response(cache_key)
    
    def set_announcement_detail_cache(
        self,
        announcement_id: str,
        data: Dict,
        ttl_seconds: int = 300  # 상세는 5분 캐싱
    ) -> bool:
        """공고 상세 캐싱"""
        cache_key = f"announcements:detail:{announcement_id}"
        return self.set_cached_response(cache_key, data, ttl_seconds)

# 싱글톤 인스턴스
announcement_cache_service = AnnouncementCacheService()