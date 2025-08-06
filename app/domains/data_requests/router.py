from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from ...core.database import get_database
from ...shared.responses import BaseResponse
from ...shared.pagination import PaginationParams
from .service import DataRequestService, CategoryService
from .repository import DataRequestRepository, CategoryRepository, VoteRepository
from .schemas import (
    DataRequestCreateRequest, DataRequestUpdateRequest, DataRequestStatusUpdateRequest,
    VoteRequest, CategoryCreateRequest, DataRequestFilters,
    DataRequestResponse, DataRequestListResponse, VoteResponse, CategoryResponse,
    DataRequestStatsResponse
)
from .models import DataRequestStatus, DataRequestPriority


router = APIRouter(
    prefix="/data-requests",
    tags=["데이터 요청"],
    responses={404: {"description": "Not found"}}
)

# 카테고리 라우터
categories_router = APIRouter(
    prefix="/categories",
    tags=["카테고리"],
    responses={404: {"description": "Not found"}}
)


# 의존성 주입 함수들
def get_data_request_service(db=Depends(get_database)) -> DataRequestService:
    """데이터 요청 서비스 의존성"""
    data_request_repo = DataRequestRepository(db)
    category_repo = CategoryRepository(db)
    vote_repo = VoteRepository(db)
    return DataRequestService(data_request_repo, category_repo, vote_repo)


def get_category_service(db=Depends(get_database)) -> CategoryService:
    """카테고리 서비스 의존성"""
    category_repo = CategoryRepository(db)
    return CategoryService(category_repo)


# 임시 사용자 ID 함수 (인증 시스템 구현 전까지)
def get_current_user_id() -> str:
    """현재 사용자 ID 조회 (임시)"""
    return "temp_user_123"


def get_current_user_info():
    """현재 사용자 정보 조회 (임시)"""
    return {
        "user_id": "temp_user_123",
        "user_name": "테스트 사용자",
        "user_email": "test@example.com"
    }


# === 데이터 요청 라우터 ===

