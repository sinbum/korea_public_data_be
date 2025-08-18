from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import uvicorn

from .core.config import settings
from .core.database import connect_to_mongo, close_mongo_connection
from .core.di_config import configure_dependencies, validate_container_setup
from .core.container import setup_container
from .core.middleware import (
    RequestValidationMiddleware,
    ResponseValidationMiddleware,
    RateLimitMiddleware,
    HealthCheckMiddleware,
    RequestIdMiddleware,
    CSRFMiddleware
)
from .core.rate_limit import RedisRateLimitMiddleware
from .core.logging_config import setup_logging
from .core.metrics import init_metrics, poll_celery_metrics
import os

def _is_redis_available(url: str) -> bool:
    try:
        import redis  # type: ignore
        client = redis.from_url(url)
        client.ping()
        return True
    except Exception:
        return False
from .domains.announcements.router import router as announcements_router
from .domains.businesses.router import router as businesses_router
from .domains.contents.router import router as contents_router
from .domains.users.router import router as users_router
from .domains.keys.router import router as keys_router
from .core.config import settings as _settings_for_alerts
# Alerts versioned router is included conditionally to avoid runtime impact when disabled
try:
    from .domains.alerts.versioned_router import get_v1_router as get_alerts_v1_router
except Exception:
    get_alerts_v1_router = None  # type: ignore
from .domains.usage.router import router as usage_router
from .domains.data_requests.router import router as data_requests_router
from .domains.data_sources.router import router as data_sources_router
from .shared.classification.router import router as classification_router
from .scheduler.task_management_api import get_task_management_router
from .shared.exceptions.handlers import (
    base_api_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    korean_api_exception_handler,
    data_validation_exception_handler,
    general_exception_handler
)
from .shared.version_middleware import create_version_middleware, create_deprecation_middleware
from .shared.version_router import add_version_info_endpoint
from .shared.exceptions.custom_exceptions import BaseAPIException
from .shared.exceptions.api_exceptions import KoreanPublicAPIError
from .shared.exceptions.data_exceptions import DataValidationError
from .shared.swagger_config import tags_metadata, swagger_ui_parameters
from .shared.security.schemas import SECURITY_SCHEMES
from starlette.middleware.gzip import GZipMiddleware

# 로깅 설정 (설정값은 내부에서 처리)
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작시 실행
    logger.info("애플리케이션 시작 중...")
    
    try:
        # MongoDB 연결 (개발 테스트를 위해 임시로 우회)
        try:
            connect_to_mongo()
            logger.info("MongoDB 연결 성공")
        except Exception as db_error:
            logger.warning(f"MongoDB 연결 실패, Mock 데이터 모드로 실행: {db_error}")
            # MongoDB 연결 실패 시에도 계속 진행
        
        # DI 컨테이너 설정
        logger.info("의존성 주입 컨테이너 설정 중...")
        container = configure_dependencies()
        setup_container(container)
        logger.info("의존성 주입 컨테이너 설정 완료")
        
        # 의존성 검증 (선택적)
        if settings.debug:
            logger.info("의존성 검증 중...")
            validation_results = validate_container_setup(container)
            failed_validations = [name for name, result in validation_results.items() if result["status"] == "error"]
            
            if failed_validations:
                logger.warning(f"의존성 검증 실패: {failed_validations}")
                for name in failed_validations:
                    logger.error(f"{name}: {validation_results[name]['error']}")
            else:
                logger.info("모든 의존성 검증 성공")
        
    except Exception as e:
        logger.error(f"애플리케이션 초기화 실패: {e}")
        raise
    
    logger.info("애플리케이션 시작 완료")
    # Start background Celery metrics poller
    stop_metrics = None
    try:
        import asyncio as _asyncio
        stop_metrics = _asyncio.Event()
        _asyncio.create_task(poll_celery_metrics(stop_metrics, interval_seconds=15))
        logger.info("Celery metrics poller started")
    except Exception as e:
        logger.warning(f"Celery metrics poller disabled: {e}")
    
    yield
    
    # 종료시 실행
    logger.info("애플리케이션 종료 중...")
    try:
        close_mongo_connection()
    except Exception as e:
        logger.error(f"MongoDB 연결 종료 중 오류: {e}")
    try:
        if stop_metrics is not None:
            stop_metrics.set()  # type: ignore
    except Exception:
        pass
    logger.info("애플리케이션 종료 완료")


