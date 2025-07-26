"""
Versioned business routers demonstrating API versioning system.

Shows how different API versions can be implemented for businesses domain
with backward compatibility and automatic response adaptation.
"""

from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, Query
from pydantic import Field

from ...shared.version_router import (
    VersionedAPIRouter,
    version_specific,
    deprecated,
    experimental,
    version_compatibility_check
)
from ...shared.versioning import APIVersion, get_api_version
from ...shared.responses import BaseResponse, PaginatedResponse, CreatedResponse, success_response
from ...shared.pagination import PaginationParams, PaginatedResult
from .service import BusinessService
from .schemas import BusinessResponse, BusinessCreate, BusinessUpdate
from .models import Business

# V1 Router - Legacy format support
v1_router = VersionedAPIRouter(
    prefix="/businesses",
    tags=["기업 관리 (V1)"],
    default_version="v1",
    supported_versions=["v1"]
)

# V2 Router - Current format
v2_router = VersionedAPIRouter(
    prefix="/businesses", 
    tags=["기업 관리 (V2)"],
    default_version="v2",
    supported_versions=["v2"]
)


def get_business_service() -> BusinessService:
    """의존성 주입을 위한 BusinessService 팩토리"""
    return BusinessService()


# V1 Endpoints (Deprecated format)
@v1_router.get(
    "/",
    summary="기업 목록 조회 (V1)",
    description="V1 형식으로 기업 목록을 조회합니다. (Deprecated)",
    deprecated_in="v2.0",
    removed_in="v3.0"
)
@deprecated(since_version="v2.0", removed_in="v3.0")
async def get_businesses_v1(
    request: Request,
    page: int = Query(1, ge=1, description="페이지 번호"),
    per_page: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    sort_by: str = Query("created_date", description="정렬 기준"),
    order: str = Query("desc", description="정렬 순서"),
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(get_api_version)
):
    """V1 형식 기업 목록 조회 (Deprecated)"""
    
    # V1 uses different parameter names
    pagination = PaginationParams(
        page=page,
        size=per_page,
        sort=sort_by,
        order="desc" if order.lower() == "desc" else "asc"
    )
    
    try:
        result = await business_service.get_businesses_paginated(pagination)
        
        # V1 response format
        return {
            "status": "success",
            "result": result.items,
            "pagination": {
                "current_page": result.page,
                "per_page": result.size,
                "total_count": result.total,
                "total_pages": result.total_pages
            },
            "msg": "기업 목록 조회 성공",
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "msg": f"기업 목록 조회 실패: {str(e)}",
            "error_code": "FETCH_ERROR"
        }


@v1_router.get(
    "/{business_id}",
    summary="기업 상세 조회 (V1)",
    description="V1 형식으로 특정 기업의 상세 정보를 조회합니다. (Deprecated)",
    deprecated_in="v2.0"
)
@deprecated(since_version="v2.0")
async def get_business_v1(
    business_id: str,
    business_service: BusinessService = Depends(get_business_service)
):
    """V1 형식 기업 상세 조회 (Deprecated)"""
    
    try:
        business = await business_service.get_business(business_id)
        if not business:
            return {
                "status": "error",
                "result": None,
                "msg": "기업을 찾을 수 없습니다",
                "error_code": "NOT_FOUND"
            }
        
        return {
            "status": "success",
            "result": business,
            "msg": "기업 조회 성공"
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "result": None,
            "msg": f"기업 조회 실패: {str(e)}",
            "error_code": "FETCH_ERROR"
        }


# V2 Endpoints (Current format)
@v2_router.get(
    "/",
    response_model=PaginatedResponse[BusinessResponse],
    summary="기업 목록 조회 (V2)",
    description="V2 형식으로 기업 목록을 조회합니다.",
    min_version="v2.0"
)
async def get_businesses_v2(
    pagination: PaginationParams = Depends(),
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(get_api_version)
):
    """V2 형식 기업 목록 조회"""
    
    try:
        result = await business_service.get_businesses_paginated(pagination)
        
        return success_response(
            data=result.items,
            message="기업 목록 조회 성공",
            pagination=result.to_pagination_meta()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 목록 조회 실패: {str(e)}"
        )


@v2_router.get(
    "/{business_id}",
    response_model=BaseResponse[BusinessResponse],
    summary="기업 상세 조회 (V2)",
    description="V2 형식으로 특정 기업의 상세 정보를 조회합니다."
)
async def get_business_v2(
    business_id: str,
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(version_compatibility_check("v2.0"))
):
    """V2 형식 기업 상세 조회"""
    
    try:
        business = await business_service.get_business(business_id)
        if not business:
            raise HTTPException(
                status_code=404,
                detail="기업을 찾을 수 없습니다"
            )
        
        return success_response(
            data=business,
            message="기업 조회 성공"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 조회 실패: {str(e)}"
        )


