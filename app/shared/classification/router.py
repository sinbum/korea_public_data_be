"""
Classification API router.

Provides RESTful endpoints for classification code management and validation.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends, Body
from fastapi.responses import JSONResponse
import logging

from .services import ClassificationService
from .models import (
    BusinessCategoryCode, ContentCategoryCode,
    ClassificationCodeSearchRequest, ClassificationCodeSearchResponse,
    ClassificationCodeValidationResult, ClassificationCodeStats
)
from .enums import BusinessCategory, ContentCategory, ClassificationCodeType
from ..responses import ErrorResponse, ValidationErrorResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/classification",
    tags=["분류 코드"],
    responses={404: {"description": "리소스를 찾을 수 없습니다"}}
)

# 공통 에러 응답 스키마 (Swagger용)
COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "잘못된 요청"},
    404: {"model": ErrorResponse, "description": "리소스를 찾을 수 없습니다"},
    422: {"model": ValidationErrorResponse, "description": "유효성 검사 실패"},
    500: {"model": ErrorResponse, "description": "서버 내부 오류"},
}

# Dependency injection
def get_classification_service() -> ClassificationService:
    """Get ClassificationService instance."""
    return ClassificationService()


@router.get(
    "/health",
    summary="분류 코드 서비스 헬스 체크",
    description="분류 코드 서비스의 상태를 확인합니다."
)
async def health_check(
    service: ClassificationService = Depends(get_classification_service)
) -> Dict[str, Any]:
    """Perform health check on classification service."""
    try:
        return await service.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


# Business Category Endpoints

@router.get(
    "/business-categories",
    response_model=List[BusinessCategoryCode],
    summary="사업 분야 코드 전체 조회",
    description="옵션 필터를 적용하여 모든 사업 분야 코드를 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_business_categories(
    active_only: bool = Query(True, description="Filter to active categories only"),
    include_details: bool = Query(True, description="Include detailed information"),
    service: ClassificationService = Depends(get_classification_service)
) -> List[BusinessCategoryCode]:
    """Get all business category codes."""
    try:
        return await service.get_business_categories(
            filter_active=active_only,
            include_details=include_details
        )
    except Exception as e:
        logger.error(f"Error retrieving business categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve business categories")


@router.get(
    "/business-categories/search",
    response_model=List[BusinessCategoryCode],
    summary="사업 분야 검색",
    description="쿼리 문자열로 사업 분야를 검색합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def search_business_categories(
    q: str = Query(..., description="검색어", example="교육"),
    fields: Optional[List[str]] = Query(None, description="검색할 필드 목록", example=["name", "description"]),
    limit: int = Query(10, ge=1, le=50, description="최대 결과 수", example=10),
    service: ClassificationService = Depends(get_classification_service)
) -> List[BusinessCategoryCode]:
    """Search business categories."""
    try:
        return await service.search_business_categories(
            query=q,
            search_fields=fields,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error searching business categories: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get(
    "/business-categories/{code}",
    response_model=BusinessCategoryCode,
    summary="사업 분야 단일 조회",
    description="코드 값으로 특정 사업 분야를 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_business_category(
    code: str = Path(..., description="사업 분야 코드 (예: cmrczn_tab1)", example="cmrczn_tab1"),
    service: ClassificationService = Depends(get_classification_service)
) -> BusinessCategoryCode:
    """Get a specific business category by code."""
    try:
        category = await service.get_business_category(code)
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Business category with code '{code}' not found"
            )
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving business category {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve business category")


@router.post(
    "/business-categories/validate",
    response_model=ClassificationCodeValidationResult,
    summary="사업 분야 코드 검증",
    description="사업 분야 코드를 검증하고, 유효하지 않은 경우 제안 코드를 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def validate_business_category(
    code: str = Query(..., description="검증할 사업 분야 코드", example="cmrczn_tab1"),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeValidationResult:
    """Validate a business category code."""
    try:
        return await service.validate_business_category(code)
    except Exception as e:
        logger.error(f"Error validating business category {code}: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")


# Content Category Endpoints

@router.get(
    "/content-categories",
    response_model=List[ContentCategoryCode],
    summary="콘텐츠 분류 코드 전체 조회",
    description="옵션 필터를 적용하여 모든 콘텐츠 분류 코드를 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_content_categories(
    active_only: bool = Query(True, description="Filter to active categories only"),
    include_details: bool = Query(True, description="Include detailed information"),
    service: ClassificationService = Depends(get_classification_service)
) -> List[ContentCategoryCode]:
    """Get all content category codes."""
    try:
        return await service.get_content_categories(
            filter_active=active_only,
            include_details=include_details
        )
    except Exception as e:
        logger.error(f"Error retrieving content categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve content categories")


@router.get(
    "/content-categories/search",
    response_model=List[ContentCategoryCode],
    summary="콘텐츠 분류 검색",
    description="쿼리 문자열로 콘텐츠 분류를 검색합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def search_content_categories(
    q: str = Query(..., description="검색어", example="정책"),
    fields: Optional[List[str]] = Query(None, description="검색할 필드 목록", example=["name", "description"]),
    limit: int = Query(10, ge=1, le=50, description="최대 결과 수", example=10),
    service: ClassificationService = Depends(get_classification_service)
) -> List[ContentCategoryCode]:
    """Search content categories."""
    try:
        return await service.search_content_categories(
            query=q,
            search_fields=fields,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error searching content categories: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get(
    "/content-categories/{code}",
    response_model=ContentCategoryCode,
    summary="콘텐츠 분류 단일 조회",
    description="코드 값으로 특정 콘텐츠 분류를 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_content_category(
    code: str = Path(..., description="콘텐츠 분류 코드 (예: notice_matr)", example="notice_matr"),
    service: ClassificationService = Depends(get_classification_service)
) -> ContentCategoryCode:
    """Get a specific content category by code."""
    try:
        category = await service.get_content_category(code)
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Content category with code '{code}' not found"
            )
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving content category {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve content category")


@router.post(
    "/content-categories/validate",
    response_model=ClassificationCodeValidationResult,
    summary="콘텐츠 분류 코드 검증",
    description="콘텐츠 분류 코드를 검증하고, 유효하지 않은 경우 제안 코드를 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def validate_content_category(
    code: str = Query(..., description="검증할 콘텐츠 분류 코드", example="notice_matr"),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeValidationResult:
    """Validate a content category code."""
    try:
        return await service.validate_content_category(code)
    except Exception as e:
        logger.error(f"Error validating content category {code}: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")


# Unified Endpoints

@router.post(
    "/validate",
    response_model=ClassificationCodeValidationResult,
    summary="분류 코드 자동 검증",
    description="분류 코드 유형을 자동으로 판별하여 검증합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def validate_any_code(
    code: str = Query(..., description="검증할 분류 코드", example="cmrczn_tab1"),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeValidationResult:
    """Validate any classification code with auto-detection."""
    try:
        return await service.validate_any_code(code)
    except Exception as e:
        logger.error(f"Error validating code {code}: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")


@router.post(
    "/validate-batch",
    response_model=Dict[str, ClassificationCodeValidationResult],
    summary="분류 코드 배치 검증",
    description="한 번의 요청으로 여러 분류 코드를 검증합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def validate_batch(
    codes: List[str] = Body(
        ...,
        description="검증할 코드 배열 (최대 100개)",
        example=["cmrczn_tab1", "notice_matr", "invalid_code"]
    ),
    service: ClassificationService = Depends(get_classification_service)
) -> Dict[str, ClassificationCodeValidationResult]:
    """Validate multiple classification codes."""
    try:
        if len(codes) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot validate more than 100 codes at once"
            )
        
        return await service.validate_batch(codes)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch validation: {e}")
        raise HTTPException(status_code=500, detail="Batch validation failed")


@router.get(
    "/detect-type/{code}",
    response_model=Dict[str, Optional[str]],
    summary="분류 코드 유형 판별",
    description="분류 코드의 유형을 판별합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def detect_code_type(
    code: str = Path(..., description="분석할 분류 코드", example="cmrczn_tab1"),
    service: ClassificationService = Depends(get_classification_service)
) -> Dict[str, Optional[str]]:
    """Detect the type of a classification code."""
    try:
        code_type = await service.detect_code_type(code)
        return {
            "code": code,
            "detected_type": code_type
        }
    except Exception as e:
        logger.error(f"Error detecting code type for {code}: {e}")
        raise HTTPException(status_code=500, detail="Type detection failed")


@router.post(
    "/search",
    response_model=ClassificationCodeSearchResponse,
    summary="통합 분류 코드 검색",
    description="모든 분류 코드 유형을 대상으로 통합 검색을 수행합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def search_all_categories(
    request: ClassificationCodeSearchRequest = Body(
        ...,
        description="통합 검색 요청",
        examples={
            "business_keyword": {
                "summary": "사업 분야 키워드 검색",
                "value": {
                    "query": "교육",
                    "code_type": "business",
                    "fields": ["name", "description"],
                    "limit": 10
                }
            },
            "content_keyword": {
                "summary": "콘텐츠 분류 키워드 검색",
                "value": {
                    "query": "정책",
                    "code_type": "content",
                    "fields": ["name"],
                    "limit": 5
                }
            }
        }
    ),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeSearchResponse:
    """Search across all classification categories."""
    try:
        return await service.search_all_categories(request)
    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get(
    "/codes",
    response_model=Dict[str, List[str]],
    summary="유효 코드 전체 조회",
    description="유형별로 정리된 모든 유효 분류 코드를 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_all_valid_codes(
    service: ClassificationService = Depends(get_classification_service)
) -> Dict[str, List[str]]:
    """Get all valid classification codes."""
    try:
        return await service.get_all_valid_codes()
    except Exception as e:
        logger.error(f"Error retrieving all valid codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve codes")


@router.get(
    "/recommendations",
    response_model=List[Dict[str, Any]],
    summary="코드 추천",
    description="컨텍스트에 기반하여 분류 코드 추천을 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_code_recommendations(
    context: str = Query(..., description="추천을 위한 컨텍스트 설명", example="해외 진출 관련 지원"),
    code_type: Optional[str] = Query(None, description="추천할 코드 유형", example="business"),
    limit: int = Query(5, ge=1, le=20, description="최대 추천 개수", example=5),
    service: ClassificationService = Depends(get_classification_service)
) -> List[Dict[str, Any]]:
    """Get code recommendations based on context."""
    try:
        # Validate code_type if provided
        if code_type and code_type not in ClassificationCodeType.get_all_types():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid code type: {code_type}"
            )
        
        return await service.get_code_recommendations(
            context=context,
            code_type=code_type,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting code recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


# Statistics and Analytics

@router.get(
    "/statistics",
    response_model=ClassificationCodeStats,
    summary="분류 코드 통계",
    description="분류 코드에 대한 종합 통계를 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_classification_statistics(
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeStats:
    """Get classification code statistics."""
    try:
        return await service.get_classification_statistics()
    except Exception as e:
        logger.error(f"Error retrieving classification statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


# Administrative Endpoints

@router.post(
    "/cache/clear",
    summary="분류 코드 캐시 초기화",
    description="분류 코드 서비스의 모든 캐시 데이터를 초기화합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def clear_cache(
    service: ClassificationService = Depends(get_classification_service)
) -> Dict[str, str]:
    """Clear classification service cache."""
    try:
        service.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


# Reference Data Endpoints

@router.get(
    "/reference/business-categories",
    response_model=List[Dict[str, Any]],
    summary="사업 분야 참조 데이터",
    description="모든 사업 분야에 대한 참조 정보를 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_business_category_reference() -> List[Dict[str, Any]]:
    """Get business category reference data."""
    try:
        return BusinessCategory.get_all_info()
    except Exception as e:
        logger.error(f"Error retrieving business category reference: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reference data")


@router.get(
    "/reference/content-categories",
    response_model=List[Dict[str, Any]],
    summary="콘텐츠 분류 참조 데이터",
    description="모든 콘텐츠 분류에 대한 참조 정보를 제공합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_content_category_reference() -> List[Dict[str, Any]]:
    """Get content category reference data."""
    try:
        return ContentCategory.get_all_info()
    except Exception as e:
        logger.error(f"Error retrieving content category reference: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reference data")


@router.get(
    "/reference/types",
    response_model=List[str],
    summary="분류 코드 유형 목록",
    description="지원되는 모든 분류 코드 유형을 조회합니다.",
    responses=COMMON_ERROR_RESPONSES
)
async def get_classification_types() -> List[str]:
    """Get all classification code types."""
    try:
        return ClassificationCodeType.get_all_types()
    except Exception as e:
        logger.error(f"Error retrieving classification types: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve types")