from fastapi import FastAPI, HTTPException
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
from .domains.announcements.router import router as announcements_router
from .domains.businesses.router import router as businesses_router
from .domains.contents.router import router as contents_router
from .domains.statistics.router import router as statistics_router
# from .domains.data_sources.router import router as data_sources_router
from .shared.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from .shared.swagger_config import tags_metadata, swagger_ui_parameters

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작시 실행
    logger.info("애플리케이션 시작 중...")
    
    try:
        # MongoDB 연결
        connect_to_mongo()
        logger.info("MongoDB 연결 성공")
        
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
    
    yield
    
    # 종료시 실행
    logger.info("애플리케이션 종료 중...")
    try:
        close_mongo_connection()
    except Exception as e:
        logger.error(f"MongoDB 연결 종료 중 오류: {e}")
    logger.info("애플리케이션 종료 완료")


app = FastAPI(
    title="한국 공공데이터 API 서비스",
    description="""
    ## 🌟 개요
    창업진흥원 K-Startup 관련 공공데이터를 수집하고 가공하여 제공하는 RESTful API 서비스입니다.
    
    ## 🚀 주요 기능
    - 🏢 **사업공고 정보**: 창업지원 사업 공고 데이터 수집 및 제공
    - 📚 **콘텐츠 정보**: 창업 관련 콘텐츠 및 자료 제공 (개발 예정)
    - 📊 **통계 정보**: 창업 현황 및 성과 통계 데이터 (개발 예정)
    - 🎯 **사업정보**: 창업지원 사업 상세 정보 (개발 예정)
    
    ## 📂 데이터 출처
    - **공공데이터포털**: [창업진흥원_K-Startup 조회서비스](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15121654)
    - **Base URL**: `apis.data.go.kr/B552735/kisedKstartupService01`
    
    ## 📖 사용 방법
    1. 각 도메인별 `/fetch` 엔드포인트로 최신 데이터 수집
    2. 일반 CRUD 엔드포인트로 저장된 데이터 조회/관리
    3. 자동 스케줄러를 통한 정기적 데이터 갱신
    
    ## 🔒 인증
    현재 버전에서는 별도 인증이 필요하지 않습니다. (개발 단계)
    
    ## 📋 기술 스택
    - **Backend**: FastAPI + Python 3.11
    - **Database**: MongoDB
    - **Task Queue**: Celery + Redis
    - **Container**: Docker + Docker Compose
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
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 예외 핸들러 등록
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# MongoDB 연결은 lifespan에서 처리


# 라우터 등록
app.include_router(announcements_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(contents_router, prefix="/api/v1")
app.include_router(statistics_router, prefix="/api/v1")
# app.include_router(data_sources_router, prefix="/api/v1")


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
            "statistics (개발 예정)", 
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