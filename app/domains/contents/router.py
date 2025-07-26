"""
콘텐츠 라우터 구현.

표준화된 응답, 페이지네이션, 에러 처리를 포함한 
콘텐츠 관련 작업을 위한 완전한 RESTful API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import ContentService
from .schemas import (
    ContentResponse,
    ContentCreate,
    ContentUpdate,
    ContentStats,
    ContentLike
)
from ...shared.responses import (
    BaseResponse,
    PaginatedResponse, 
    CreatedResponse,
    success_response
)
from ...shared.pagination import PaginationParams
from ...shared.exceptions.custom_exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException
)
from ...core.dependencies import get_content_service

router = APIRouter(
    prefix="/contents",
    tags=["콘텐츠"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"},
        422: {"description": "입력 데이터 검증 오류"},
        500: {"description": "서버 내부 오류"}
    }
)


@router.post(
    "/fetch",
    response_model=BaseResponse[List[ContentResponse]],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 콘텐츠 수집",
    description="""
    K-Startup API에서 콘텐츠 데이터를 가져와 데이터베이스에 저장합니다.
    
    **주요 기능:**
    - 공공데이터 API 실시간 호출
    - 중복 데이터 자동 감지 및 스킵
    - 새로운 데이터만 저장
    - 다양한 필터 조건 지원
    
    **사용 시나리오:**
    - 정기적인 데이터 동기화
    - 특정 콘텐츠 유형만 수집
    - 신규 콘텐츠 즉시 확인
    """,
    response_description="성공적으로 수집된 콘텐츠 목록"
)
async def fetch_contents(
    page_no: int = Query(
        1, 
        ge=1, 
        description="조회할 페이지 번호 (1부터 시작)",
        example=1
    ),
    num_of_rows: int = Query(
        10, 
        ge=1, 
        le=100, 
        description="한 페이지당 결과 수 (최대 100개)",
        example=10
    ),
    content_type: Optional[str] = Query(
        None, 
        description="콘텐츠 유형으로 필터링",
        example="동영상"
    ),
    category: Optional[str] = Query(
        None, 
        description="카테고리로 필터링",
        example="창업교육"
    ),
    service: ContentService = Depends(get_content_service)
):
    """
    K-Startup API에서 콘텐츠를 실시간으로 가져와 저장
    
    중복된 데이터는 자동으로 스킵되며, 새로운 데이터만 데이터베이스에 저장됩니다.
    """
    try:
        contents = await service.fetch_and_save_contents(
            page_no=page_no,
            num_of_rows=num_of_rows,
            content_type=content_type,
            category=category
        )
        
        response_data = [ContentResponse(
            id=str(c.id),
            content_data=c.content_data,
            source_url=c.source_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in contents]
        
        return success_response(
            data=response_data,
            message=f"총 {len(response_data)}개의 콘텐츠가 성공적으로 수집되었습니다"
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
    response_model=PaginatedResponse[ContentResponse],
    summary="콘텐츠 목록 조회",
    description="""
    저장된 콘텐츠 목록을 페이지네이션과 함께 조회합니다.
    
    **주요 기능:**
    - 표준 페이지네이션 지원 (page, size, sort, order)
    - 다양한 필터링 옵션 (검색, 콘텐츠 유형, 카테고리, 태그)
    - 정렬 옵션 지원
    
    **사용 시나리오:**
    - 웹사이트 메인 페이지 콘텐츠 목록
    - 관리자 페이지 데이터 관리
    - 모바일 앱 목록 화면
    """,
    response_description="페이지네이션된 콘텐츠 목록"
)
async def get_contents(
    pagination: PaginationParams = Depends(),
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    content_type: Optional[str] = Query(None, description="콘텐츠 유형 필터"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    tags: Optional[str] = Query(None, description="태그 필터 (콤마로 구분)"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    service: ContentService = Depends(get_content_service)
):
    """
    저장된 콘텐츠 목록을 조회합니다.
    
    표준 페이지네이션과 필터링을 지원합니다.
    """
    try:
        # 필터 조건 구성
        filters = {
            "keyword": keyword,
            "content_type": content_type,
            "category": category,
            "tags": tags.split(",") if tags else None,
            "is_active": is_active
        }
        # None 값 제거
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = await service.get_contents_paginated(pagination, filters)
        
        items = [ContentResponse(
            id=str(c.id),
            content_data=c.content_data,
            source_url=c.source_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in result.items]
        
        return PaginatedResponse(
            success=True,
            data=items,
            message="콘텐츠 목록 조회 성공",
            pagination=result.to_pagination_meta()
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/{content_id}",
    response_model=BaseResponse[ContentResponse],
    summary="특정 콘텐츠 상세 조회",
    description="""
    MongoDB ObjectId를 사용하여 특정 콘텐츠의 상세 정보를 조회합니다.
    
    **주요 기능:**
    - 고유 ID로 정확한 데이터 조회
    - 전체 콘텐츠 상세 정보 반환
    - 조회수 자동 증가
    - 표준 에러 응답 포맷
    
    **사용 시나리오:**
    - 콘텐츠 상세 페이지 조회
    - 특정 콘텐츠 확인
    - 관리 시스템에서 개별 데이터 조회
    """,
    response_description="콘텐츠 상세 정보"
)
async def get_content(
    content_id: str = Path(
        ...,
        description="조회할 콘텐츠의 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    ),
    service: ContentService = Depends(get_content_service)
):
    """
    특정 콘텐츠의 상세 정보를 조회합니다.
    
    MongoDB ObjectId를 사용하여 정확한 데이터를 반환하며, 조회수가 자동으로 증가합니다.
    """
    try:
        content = await service.get_content_by_id(content_id)
        if not content:
            raise NotFoundException("content", content_id, f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
        
        data = ContentResponse(
            id=str(content.id),
            content_data=content.content_data,
            source_url=content.source_url,
            is_active=content.is_active,
            created_at=content.created_at,
            updated_at=content.updated_at
        )
        
        return success_response(
            data=data,
            message="콘텐츠 상세 정보 조회 성공"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/",
    response_model=CreatedResponse[ContentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="새 콘텐츠 생성",
    description="새로운 콘텐츠를 생성합니다.",
    response_description="생성된 콘텐츠 정보"
)
async def create_content(
    content_data: ContentCreate,
    service: ContentService = Depends(get_content_service)
):
    """새 콘텐츠 생성"""
    try:
        content = await service.create_content(content_data)
        
        data = ContentResponse(
            id=str(content.id),
            content_data=content.content_data,
            source_url=content.source_url,
            is_active=content.is_active,
            created_at=content.created_at,
            updated_at=content.updated_at
        )
        
        return CreatedResponse(
            success=True,
            data=data,
            message="콘텐츠가 성공적으로 생성되었습니다",
            resource_id=str(content.id)
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.put(
    "/{content_id}",
    response_model=BaseResponse[ContentResponse],
    summary="콘텐츠 수정",
    description="기존 콘텐츠를 수정합니다.",
    response_description="수정된 콘텐츠 정보"
)
async def update_content(
    content_id: str = Path(..., description="수정할 콘텐츠 ID"),
    update_data: ContentUpdate = ...,
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 수정"""
    try:
        content = await service.update_content(content_id, update_data)
        if not content:
            raise NotFoundException("content", content_id, f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
        
        data = ContentResponse(
            id=str(content.id),
            content_data=content.content_data,
            source_url=content.source_url,
            is_active=content.is_active,
            created_at=content.created_at,
            updated_at=content.updated_at
        )
        
        return success_response(
            data=data,
            message="콘텐츠가 성공적으로 수정되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 수정 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete(
    "/{content_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="콘텐츠 삭제",
    description="콘텐츠를 삭제(비활성화)합니다.",
    response_description="삭제 성공 메시지"
)
async def delete_content(
    content_id: str = Path(..., description="삭제할 콘텐츠 ID"),
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 삭제 (비활성화)"""
    try:
        success = await service.delete_content(content_id)
        if not success:
            raise NotFoundException("content", content_id, f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
        
        return success_response(
            data={"content_id": content_id, "deleted": True},
            message="콘텐츠가 성공적으로 삭제되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"콘텐츠 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/{content_id}/like",
    response_model=BaseResponse[dict],
    summary="콘텐츠 좋아요",
    description="콘텐츠에 좋아요를 추가합니다.",
    response_description="좋아요 성공 메시지"
)
async def like_content(
    content_id: str = Path(..., description="좋아요할 콘텐츠 ID"),
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 좋아요"""
    try:
        success = await service.like_content(content_id)
        if not success:
            raise NotFoundException("content", content_id, f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
        
        return success_response(
            data={"content_id": content_id, "liked": True},
            message="좋아요가 추가되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다")
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"좋아요 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/recent",
    response_model=BaseResponse[List[ContentResponse]],
    summary="최근 콘텐츠 조회",
    description="최근에 등록된 콘텐츠 목록을 조회합니다."
)
async def get_recent_contents(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 콘텐츠 수"),
    service: ContentService = Depends(get_content_service)
):
    """최근 콘텐츠 조회"""
    try:
        contents = await service.get_recent_contents(limit)
        
        response_data = [ContentResponse(
            id=str(c.id),
            content_data=c.content_data,
            source_url=c.source_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in contents]
        
        return success_response(
            data=response_data,
            message=f"최근 {len(response_data)}개의 콘텐츠를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최근 콘텐츠 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/popular",
    response_model=BaseResponse[List[ContentResponse]],
    summary="인기 콘텐츠 조회",
    description="조회수 기준 인기 콘텐츠 목록을 조회합니다."
)
async def get_popular_contents(
    limit: int = Query(10, ge=1, le=50, description="조회할 인기 콘텐츠 수"),
    service: ContentService = Depends(get_content_service)
):
    """인기 콘텐츠 조회 (조회수 기준)"""
    try:
        contents = await service.get_popular_contents(limit)
        
        response_data = [ContentResponse(
            id=str(c.id),
            content_data=c.content_data,
            source_url=c.source_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in contents]
        
        return success_response(
            data=response_data,
            message=f"인기 {len(response_data)}개의 콘텐츠를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"인기 콘텐츠 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=BaseResponse[ContentStats],
    summary="콘텐츠 통계 조회",
    description="콘텐츠에 대한 통계 정보를 조회합니다."
)
async def get_content_statistics(
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 통계 조회"""
    try:
        stats = await service.get_content_statistics()
        return success_response(
            data=stats,
            message="콘텐츠 통계 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )