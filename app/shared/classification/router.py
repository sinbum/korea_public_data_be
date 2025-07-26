"""
Classification API router.

Provides RESTful endpoints for classification code management and validation.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from fastapi.responses import JSONResponse
import logging

from .services import ClassificationService
from .models import (
    BusinessCategoryCode, ContentCategoryCode,
    ClassificationCodeSearchRequest, ClassificationCodeSearchResponse,
    ClassificationCodeValidationResult, ClassificationCodeStats
)
from .enums import BusinessCategory, ContentCategory, ClassificationCodeType

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/classification",
    tags=["Classification Codes"],
    responses={404: {"description": "Not found"}}
)

# Dependency injection
def get_classification_service() -> ClassificationService:
    """Get ClassificationService instance."""
    return ClassificationService()


@router.get(
    "/health",
    summary="Health check for classification service",
    description="Check the health status of the classification service"
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
    summary="Get all business category codes",
    description="Retrieve all business category codes with optional filtering"
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
    "/business-categories/{code}",
    response_model=BusinessCategoryCode,
    summary="Get business category by code",
    description="Retrieve a specific business category by its code"
)
async def get_business_category(
    code: str = Path(..., description="Business category code (e.g., cmrczn_tab1)"),
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
    summary="Validate business category code",
    description="Validate a business category code and get suggestions if invalid"
)
async def validate_business_category(
    code: str = Query(..., description="Business category code to validate"),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeValidationResult:
    """Validate a business category code."""
    try:
        return await service.validate_business_category(code)
    except Exception as e:
        logger.error(f"Error validating business category {code}: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")


@router.get(
    "/business-categories/search",
    response_model=List[BusinessCategoryCode],
    summary="Search business categories",
    description="Search business categories by query string"
)
async def search_business_categories(
    q: str = Query(..., description="Search query"),
    fields: Optional[List[str]] = Query(None, description="Fields to search in"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
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


# Content Category Endpoints

@router.get(
    "/content-categories",
    response_model=List[ContentCategoryCode],
    summary="Get all content category codes",
    description="Retrieve all content category codes with optional filtering"
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
    "/content-categories/{code}",
    response_model=ContentCategoryCode,
    summary="Get content category by code",
    description="Retrieve a specific content category by its code"
)
async def get_content_category(
    code: str = Path(..., description="Content category code (e.g., notice_matr)"),
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
    summary="Validate content category code",
    description="Validate a content category code and get suggestions if invalid"
)
async def validate_content_category(
    code: str = Query(..., description="Content category code to validate"),
    service: ClassificationService = Depends(get_classification_service)
) -> ClassificationCodeValidationResult:
    """Validate a content category code."""
    try:
        return await service.validate_content_category(code)
    except Exception as e:
        logger.error(f"Error validating content category {code}: {e}")
        raise HTTPException(status_code=500, detail="Validation failed")


@router.get(
    "/content-categories/search",
    response_model=List[ContentCategoryCode],
    summary="Search content categories",
    description="Search content categories by query string"
)
async def search_content_categories(
    q: str = Query(..., description="Search query"),
    fields: Optional[List[str]] = Query(None, description="Fields to search in"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
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


# Unified Endpoints

@router.post(
    "/validate",
    response_model=ClassificationCodeValidationResult,
    summary="Validate any classification code",
    description="Validate any classification code (auto-detects type)"
)
async def validate_any_code(
    code: str = Query(..., description="Classification code to validate"),
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
    summary="Validate multiple classification codes",
    description="Validate multiple classification codes in one request"
)
async def validate_batch(
    codes: List[str],
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
    summary="Detect classification code type",
    description="Detect the type of a classification code"
)
async def detect_code_type(
    code: str = Path(..., description="Classification code to analyze"),
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
    summary="Search all classification codes",
    description="Search across all classification code types"
)
async def search_all_categories(
    request: ClassificationCodeSearchRequest,
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
    summary="Get all valid codes",
    description="Get all valid classification codes organized by type"
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
    summary="Get code recommendations",
    description="Get classification code recommendations based on context"
)
async def get_code_recommendations(
    context: str = Query(..., description="Context description for recommendations"),
    code_type: Optional[str] = Query(None, description="Type of codes to recommend"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
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
    summary="Get classification code statistics",
    description="Get comprehensive statistics about classification codes"
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
    summary="Clear classification service cache",
    description="Clear all cached data in the classification service"
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
    summary="Get business category reference data",
    description="Get comprehensive reference information for all business categories"
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
    summary="Get content category reference data",
    description="Get comprehensive reference information for all content categories"
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
    summary="Get classification code types",
    description="Get all supported classification code types"
)
async def get_classification_types() -> List[str]:
    """Get all classification code types."""
    try:
        return ClassificationCodeType.get_all_types()
    except Exception as e:
        logger.error(f"Error retrieving classification types: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve types")