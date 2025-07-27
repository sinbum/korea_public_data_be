from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import AnnouncementService
from .models import AnnouncementResponse, AnnouncementCreate, AnnouncementUpdate
from .schemas import (
    AnnouncementResponse as AnnouncementResponseSchema,
    AnnouncementCreate as AnnouncementCreateSchema,
    AnnouncementUpdate as AnnouncementUpdateSchema,
    AnnouncementSummary,
    AnnouncementStats,
    AnnouncementSearch
)
from ...shared.responses import (
    BaseResponse,
    PaginatedResponse, 
    CreatedResponse,
    success_response,
    created_response,
    error_response
)
from ...shared.schemas import (
    BaseResponse as BaseResponseSchema,
    ErrorResponse,
    PaginatedResponse as PaginatedResponseSchema,
    ValidationErrorResponse,
    WRITE_HTTP_RESPONSES,
    READ_ONLY_HTTP_RESPONSES
)
from ...shared.pagination import PaginationParams, FilterParams
from ...shared.exceptions.custom_exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException
)
from ...core.dependencies import get_announcement_service

router = APIRouter(
    prefix="/announcements",
    tags=["사업공고"],
    responses=WRITE_HTTP_RESPONSES
)


# DI function is imported from dependencies module


@router.post(
    "/fetch",
    response_model=BaseResponseSchema[List[AnnouncementResponseSchema]],
    status_code=status.HTTP_200_OK,
    summary="공공데이터에서 사업공고 수집",
    description="""
    공공데이터포털의 창업진흥원 K-Startup API에서 사업공고 데이터를 가져와 데이터베이스에 저장합니다.
    
    **주요 기능:**
    - 공공데이터 API 실시간 호출
    - 중복 데이터 자동 감지 및 스킵
    - 새로운 데이터만 저장
    - 다양한 필터 조건 지원
    
    **사용 시나리오:**
    - 정기적인 데이터 동기화
    - 특정 사업 유형의 공고만 수집
    - 신규 공고 즉시 확인
    
    **API 제한사항:**
    - 외부 API 호출 시간: 최대 30초
    - 한 번에 최대 100개 항목 수집 가능
    - Rate Limiting: 분당 5회 호출 제한
    """,
    response_description="성공적으로 수집된 사업공고 목록과 수집 통계",
    operation_id="fetch_announcements_from_public_api",
    responses={
        **WRITE_HTTP_RESPONSES,
        200: {
            "model": BaseResponseSchema[List[AnnouncementResponseSchema]],
            "description": "성공적으로 데이터를 수집함",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "success",
                        "data": [
                            {
                                "id": "674a1b2c3d4e5f6789abcdef",
                                "announcement_data": {
                                    "announcement_id": "174329",
                                    "title": "2025년 민간주도 스타트업 스케일업 실증지원사업",
                                    "business_category": "기술개발(R&D)",
                                    "support_region": "전북"
                                },
                                "source_url": "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do",
                                "is_active": True,
                                "created_at": "2025-07-27T00:00:00Z",
                                "updated_at": "2025-07-27T00:00:00Z"
                            }
                        ],
                        "message": "총 1개의 사업공고가 성공적으로 수집되었습니다",
                        "timestamp": "2025-07-27T00:00:00Z"
                    }
                }
            }
        }
    }
)
async def fetch_announcements(
    page_no: int = Query(
        1, 
        ge=1, 
        description="조회할 페이지 번호 (1부터 시작)",
        example=1
    ),
    num_of_rows: int = Query(
        100, 
        ge=1, 
        le=100, 
        description="한 페이지당 결과 수 (최대 100개)",
        example=100
    ),
    business_name: Optional[str] = Query(
        None, 
        description="사업명으로 필터링 (부분 검색 가능)",
        example="창업도약패키지"
    ),
    business_type: Optional[str] = Query(
        None, 
        description="사업유형으로 필터링",
        example="정부지원사업"
    ),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """
    공공데이터에서 사업공고 정보를 실시간으로 가져와 저장
    
    중복된 데이터는 자동으로 스킵되며, 새로운 데이터만 데이터베이스에 저장됩니다.
    """
    try:
        announcements = await service.fetch_and_save_announcements(
            page_no=page_no,
            num_of_rows=num_of_rows,
            business_name=business_name,
            business_type=business_type
        )
        
        response_data = []
        for a in announcements:
            # Convert Announcement model to response schema manually to handle datetime serialization
            if hasattr(a.announcement_data, 'model_dump'):
                announcement_data_dict = a.announcement_data.model_dump(mode='json')
            elif hasattr(a.announcement_data, 'dict'):
                announcement_data_dict = a.announcement_data.dict()
            else:
                announcement_data_dict = dict(a.announcement_data)
            
            # Convert datetime objects to strings in the announcement_data_dict
            for key, value in announcement_data_dict.items():
                if hasattr(value, 'isoformat'):  # datetime object
                    announcement_data_dict[key] = value.isoformat() + "Z"
            
            response_item = AnnouncementResponseSchema(
                id=str(a.id),
                announcement_data=announcement_data_dict,
                source_url=a.source_url,
                is_active=a.is_active,
                created_at=a.created_at.isoformat() + "Z" if a.created_at else None,
                updated_at=a.updated_at.isoformat() + "Z" if a.updated_at else None
            )
            response_data.append(response_item)
        
        return success_response(
            data=response_data,
            message=f"총 {len(response_data)}개의 사업공고가 성공적으로 수집되었습니다"
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}"
        )
 

