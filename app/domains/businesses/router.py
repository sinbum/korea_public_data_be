"""
Business Router implementation.

Provides REST API endpoints for business-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import BusinessService
from .models import BusinessResponse, BusinessCreate, BusinessUpdate
from ...shared.schemas import PaginatedResponse

router = APIRouter(
    prefix="/businesses",
    tags=["사업정보"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)


def get_business_service() -> BusinessService:
    return BusinessService()


@router.post(
    "/fetch",
    response_model=List[BusinessResponse],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 사업정보 수집",
    description="K-Startup API에서 사업정보 데이터를 가져와 데이터베이스에 저장합니다."
)
def fetch_businesses(
    page_no: int = Query(1, ge=1, description="조회할 페이지 번호"),
    num_of_rows: int = Query(10, ge=1, le=100, description="한 페이지당 결과 수"),
    business_field: Optional[str] = Query(None, description="사업분야 필터"),
    organization: Optional[str] = Query(None, description="주관기관 필터"),
    service: BusinessService = Depends(get_business_service)
):
    """K-Startup API에서 사업정보를 가져와 저장"""
    try:
        businesses = service.fetch_and_save_businesses(
            page_no=page_no,
            num_of_rows=num_of_rows,
            business_field=business_field,
            organization=organization
        )
        return [BusinessResponse(
            id=str(b.id),
            business_data=b.business_data,
            source_url=b.source_url,
            is_active=b.is_active,
            created_at=b.created_at,
            updated_at=b.updated_at
        ) for b in businesses]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=PaginatedResponse[BusinessResponse],
    status_code=status.HTTP_200_OK,
    summary="사업정보 목록 조회"
)
def get_businesses(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    is_active: bool = Query(True, description="활성 상태 필터"),
    service: BusinessService = Depends(get_business_service)
):
    """저장된 사업정보 목록을 조회합니다."""
    result = service.get_businesses(page=page, page_size=page_size, is_active=is_active)
    
    items = [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in result.items]
    
    return PaginatedResponse(
        items=items,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        has_next=result.has_next,
        has_previous=result.has_previous
    )


@router.get(
    "/{business_id}",
    response_model=BusinessResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 사업정보 상세 조회"
)
def get_business(
    business_id: str = Path(..., description="조회할 사업정보의 고유 ID"),
    service: BusinessService = Depends(get_business_service)
):
    """특정 사업정보의 상세 정보를 조회합니다."""
    business = service.get_business_by_id(business_id)
    if not business:
        raise HTTPException(
            status_code=404,
            detail="해당 ID의 사업정보를 찾을 수 없습니다"
        )
    
    return BusinessResponse(
        id=str(business.id),
        business_data=business.business_data,
        source_url=business.source_url,
        is_active=business.is_active,
        created_at=business.created_at,
        updated_at=business.updated_at
    )


@router.post("/", response_model=BusinessResponse)
def create_business(
    business_data: BusinessCreate,
    service: BusinessService = Depends(get_business_service)
):
    """새 사업정보 생성"""
    business = service.create_business(business_data)
    return BusinessResponse(
        id=str(business.id),
        business_data=business.business_data,
        source_url=business.source_url,
        is_active=business.is_active,
        created_at=business.created_at,
        updated_at=business.updated_at
    )


@router.put("/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: str,
    update_data: BusinessUpdate,
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 수정"""
    business = service.update_business(business_id, update_data)
    if not business:
        raise HTTPException(status_code=404, detail="사업정보를 찾을 수 없습니다")
    
    return BusinessResponse(
        id=str(business.id),
        business_data=business.business_data,
        source_url=business.source_url,
        is_active=business.is_active,
        created_at=business.created_at,
        updated_at=business.updated_at
    )


@router.delete("/{business_id}")
def delete_business(
    business_id: str,
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 삭제 (비활성화)"""
    success = service.delete_business(business_id)
    if not success:
        raise HTTPException(status_code=404, detail="사업정보를 찾을 수 없습니다")
    
    return {"message": "사업정보가 삭제되었습니다"}


@router.get("/search/{search_term}", response_model=List[BusinessResponse])
def search_businesses(
    search_term: str = Path(..., description="검색어"),
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 검색"""
    businesses = service.search_businesses(search_term)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/type/{business_type}", response_model=List[BusinessResponse])
def get_businesses_by_type(
    business_type: str = Path(..., description="사업 유형"),
    service: BusinessService = Depends(get_business_service)
):
    """사업 유형별 사업정보 조회"""
    businesses = service.get_businesses_by_type(business_type)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/organization/{organization}", response_model=List[BusinessResponse])
def get_businesses_by_organization(
    organization: str = Path(..., description="주관기관"),
    service: BusinessService = Depends(get_business_service)
):
    """주관기관별 사업정보 조회"""
    businesses = service.get_businesses_by_organization(organization)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/field/{business_field}", response_model=List[BusinessResponse])
def get_businesses_by_field(
    business_field: str = Path(..., description="사업분야"),
    service: BusinessService = Depends(get_business_service)
):
    """사업분야별 사업정보 조회"""
    businesses = service.get_businesses_by_field(business_field)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/startup-stage/{startup_stage}", response_model=List[BusinessResponse])
def get_businesses_by_startup_stage(
    startup_stage: str = Path(..., description="창업단계"),
    service: BusinessService = Depends(get_business_service)
):
    """창업단계별 사업정보 조회"""
    businesses = service.get_businesses_by_startup_stage(startup_stage)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/recent", response_model=List[BusinessResponse])
def get_recent_businesses(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 사업정보 수"),
    service: BusinessService = Depends(get_business_service)
):
    """최근 사업정보 조회"""
    businesses = service.get_recent_businesses(limit)
    return [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in businesses]


@router.get("/filter", response_model=PaginatedResponse[BusinessResponse])
def get_businesses_with_filter(
    business_type: Optional[str] = Query(None, description="사업 유형"),
    organization: Optional[str] = Query(None, description="주관기관"),
    business_field: Optional[str] = Query(None, description="사업분야"),
    startup_stage: Optional[str] = Query(None, description="창업단계"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    service: BusinessService = Depends(get_business_service)
):
    """필터 조건에 따른 사업정보 조회"""
    result = service.get_businesses_with_filter(
        business_type=business_type,
        organization=organization,
        business_field=business_field,
        startup_stage=startup_stage,
        page=page,
        page_size=page_size
    )
    
    items = [BusinessResponse(
        id=str(b.id),
        business_data=b.business_data,
        source_url=b.source_url,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at
    ) for b in result.items]
    
    return PaginatedResponse(
        items=items,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        has_next=result.has_next,
        has_previous=result.has_previous
    )


@router.get("/statistics", response_model=dict)
def get_business_statistics(
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 통계 조회"""
    return service.get_business_statistics()