@router.post(
    "/",
    response_model=BaseResponse[DataRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="데이터 요청 생성",
    description="새로운 데이터 요청을 생성합니다."
)
async def create_data_request(
    request_data: DataRequestCreateRequest,
    service: DataRequestService = Depends(get_data_request_service),
    user_info=Depends(get_current_user_info)
):
    """데이터 요청 생성"""
    try:
        result = await service.create_data_request(
            request_data,
            user_info["user_id"],
            user_info["user_name"],
            user_info["user_email"]
        )
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청이 성공적으로 생성되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/",
    response_model=BaseResponse[DataRequestListResponse],
    summary="데이터 요청 목록 조회",
    description="필터와 페이지네이션을 적용한 데이터 요청 목록을 조회합니다."
)
async def get_data_requests(
    category: Optional[str] = Query(None, description="카테고리 ID"),
    status: Optional[DataRequestStatus] = Query(None, description="상태"),
    priority: Optional[DataRequestPriority] = Query(None, description="우선순위"),
    search: Optional[str] = Query(None, description="검색어"),
    sort: str = Query("likes", description="정렬 기준", regex="^(likes|newest|oldest|priority)$"),
    page: int = Query(1, description="페이지", ge=1),
    limit: int = Query(20, description="페이지당 개수", ge=1, le=100),
    service: DataRequestService = Depends(get_data_request_service),
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """데이터 요청 목록 조회"""
    try:
        filters = DataRequestFilters(
            category=category,
            status=status,
            priority=priority,
            search=search,
            sort=sort,
            page=page,
            limit=limit
        )
        
        result = await service.get_data_requests(filters, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청 목록을 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/popular",
    response_model=BaseResponse[List[DataRequestResponse]],
    summary="인기 데이터 요청 조회",
    description="투표 수가 많은 인기 데이터 요청을 조회합니다."
)
async def get_popular_requests(
    limit: int = Query(10, description="조회할 개수", ge=1, le=50),
    service: DataRequestService = Depends(get_data_request_service)
):
    """인기 데이터 요청 조회"""
    try:
        result = await service.get_popular_requests(limit)
        return BaseResponse(
            success=True,
            data=result,
            message="인기 데이터 요청을 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/stats",
    response_model=BaseResponse[DataRequestStatsResponse],
    summary="데이터 요청 통계 조회",
    description="데이터 요청 관련 통계 정보를 조회합니다."
)
async def get_request_stats(
    service: DataRequestService = Depends(get_data_request_service)
):
    """데이터 요청 통계 조회"""
    try:
        result = await service.get_stats()
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청 통계를 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{request_id}",
    response_model=BaseResponse[DataRequestResponse],
    summary="데이터 요청 상세 조회",
    description="특정 데이터 요청의 상세 정보를 조회합니다."
)
async def get_data_request(
    request_id: str,
    service: DataRequestService = Depends(get_data_request_service),
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """데이터 요청 상세 조회"""
    try:
        result = await service.get_data_request(request_id, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청을 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{request_id}",
    response_model=BaseResponse[DataRequestResponse],
    summary="데이터 요청 수정",
    description="데이터 요청을 수정합니다. (요청자만 가능)"
)
async def update_data_request(
    request_id: str,
    update_data: DataRequestUpdateRequest,
    service: DataRequestService = Depends(get_data_request_service),
    user_id: str = Depends(get_current_user_id)
):
    """데이터 요청 수정"""
    try:
        result = await service.update_data_request(request_id, update_data, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청이 성공적으로 수정되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{request_id}",
    response_model=BaseResponse[bool],
    summary="데이터 요청 삭제",
    description="데이터 요청을 삭제합니다. (요청자만 가능)"
)
async def delete_data_request(
    request_id: str,
    service: DataRequestService = Depends(get_data_request_service),
    user_id: str = Depends(get_current_user_id)
):
    """데이터 요청 삭제"""
    try:
        result = await service.delete_data_request(request_id, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청이 성공적으로 삭제되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{request_id}/vote",
    response_model=BaseResponse[VoteResponse],
    summary="데이터 요청에 투표",
    description="데이터 요청에 투표합니다."
)
async def vote_data_request(
    request_id: str,
    vote_data: VoteRequest,
    service: DataRequestService = Depends(get_data_request_service),
    user_id: str = Depends(get_current_user_id)
):
    """데이터 요청에 투표"""
    try:
        # vote_data에서 request_id를 URL 파라미터로 대체
        vote_data.request_id = request_id
        
        result = await service.vote_data_request(request_id, vote_data, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="투표가 성공적으로 처리되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{request_id}/vote",
    response_model=BaseResponse[VoteResponse],
    summary="투표 취소",
    description="데이터 요청에 대한 투표를 취소합니다."
)
async def cancel_vote(
    request_id: str,
    service: DataRequestService = Depends(get_data_request_service),
    user_id: str = Depends(get_current_user_id)
):
    """투표 취소"""
    try:
        # 기존 투표를 찾아서 취소 처리
        vote_data = VoteRequest(request_id=request_id, vote_type="like")  # 임시값
        result = await service.vote_data_request(request_id, vote_data, user_id)
        return BaseResponse(
            success=True,
            data=result,
            message="투표가 성공적으로 취소되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/user/{user_id}",
    response_model=BaseResponse[DataRequestListResponse],
    summary="사용자 데이터 요청 조회",
    description="특정 사용자의 데이터 요청 목록을 조회합니다."
)
async def get_user_requests(
    user_id: str,
    page: int = Query(1, description="페이지", ge=1),
    limit: int = Query(20, description="페이지당 개수", ge=1, le=100),
    service: DataRequestService = Depends(get_data_request_service)
):
    """사용자 데이터 요청 조회"""
    try:
        result = await service.get_user_requests(user_id, page, limit)
        return BaseResponse(
            success=True,
            data=result,
            message="사용자 데이터 요청을 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/{request_id}/status",
    response_model=BaseResponse[DataRequestResponse],
    summary="데이터 요청 상태 변경 (관리자용)",
    description="데이터 요청의 상태를 변경합니다. 관리자만 사용 가능합니다."
)
async def update_request_status(
    request_id: str,
    status_data: DataRequestStatusUpdateRequest,
    service: DataRequestService = Depends(get_data_request_service)
    # TODO: 관리자 권한 확인 의존성 추가
):
    """데이터 요청 상태 변경 (관리자용)"""
    try:
        result = await service.update_request_status(request_id, status_data)
        return BaseResponse(
            success=True,
            data=result,
            message="데이터 요청 상태가 성공적으로 변경되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# === 카테고리 라우터 ===

@categories_router.post(
    "/",
    response_model=BaseResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="카테고리 생성",
    description="새로운 카테고리를 생성합니다."
)
async def create_category(
    request_data: CategoryCreateRequest,
    service: CategoryService = Depends(get_category_service)
):
    """카테고리 생성"""
    try:
        result = await service.create_category(request_data)
        return BaseResponse(
            success=True,
            data=result,
            message="카테고리가 성공적으로 생성되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@categories_router.get(
    "/",
    response_model=BaseResponse[List[CategoryResponse]],
    summary="카테고리 목록 조회",
    description="모든 활성화된 카테고리 목록을 조회합니다."
)
async def get_categories(
    service: CategoryService = Depends(get_category_service)
):
    """카테고리 목록 조회"""
    try:
        result = await service.get_categories()
        return BaseResponse(
            success=True,
            data=result,
            message="카테고리 목록을 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@categories_router.get(
    "/{category_id}",
    response_model=BaseResponse[CategoryResponse],
    summary="카테고리 상세 조회",
    description="특정 카테고리의 상세 정보를 조회합니다."
)
async def get_category(
    category_id: str,
    service: CategoryService = Depends(get_category_service)
):
    """카테고리 상세 조회"""
    try:
        result = await service.get_category(category_id)
        return BaseResponse(
            success=True,
            data=result,
            message="카테고리를 성공적으로 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# 라우터 포함
router.include_router(categories_router)