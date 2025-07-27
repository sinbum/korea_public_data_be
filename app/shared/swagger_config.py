"""Swagger UI 커스터마이징 설정"""

# Swagger UI CSS 커스터마이징
swagger_ui_parameters = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "list",
    "operationsSorter": "method",
    "filter": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "defaultModelsExpandDepth": 2,
    "defaultModelExpandDepth": 2,
    "displayOperationId": False,
    "tryItOutEnabled": True
}

# OpenAPI 태그 설명
tags_metadata = [
    {
        "name": "기본",
        "description": """
        기본 서비스 정보 및 상태 확인 API
        
        **포함된 엔드포인트:**
        - 서비스 정보 조회
        - 헬스 체크
        - API 버전 정보
        """
    },
    {
        "name": "사업공고",
        "description": """
        창업진흥원 K-Startup 사업공고 관련 API
        
        **주요 기능:**
        - 🔄 공공데이터에서 실시간 데이터 수집
        - 📋 저장된 공고 목록 조회 및 관리
        - 🔍 고급 검색 및 필터링 기능
        - ✏️ 완전한 CRUD 작업 지원
        - 📊 통계 및 요약 정보 제공
        
        **데이터 흐름:**
        1. `/fetch` 엔드포인트로 공공데이터 수집
        2. 수집된 데이터를 MongoDB에 저장 (중복 제거)
        3. RESTful API를 통해 데이터 조회/관리
        4. 고급 검색 및 페이지네이션 지원
        
        **데이터 출처:** K-Startup 공공데이터포털 (apis.data.go.kr)
        """
    },
    {
        "name": "콘텐츠",
        "description": """
        창업 관련 콘텐츠 및 자료 API
        
        **제공 콘텐츠:**
        - 📚 정책 및 규제정보 (공지사항)
        - 🏆 창업우수사례
        - 📈 생태계 이슈 및 동향
        
        **개발 상태:** 모델 완성, API 개발 중
        """,
        "externalDocs": {
            "description": "콘텐츠 분류 코드 상세 정보",
            "url": "https://github.com/your-repo/docs/content-category-codes.md"
        }
    },
    {
        "name": "통계",
        "description": """
        창업 현황 및 성과 통계 데이터 API
        
        **제공 통계:**
        - 📊 창업 지원 현황 통계
        - 📈 성과 분석 데이터
        - 🎯 트렌드 및 동향 분석
        
        **개발 상태:** 모델 완성, API 개발 중
        """
    },
    {
        "name": "사업정보",
        "description": """
        창업지원 사업 상세 정보 API
        
        **제공 정보:**
        - 🏢 사업 기본 정보
        - 💰 지원 내용 및 예산
        - 🎯 대상 및 조건
        - 📅 일정 및 절차
        
        **개발 상태:** 모델 완성, API 개발 중
        """
    },
    {
        "name": "분류 코드",
        "description": """
        시스템에서 사용하는 분류 코드 관리 API
        
        **제공 분류:**
        - 🏷️ 사업 카테고리 코드
        - 📁 콘텐츠 분류 코드
        - 🔍 코드 검색 및 추천
        - 📊 사용 통계
        
        **개발 상태:** 완성
        """
    },
    {
        "name": "작업 관리",
        "description": """
        데이터 수집 작업 관리 및 모니터링 API
        
        **관리 기능:**
        - ⏰ Celery 작업 스케줄링
        - 📋 작업 상태 모니터링
        - 🔄 수동 작업 실행
        - 📊 작업 성과 통계
        
        **개발 상태:** 완성
        """
    }
]

# OpenAPI 스키마 추가 정보
openapi_schema_extra = {
    "info": {
        "termsOfService": "https://example.com/terms/",
        "x-logo": {
            "url": "https://example.com/logo.png"
        }
    },
    "externalDocs": {
        "description": "상세 API 가이드",
        "url": "https://github.com/your-repo/docs/API_GUIDE.md"
    },
    "servers": [
        {
            "url": "http://localhost:8000",
            "description": "개발 서버"
        },
        {
            "url": "https://api.startup-data.kr",
            "description": "프로덕션 서버"
        }
    ]
}