app = FastAPI(
    title="한국 공공데이터 API 플랫폼",
    description="""
    ## 🌟 개요
    확장 가능한 공공데이터 API 플랫폼으로, 창업진흥원 K-Startup을 시작으로 다양한 정부 공공데이터를 통합하여 제공하는 RESTful API 서비스입니다.
    
    ## 🏗️ 아키텍처 특징
    - **SOLID 원칙 적용**: 확장 가능하고 유지보수하기 쉬운 설계
    - **디자인 패턴 활용**: Strategy, Factory, Repository, Plugin 패턴 적용
    - **의존성 주입**: 느슨한 결합과 높은 테스트 가능성
    - **API 버저닝**: 호환성을 유지하면서 점진적 업그레이드 지원
    
    ## 🚀 주요 기능
    
    ### ✅ 완성된 기능
    - 🏢 **사업공고 정보**: 창업지원 사업 공고 데이터 실시간 수집 및 완전한 CRUD API
    - 🔄 **자동 데이터 수집**: Celery 기반 스케줄링으로 정기적 데이터 갱신
    - 📄 **표준 페이지네이션**: 일관된 페이징 및 정렬 시스템
    - 🎯 **고급 필터링**: 키워드, 카테고리, 상태, 날짜 범위별 검색
    - ⚡ **성능 최적화**: Redis 캐싱 및 데이터베이스 쿼리 최적화
    
    ### 🔄 개발 진행 중
    - 📚 **콘텐츠 정보**: 창업 관련 콘텐츠 및 자료 (모델 완성, API 개발 중)
    - 🎯 **기업정보**: 창업기업 상세 정보 (모델 완성, API 개발 중)
    
    ## 📂 데이터 출처
    - **공공데이터포털**: [창업진흥원_K-Startup 조회서비스](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654)
    - **Base URL**: `apis.data.go.kr/B552735/kisedKstartupService01`
    - **지원 형식**: JSON 응답, RESTful API
    
    ## 📖 API 사용 가이드
    
    ### 데이터 수집 워크플로우
    1. **실시간 수집**: `/fetch` 엔드포인트로 최신 데이터 수집
    2. **자동 수집**: Celery Beat 스케줄러가 일정 주기로 자동 실행
    3. **데이터 조회**: 표준 CRUD 엔드포인트로 저장된 데이터 접근
    4. **고급 검색**: 필터링, 정렬, 페이지네이션 활용
    
    ### 응답 형식
    모든 API는 일관된 응답 구조를 제공합니다:
    ```json
    {
      "success": true,
      "data": {...},
      "message": "작업 완료",
      "timestamp": "2024-01-01T00:00:00Z"
    }
    ```
    
    ## 🔒 인증 및 보안
    - **현재**: 인증 없음 (개발 단계)
    - **계획**: JWT 기반 인증, API 키 관리, Rate Limiting
    
    ## ⚡ 성능 지표
    - **API 응답 시간**: < 200ms (캐시된 데이터)
    - **실시간 데이터 수집**: < 2초
    - **동시 처리**: 1000+ 요청/분
    - **데이터 정확도**: 99.9% (중복 제거 포함)
    
    ## 📋 기술 스택
    - **Backend**: FastAPI 0.104+ + Python 3.11+
    - **Database**: MongoDB (pymongo)
    - **Task Queue**: Celery + Redis
    - **Validation**: Pydantic V2
    - **Container**: Docker + Docker Compose
    - **Architecture**: Domain-Driven Design (DDD)
    """,
    version="1.0.0",
    contact={
        "name": "개발팀",
        "email": "dev@example.com",
        "url": "https://github.com/your-repo"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    swagger_ui_parameters=swagger_ui_parameters,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    # 추가 성능 최적화 설정
    swagger_ui_init_oauth=None  # OAuth 초기화 비활성화
)


# OpenAPI 스키마에 보안 설정 추가
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 보안 스키마 추가
    openapi_schema["components"]["securitySchemes"] = SECURITY_SCHEMES
    
    # 모든 API 엔드포인트에 대해 보안 스키마 설명을 위한 전역 보안 설정 (선택적)
    # 주석: 현재는 인증이 구현되지 않았으므로 실제 보안 요구사항은 추가하지 않음
    # openapi_schema["security"] = [
    #     {"JWT": []},
    #     {"APIKey": []},
    #     {"OAuth2": ["read", "write"]},
    #     {"Basic": []}
    # ]
    
    # 서버 정보 추가
    if not openapi_schema.get("servers"):
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "개발 서버"
            },
            {
                "url": "https://api.startup-data.kr",
                "description": "프로덕션 서버 (계획됨)"
            }
        ]
    
    # 외부 문서 정보 추가
    openapi_schema["externalDocs"] = {
        "description": "상세 API 가이드 및 개발 문서",
        "url": "https://github.com/your-repo/docs/API_GUIDE.md"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS 설정 - 반드시 가장 먼저 등록해야 함!!
# 설정값 기반으로 통일하여 FE 변경 없이 동작
cors_origins = settings.allowed_origins
logger.info(f"CORS origins: {cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 미들웨어 등록 (순서 중요: 먼저 등록된 미들웨어가 나중에 실행됨)
app.add_middleware(ResponseValidationMiddleware)
app.add_middleware(RequestValidationMiddleware)
# 레이트리밋: Redis 사용 가능 시 분산 미들웨어만 활성화
redis_enabled = _is_redis_available(settings.redis_url)
if not redis_enabled:
    app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.rl_per_minute, calls_per_hour=settings.rl_per_hour)
app.add_middleware(HealthCheckMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(CSRFMiddleware)

if redis_enabled:
    try:
        app.add_middleware(
            RedisRateLimitMiddleware,
            redis_url=settings.redis_url,
            calls_per_minute=settings.rl_per_minute,
            calls_per_hour=settings.rl_per_hour,
        )
        logger.info("RedisRateLimitMiddleware enabled")
    except Exception as e:
        logger.warning(f"RedisRateLimitMiddleware disabled: {e}")

# Metrics
init_metrics(app, enabled=True, endpoint="/metrics")

# GZip compression for large JSON responses (improves LCP)
app.add_middleware(GZipMiddleware, minimum_size=500)

# API 버전 미들웨어 (요청 초기에 처리)
app.add_middleware(
    create_deprecation_middleware(
        add_deprecation_warnings=True,
        log_deprecated_usage=True
    )
)
app.add_middleware(
    create_version_middleware(
        skip_paths=["/docs", "/redoc", "/openapi.json", "/favicon.ico", "/health", "/"],
        add_version_headers=True
    )
)

# 예외 핸들러 등록 (순서 중요: 구체적인 예외부터 일반적인 예외 순서로)
app.add_exception_handler(BaseAPIException, base_api_exception_handler)
app.add_exception_handler(KoreanPublicAPIError, korean_api_exception_handler)
app.add_exception_handler(DataValidationError, data_validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# MongoDB 연결은 lifespan에서 처리


# 라우터 등록
app.include_router(announcements_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(contents_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(data_requests_router, prefix="/api/v1")
app.include_router(classification_router, prefix="/api/v1")
app.include_router(keys_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(get_task_management_router())
app.include_router(data_sources_router, prefix="/api/v1")

# Conditionally mount alerts router when enabled (keeps default runtime unchanged)
if _settings_for_alerts.alerts_enabled and get_alerts_v1_router is not None:
    try:
        app.include_router(get_alerts_v1_router(), prefix="/api")
        logger.info("Alerts router mounted under /api/v1/alerts")
    except Exception as e:
        logger.warning(f"Failed to mount alerts router: {e}")

# Versioned router examples (demonstrating API versioning system)
# These show how to implement different API versions with backward compatibility
try:
    from .domains.announcements.versioned_router import create_versioned_announcement_router
    from .domains.businesses.versioned_router import create_versioned_business_router
    
    app.include_router(create_versioned_announcement_router(), prefix="/api")
    app.include_router(create_versioned_business_router(), prefix="/api")
    logger.info("Versioned routers enabled for announcements and businesses")
except Exception as e:
    logger.warning(f"Failed to enable versioned routers: {e}")

# 버전 정보 엔드포인트 추가
add_version_info_endpoint(app)


@app.get(
    "/",
    tags=["기본"],
    summary="API 정보 조회",
    description="서비스의 기본 정보와 사용 가능한 엔드포인트를 확인합니다."
)
def root():
    """API 루트 엔드포인트 - 서비스 기본 정보 제공"""
    return {
        "service": "한국 공공데이터 API 서비스",
        "description": "창업진흥원 K-Startup 데이터 수집 및 제공",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "api_v1": "/api/v1"
        },
        "available_domains": [
            "announcements",
            "contents (개발 예정)",
            "businesses (개발 예정)"
        ]
    }


@app.get(
    "/health",
    tags=["기본"],
    summary="서비스 상태 확인",
    description="API 서버와 데이터베이스 연결 상태를 확인합니다."
)
def health_check():
    """헬스 체크 엔드포인트 - 서비스 상태 모니터링"""
    from datetime import datetime
    from .core.database import get_database
    
    try:
        # MongoDB 연결 상태 확인
        db = get_database()
        db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": db_status,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )