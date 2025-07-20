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
        "description": "기본 서비스 정보 및 상태 확인 API"
    },
    {
        "name": "사업공고",
        "description": """
        창업진흥원 K-Startup 사업공고 관련 API
        
        **주요 기능:**
        - 공공데이터에서 실시간 데이터 수집
        - 저장된 공고 목록 조회 및 관리
        - 검색 및 필터링 기능
        - CRUD 작업 지원
        
        **데이터 흐름:**
        1. `/fetch` 엔드포인트로 공공데이터 수집
        2. 수집된 데이터를 MongoDB에 저장
        3. 일반 API를 통해 데이터 조회/관리
        """
    },
    {
        "name": "콘텐츠",
        "description": "창업 관련 콘텐츠 및 자료 API (개발 예정)",
        "externalDocs": {
            "description": "개발 로드맵 확인",
            "url": "https://github.com/your-repo/roadmap"
        }
    },
    {
        "name": "통계",
        "description": "창업 현황 및 성과 통계 데이터 API (개발 예정)"
    },
    {
        "name": "사업정보",
        "description": "창업지원 사업 상세 정보 API (개발 예정)"
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