"""
Middleware components for the Korea Public API platform.

Provides request/response validation, logging, and monitoring.
"""

import time
import json
import logging
from typing import Callable, Any, Dict, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..shared.exceptions import DataValidationError, KoreanPublicAPIError
from ..shared.schemas import ErrorResponse

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """요청 데이터 검증 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        요청 데이터를 검증하고 로깅합니다.
        
        Args:
            request: HTTP 요청
            call_next: 다음 미들웨어 또는 엔드포인트
            
        Returns:
            HTTP 응답
        """
        # 요청 시작 시간 기록
        start_time = time.time()
        
        # 요청 로깅
        logger.info(f"Request: {request.method} {request.url.path}")
        
        try:
            # 요청 본문 읽기 (POST, PUT, PATCH) - 조심스럽게 처리
            if request.method in ["POST", "PUT", "PATCH"]:
                # 요청 스트림을 소비하지 않고 로깅만 수행
                # request.body()를 호출하면 스트림이 소비되어 FastAPI가 파싱할 수 없음
                logger.debug(f"Processing {request.method} request to {request.url.path}")
            
            # 다음 미들웨어 또는 엔드포인트 호출
            response = await call_next(request)
            
            # 응답 시간 계산
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # 응답 로깅
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 처리되지 않은 예외 로깅
            logger.exception(f"Unhandled exception in middleware: {str(e)}")
            
            # 에러 응답 생성
            from datetime import datetime
            error_response = ErrorResponse(
                success=False,
                status="error",
                error={
                    "type": "InternalServerError",
                    "message": "내부 서버 오류가 발생했습니다.",
                    "details": []
                },
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump()
            )
    
    def _sanitize_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        민감한 정보를 제거한 요청 데이터 반환
        
        Args:
            data: 원본 요청 데이터
            
        Returns:
            민감한 정보가 제거된 데이터
        """
        sensitive_fields = [
            'password', 'api_key', 'secret', 'token',
            'authorization', 'cookie', 'session'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_request_data(value)
            else:
                sanitized[key] = value
                
        return sanitized


class ResponseValidationMiddleware(BaseHTTPMiddleware):
    """응답 데이터 검증 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        응답 데이터를 검증하고 표준 형식으로 변환합니다.
        
        Args:
            request: HTTP 요청
            call_next: 다음 미들웨어 또는 엔드포인트
            
        Returns:
            HTTP 응답
        """
        response = await call_next(request)
        
        # API 엔드포인트만 처리
        if not request.url.path.startswith("/api/"):
            return response
        
        # 정적 파일이나 문서는 제외
        if request.url.path.endswith((".js", ".css", ".png", ".jpg", ".ico")):
            return response
        
        # OpenAPI 문서는 제외
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return response
        
        # 응답 본문 읽기
        if hasattr(response, "body_iterator"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
                
            try:
                # JSON 응답인 경우 검증
                if response.headers.get("content-type", "").startswith("application/json"):
                    json_body = json.loads(body.decode())
                    
                    # 표준 응답 형식 확인 (딕셔너리인 경우만)
                    if isinstance(json_body, dict):
                        if not self._is_standard_response(json_body):
                            logger.warning(
                                f"Non-standard response format for {request.url.path}: "
                                f"{list(json_body.keys())}"
                            )
                    else:
                        # 리스트나 다른 형태의 JSON 응답
                        logger.debug(
                            f"Non-dict JSON response for {request.url.path}: "
                            f"{type(json_body).__name__}"
                        )
                    
                    # 에러 응답인 경우 추가 검증 (딕셔너리인 경우만)
                    if response.status_code >= 400 and isinstance(json_body, dict):
                        if not all(key in json_body for key in ["success", "message"]):
                            logger.error(
                                f"Invalid error response format for {request.url.path}"
                            )
                
                # 새 응답 생성
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
            except json.JSONDecodeError:
                # JSON이 아닌 응답은 그대로 반환
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
        
        return response
    
    def _is_standard_response(self, data: Dict[str, Any]) -> bool:
        """
        표준 응답 형식인지 확인
        
        Args:
            data: 응답 데이터
            
        Returns:
            표준 형식인 경우 True
        """
        # 기본 응답 필드
        required_fields = ["success", "message"]
        
        # 페이지네이션 응답인 경우
        if "meta" in data and isinstance(data.get("meta"), dict):
            required_fields.extend(["data", "meta"])
            
        return all(field in data for field in required_fields)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 속도 제한 미들웨어"""
    
    def __init__(
        self,
        app: ASGIApp,
        calls_per_minute: int = 60,
        calls_per_hour: int = 1000
    ):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.request_history: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        API 호출 속도를 제한합니다.
        
        Args:
            request: HTTP 요청
            call_next: 다음 미들웨어 또는 엔드포인트
            
        Returns:
            HTTP 응답
        """
        # 클라이언트 IP 추출
        client_ip = request.client.host if request.client else "unknown"
        
        # API 엔드포인트만 속도 제한 적용
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        current_time = time.time()
        
        # 요청 기록 초기화
        if client_ip not in self.request_history:
            self.request_history[client_ip] = []
        
        # 오래된 요청 기록 제거
        self.request_history[client_ip] = [
            timestamp for timestamp in self.request_history[client_ip]
            if current_time - timestamp < 3600  # 1시간
        ]
        
        # 속도 제한 확인
        recent_requests = self.request_history[client_ip]
        
        # 분당 요청 수 확인
        minute_requests = sum(
            1 for timestamp in recent_requests
            if current_time - timestamp < 60
        )
        
        if minute_requests >= self.calls_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "요청 속도 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.calls_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 60))
                }
            )
        
        # 시간당 요청 수 확인
        if len(recent_requests) >= self.calls_per_hour:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "시간당 요청 한도를 초과했습니다.",
                    "error_code": "HOURLY_LIMIT_EXCEEDED",
                    "retry_after": 3600
                },
                headers={
                    "Retry-After": "3600",
                    "X-RateLimit-Limit": str(self.calls_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 3600))
                }
            )
        
        # 요청 기록 추가
        self.request_history[client_ip].append(current_time)
        
        # 다음 미들웨어 호출
        response = await call_next(request)
        
        # Rate limit 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.calls_per_minute - minute_requests - 1
        )
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """헬스체크 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        헬스체크 엔드포인트 처리
        
        Args:
            request: HTTP 요청
            call_next: 다음 미들웨어 또는 엔드포인트
            
        Returns:
            HTTP 응답
        """
        # 헬스체크 경로
        if request.url.path == "/health":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": time.time(),
                    "service": "Korean Public API Platform"
                }
            )
        
        return await call_next(request)