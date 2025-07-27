"""Swagger UI 커스터마이징 설정"""

# Swagger UI CSS 커스터마이징
swagger_ui_parameters = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "none",  # 기본적으로 모든 엔드포인트 접기 (성능 최적화)
    "operationsSorter": "method",
    "filter": True,
    "showExtensions": False,  # 확장 정보 숨김 (성능 최적화)
    "showCommonExtensions": False,  # 공통 확장 정보 숨김 (성능 최적화)
    "defaultModelsExpandDepth": 0,  # 모델 기본 접힘 (성능 최적화)
    "defaultModelExpandDepth": 0,  # 모델 상세 기본 접힘 (성능 최적화)
    "displayOperationId": False,
    "tryItOutEnabled": True,
    "syntaxHighlight": False,  # 성능 최적화를 위해 syntax highlighting 비활성화
    "persistAuthorization": True,  # 인증 정보 유지
    "maxDisplayedTags": 10,  # 표시할 최대 태그 수 제한
    "preauthorizeBasic": False,
    "preauthorizeApiKey": False,
    "withCredentials": False
}

# OpenAPI 태그 설명 (간소화 - 성능 최적화)
tags_metadata = [
    {
        "name": "기본",
        "description": "기본 서비스 정보 및 상태 확인 API"
    },
    {
        "name": "사업공고", 
        "description": "창업진흥원 K-Startup 사업공고 관련 API - 데이터 수집, 조회, 관리"
    },
    {
        "name": "콘텐츠",
        "description": "창업 관련 콘텐츠 및 자료 API"
    },
    {
        "name": "통계",
        "description": "창업 현황 및 성과 통계 데이터 API"
    },
    {
        "name": "사업정보",
        "description": "창업지원 사업 상세 정보 API"
    },
    {
        "name": "분류 코드",
        "description": "시스템에서 사용하는 분류 코드 관리 API"
    },
    {
        "name": "작업 관리",
        "description": "데이터 수집 작업 관리 및 모니터링 API"
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