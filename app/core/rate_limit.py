import time
import logging
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None  # type: ignore


logger = logging.getLogger(__name__)


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Distributed rate limit middleware backed by Redis.

    Falls back to allowing requests if Redis is not available.
    """

    def __init__(
        self,
        app,
        redis_url: str,
        calls_per_minute: int = 60,
        calls_per_hour: int = 1000,
        key_prefix: str = "rl",
    ):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.key_prefix = key_prefix

        self.client: Optional["redis.Redis"] = None
        if redis is not None:
            try:
                self.client = redis.from_url(redis_url, decode_responses=True)
                # basic ping test
                self.client.ping()
                logger.info("RedisRateLimitMiddleware connected to Redis")
            except Exception as e:  # pragma: no cover
                logger.warning(f"Redis unavailable for rate limit: {e}")
                self.client = None
        else:  # pragma: no cover
            logger.warning("redis-py not installed; Redis rate limit disabled")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = int(time.time())

        # If no Redis, allow request and continue
        if self.client is None:
            return await call_next(request)

        minute_key = f"{self.key_prefix}:m:{client_ip}:{now // 60}"
        hour_key = f"{self.key_prefix}:h:{client_ip}:{now // 3600}"

        try:
            pipe = self.client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # 2 minutes TTL
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600 + 60)  # 1h+ TTL
            minute_count, _, hour_count, _ = pipe.execute()

            if minute_count > self.calls_per_minute:
                retry_after = 60 - (now % 60)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "요청 속도 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.calls_per_minute),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            if hour_count > self.calls_per_hour:
                retry_after = 3600 - (now % 3600)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "시간당 요청 한도를 초과했습니다.",
                        "error_code": "HOURLY_LIMIT_EXCEEDED",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.calls_per_hour),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        except Exception as e:  # pragma: no cover
            logger.warning(f"Redis rate limit error: {e}")
            # Fail open: allow request if Redis errors
            return await call_next(request)

        response = await call_next(request)
        return response