@v2_router.post(
    "/",
    response_model=CreatedResponse[BusinessResponse],
    summary="기업 생성 (V2)",
    description="새로운 기업을 생성합니다.",
    status_code=201
)
async def create_business_v2(
    business_data: BusinessCreate,
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(version_compatibility_check("v2.0"))
):
    """V2 형식 기업 생성"""
    
    try:
        created_business = await business_service.create_business(business_data)
        
        return CreatedResponse(
            success=True,
            data=created_business,
            message="기업이 성공적으로 생성되었습니다",
            resource_id=created_business.id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 생성 실패: {str(e)}"
        )


@v2_router.put(
    "/{business_id}",
    response_model=BaseResponse[BusinessResponse],
    summary="기업 수정 (V2)",
    description="기존 기업을 수정합니다."
)
async def update_business_v2(
    business_id: str,
    business_data: BusinessUpdate,
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(version_compatibility_check("v2.0"))
):
    """V2 형식 기업 수정"""
    
    try:
        updated_business = await business_service.update_business(
            business_id, business_data
        )
        if not updated_business:
            raise HTTPException(
                status_code=404,
                detail="수정할 기업을 찾을 수 없습니다"
            )
        
        return success_response(
            data=updated_business,
            message="기업이 성공적으로 수정되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 수정 실패: {str(e)}"
        )


@v2_router.delete(
    "/{business_id}",
    summary="기업 삭제 (V2)",
    description="기업을 삭제합니다.",
    status_code=204
)
async def delete_business_v2(
    business_id: str,
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(version_compatibility_check("v2.0"))
):
    """V2 형식 기업 삭제"""
    
    try:
        deleted = await business_service.delete_business(business_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="삭제할 기업을 찾을 수 없습니다"
            )
        
        # 204 No Content - no response body
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 삭제 실패: {str(e)}"
        )


# Fetch from external API endpoint (V2)
@v2_router.post(
    "/fetch",
    summary="외부 API에서 기업 데이터 수집 (V2)",
    description="한국공공데이터 API에서 기업 정보를 수집하여 데이터베이스에 저장합니다."
)
async def fetch_businesses_v2(
    business_service: BusinessService = Depends(get_business_service),
    current_version: APIVersion = Depends(version_compatibility_check("v2.0"))
):
    """V2 형식 외부 API 기업 데이터 수집"""
    
    try:
        result = await business_service.fetch_and_store_businesses()
        
        return success_response(
            data=result,
            message="기업 데이터 수집이 성공적으로 완료되었습니다"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"기업 데이터 수집 실패: {str(e)}"
        )


# Experimental V3 Endpoints (Future features)
v3_router = VersionedAPIRouter(
    prefix="/businesses",
    tags=["기업 관리 (V3 - Experimental)"],
    default_version="v3",
    supported_versions=["v3"]
)


@v3_router.get(
    "/search",
    summary="고급 기업 검색 (V3 - Experimental)",
    description="향후 V3에서 제공될 고급 검색 기능입니다.",
    min_version="v3.0"
)
@experimental(version="v3.0")
async def search_businesses_v3(
    q: str = Query(..., description="검색 키워드"),
    category: Optional[str] = Query(None, description="기업 카테고리"),
    region: Optional[str] = Query(None, description="지역"),
    business_service: BusinessService = Depends(get_business_service)
):
    """V3 실험적 고급 검색 기능"""
    
    # This is a placeholder for future advanced search functionality
    return {
        "success": True,
        "data": [],
        "message": "실험적 검색 기능 - 아직 구현되지 않음",
        "experimental_notice": "이 엔드포인트는 실험적 기능으로 변경될 수 있습니다"
    }


@v3_router.get(
    "/analytics",
    summary="기업 분석 데이터 (V3 - Experimental)",
    description="기업 관련 분석 데이터를 제공합니다.",
    min_version="v3.0"
)
@experimental(version="v3.0")
async def get_business_analytics_v3():
    """V3 실험적 분석 기능"""
    
    return {
        "success": True,
        "data": {
            "total_businesses": 0,
            "active_businesses": 0,
            "categories": [],
            "regions": [],
            "trends": []
        },
        "message": "기업 분석 데이터 조회 성공",
        "experimental_notice": "이 엔드포인트는 실험적 기능입니다"
    }


# Create main versioned router that includes all versions
def create_versioned_business_router() -> VersionedAPIRouter:
    """Create main versioned business router."""
    
    main_router = VersionedAPIRouter(
        prefix="/businesses",
        tags=["기업 관리"],
        default_version="v2",
        supported_versions=["v1", "v2", "v3"]
    )
    
    # Include version-specific routers
    main_router.include_router(v1_router, prefix="/v1")
    main_router.include_router(v2_router, prefix="/v2") 
    main_router.include_router(v3_router, prefix="/v3")
    
    return main_router


# Export routers
__all__ = [
    "v1_router",
    "v2_router", 
    "v3_router",
    "create_versioned_business_router"
]