@router.get(
    "/",
    response_model=PaginatedResponse[AnnouncementResponseSchema],
    summary="사업공고 목록 조회",
    description="""
    저장된 사업공고 목록을 페이지네이션과 함께 조회합니다.
    
    **주요 기능:**
    - 표준 페이지네이션 지원 (page, size, sort, order)
    - 다양한 필터링 옵션 (검색, 상태, 카테고리, 날짜)
    - 정렬 옵션 지원
    
    **사용 시나리오:**
    - 웹사이트 메인 페이지 공고 목록
    - 관리자 페이지 데이터 관리
    - 모바일 앱 목록 화면
    """,
    response_description="페이지네이션된 사업공고 목록",
    responses=READ_ONLY_HTTP_RESPONSES
)
async def get_announcements(
    pagination: PaginationParams = Depends(),
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    business_type: Optional[str] = Query(None, description="사업 유형 필터"),
    status: Optional[str] = Query(None, description="상태 필터"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """
    저장된 사업공고 목록을 조회합니다.
    
    표준 페이지네이션과 필터링을 지원합니다.
    """
    try:
        # Use the simpler get_announcements method for now
        result = service.get_announcements(
            page=pagination.page,
            page_size=pagination.size,
            is_active=is_active if is_active is not None else True
        )
        
        items = []
        for a in result.items:
            # Convert Announcement model to response schema manually to handle datetime serialization
            if hasattr(a.announcement_data, 'model_dump'):
                announcement_data_dict = a.announcement_data.model_dump(mode='json')
            elif hasattr(a.announcement_data, 'dict'):
                announcement_data_dict = a.announcement_data.dict()
            else:
                announcement_data_dict = dict(a.announcement_data)
            
            # Convert datetime objects to strings in the announcement_data_dict
            for key, value in announcement_data_dict.items():
                if hasattr(value, 'isoformat'):  # datetime object
                    announcement_data_dict[key] = value.isoformat() + "Z"
            
            response_item = AnnouncementResponseSchema(
                id=str(a.id),
                announcement_data=announcement_data_dict,
                source_url=a.source_url,
                is_active=a.is_active,
                created_at=a.created_at.isoformat() + "Z" if a.created_at else None,
                updated_at=a.updated_at.isoformat() + "Z" if a.updated_at else None
            )
            items.append(response_item)
        
        import math
        total_pages = math.ceil(result.total_count / pagination.size) if result.total_count > 0 else 1
        
        return PaginatedResponse(
            success=True,
            items=items,
            message="사업공고 목록 조회 성공",
            pagination={
                "page": result.page,
                "size": pagination.size,
                "total": result.total_count,
                "total_pages": total_pages,
                "has_next": result.has_next,
                "has_previous": result.has_previous
            }
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업공고 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/{announcement_id}",
    response_model=BaseResponse[AnnouncementResponseSchema],
    summary="특정 사업공고 상세 조회",
    description="""
    MongoDB ObjectId를 사용하여 특정 사업공고의 상세 정보를 조회합니다.
    
    **주요 기능:**
    - 고유 ID로 정확한 데이터 조회
    - 전체 공고 상세 정보 반환
    - 표준 에러 응답 포맷
    
    **사용 시나리오:**
    - 공고 상세 페이지 조회
    - 특정 공고 정보 확인
    - 관리 시스템에서 개별 데이터 조회
    """,
    response_description="사업공고 상세 정보",
    responses=READ_ONLY_HTTP_RESPONSES
)
async def get_announcement(
    announcement_id: str = Path(
        ...,
        description="조회할 사업공고의 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    ),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """
    특정 사업공고의 상세 정보를 조회합니다.
    
    MongoDB ObjectId를 사용하여 정확한 데이터를 반환합니다.
    """
    try:
        announcement = await service.get_announcement_by_id(announcement_id)
        if not announcement:
            raise NotFoundException("announcement", announcement_id, f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
        
        data = AnnouncementResponseSchema(
            id=str(announcement.id),
            announcement_data=announcement.announcement_data,
            source_url=announcement.source_url,
            is_active=announcement.is_active,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at
        )
        
        return success_response(
            data=data,
            message="사업공고 상세 정보 조회 성공"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업공고 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/",
    response_model=CreatedResponse[AnnouncementResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="새 사업공고 생성",
    description="새로운 사업공고를 생성합니다.",
    response_description="생성된 사업공고 정보",
    responses=WRITE_HTTP_RESPONSES
)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    service: AnnouncementService = Depends(get_announcement_service)
):
    """새 사업공고 생성"""
    try:
        announcement = await service.create_announcement(announcement_data)
        
        data = AnnouncementResponseSchema(
            id=str(announcement.id),
            announcement_data=announcement.announcement_data,
            source_url=announcement.source_url,
            is_active=announcement.is_active,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at
        )
        
        return CreatedResponse(
            success=True,
            data=data,
            message="사업공고가 성공적으로 생성되었습니다",
            resource_id=str(announcement.id)
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업공고 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.put(
    "/{announcement_id}",
    response_model=BaseResponse[AnnouncementResponseSchema],
    summary="사업공고 수정",
    description="기존 사업공고를 수정합니다.",
    response_description="수정된 사업공고 정보",
    responses=WRITE_HTTP_RESPONSES
)
async def update_announcement(
    announcement_id: str = Path(..., description="수정할 사업공고 ID"),
    update_data: AnnouncementUpdate = ...,
    service: AnnouncementService = Depends(get_announcement_service)
):
    """사업공고 수정"""
    try:
        announcement = await service.update_announcement(announcement_id, update_data)
        if not announcement:
            raise NotFoundException("announcement", announcement_id, f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
        
        data = AnnouncementResponseSchema(
            id=str(announcement.id),
            announcement_data=announcement.announcement_data,
            source_url=announcement.source_url,
            is_active=announcement.is_active,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at
        )
        
        return success_response(
            data=data,
            message="사업공고가 성공적으로 수정되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업공고 수정 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete(
    "/{announcement_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="사업공고 삭제",
    description="사업공고를 삭제(비활성화)합니다.",
    response_description="삭제 성공 메시지",
    responses=WRITE_HTTP_RESPONSES
)
async def delete_announcement(
    announcement_id: str = Path(..., description="삭제할 사업공고 ID"),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """사업공고 삭제 (비활성화)"""
    try:
        success = await service.delete_announcement(announcement_id)
        if not success:
            raise NotFoundException("announcement", announcement_id, f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
        
        return success_response(
            data={"announcement_id": announcement_id, "deleted": True},
            message="사업공고가 성공적으로 삭제되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {announcement_id}에 해당하는 사업공고를 찾을 수 없습니다")
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업공고 삭제 중 오류가 발생했습니다: {str(e)}"
        )


# 검색은 메인 GET / 엔드포인트의 keyword 파라미터로 통합됨

@router.get(
    "/recent",
    response_model=BaseResponse[List[AnnouncementResponseSchema]],
    summary="최근 사업공고 조회",
    description="최근에 등록된 사업공고 목록을 조회합니다.",
    responses=READ_ONLY_HTTP_RESPONSES
)
async def get_recent_announcements(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 공고 수"),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """최근 공고 조회"""
    try:
        announcements = await service.get_recent_announcements(limit)
        
        response_data = [AnnouncementResponseSchema(
            id=str(a.id),
            announcement_data=a.announcement_data,
            source_url=a.source_url,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at
        ) for a in announcements]
        
        return success_response(
            data=response_data,
            message=f"최근 {len(response_data)}개의 사업공고를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최근 공고 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=BaseResponse[dict],
    summary="사업공고 통계 조회",
    description="사업공고에 대한 통계 정보를 조회합니다.",
    responses=READ_ONLY_HTTP_RESPONSES
)
async def get_announcement_statistics(
    service: AnnouncementService = Depends(get_announcement_service)
):
    """공고 통계 조회"""
    try:
        stats = await service.get_announcement_statistics()
        return success_response(
            data=stats,
            message="사업공고 통계 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )