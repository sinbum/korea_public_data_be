"""
Content Router implementation.

Provides REST API endpoints for content-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from datetime import datetime
from .service import ContentService
from .models import ContentResponse, ContentCreate, ContentUpdate
from ...shared.schemas import PaginatedResponse

router = APIRouter(
    prefix="/contents",
    tags=["콘텐츠"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)


def get_content_service() -> ContentService:
    return ContentService()


@router.post(
    "/fetch",
    response_model=List[ContentResponse],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 콘텐츠 수집",
    description="K-Startup API에서 콘텐츠 데이터를 가져와 데이터베이스에 저장합니다."
)
def fetch_contents(
    page_no: int = Query(1, ge=1, description="조회할 페이지 번호"),
    num_of_rows: int = Query(10, ge=1, le=100, description="한 페이지당 결과 수"),
    content_type: Optional[str] = Query(None, description="콘텐츠 유형 필터"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    service: ContentService = Depends(get_content_service)
):
    """K-Startup API에서 콘텐츠를 가져와 저장"""
    try:
        contents = service.fetch_and_save_contents(
            page_no=page_no,
            num_of_rows=num_of_rows,
            content_type=content_type,
            category=category
        )
        return [ContentResponse(
            id=str(c.id),
            content_data=c.content_data,
            source_url=c.source_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in contents]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=PaginatedResponse[ContentResponse],
    status_code=status.HTTP_200_OK,
    summary="콘텐츠 목록 조회"
)
def get_contents(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    is_active: bool = Query(True, description="활성 상태 필터"),
    service: ContentService = Depends(get_content_service)
):
    """저장된 콘텐츠 목록을 조회합니다."""
    result = service.get_contents(page=page, page_size=page_size, is_active=is_active)
    
    items = [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in result.items]
    
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
    "/{content_id}",
    response_model=ContentResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 콘텐츠 상세 조회"
)
def get_content(
    content_id: str = Path(..., description="조회할 콘텐츠의 고유 ID"),
    service: ContentService = Depends(get_content_service)
):
    """특정 콘텐츠의 상세 정보를 조회합니다. (조회수 자동 증가)"""
    content = service.get_content_by_id(content_id)
    if not content:
        raise HTTPException(
            status_code=404,
            detail="해당 ID의 콘텐츠를 찾을 수 없습니다"
        )
    
    return ContentResponse(
        id=str(content.id),
        content_data=content.content_data,
        source_url=content.source_url,
        is_active=content.is_active,
        created_at=content.created_at,
        updated_at=content.updated_at
    )


@router.post("/", response_model=ContentResponse)
def create_content(
    content_data: ContentCreate,
    service: ContentService = Depends(get_content_service)
):
    """새 콘텐츠 생성"""
    content = service.create_content(content_data)
    return ContentResponse(
        id=str(content.id),
        content_data=content.content_data,
        source_url=content.source_url,
        is_active=content.is_active,
        created_at=content.created_at,
        updated_at=content.updated_at
    )


@router.put("/{content_id}", response_model=ContentResponse)
def update_content(
    content_id: str,
    update_data: ContentUpdate,
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 수정"""
    content = service.update_content(content_id, update_data)
    if not content:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    
    return ContentResponse(
        id=str(content.id),
        content_data=content.content_data,
        source_url=content.source_url,
        is_active=content.is_active,
        created_at=content.created_at,
        updated_at=content.updated_at
    )


@router.delete("/{content_id}")
def delete_content(
    content_id: str,
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 삭제 (비활성화)"""
    success = service.delete_content(content_id)
    if not success:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    
    return {"message": "콘텐츠가 삭제되었습니다"}


@router.post("/{content_id}/like")
def like_content(
    content_id: str = Path(..., description="좋아요할 콘텐츠 ID"),
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 좋아요"""
    success = service.like_content(content_id)
    if not success:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다")
    
    return {"message": "좋아요가 추가되었습니다"}


@router.get("/search/{search_term}", response_model=List[ContentResponse])
def search_contents(
    search_term: str = Path(..., description="검색어"),
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 검색"""
    contents = service.search_contents(search_term)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/type/{content_type}", response_model=List[ContentResponse])
def get_contents_by_type(
    content_type: str = Path(..., description="콘텐츠 유형"),
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 유형별 조회"""
    contents = service.get_contents_by_type(content_type)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/category/{category}", response_model=List[ContentResponse])
def get_contents_by_category(
    category: str = Path(..., description="카테고리"),
    service: ContentService = Depends(get_content_service)
):
    """카테고리별 콘텐츠 조회"""
    contents = service.get_contents_by_category(category)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/tags/{tags}", response_model=List[ContentResponse])
def get_contents_by_tags(
    tags: str = Path(..., description="태그 (콤마로 구분)"),
    service: ContentService = Depends(get_content_service)
):
    """태그별 콘텐츠 조회"""
    tag_list = [tag.strip() for tag in tags.split(",")]
    contents = service.get_contents_by_tags(tag_list)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/popular", response_model=List[ContentResponse])
def get_popular_contents(
    limit: int = Query(10, ge=1, le=50, description="조회할 인기 콘텐츠 수"),
    service: ContentService = Depends(get_content_service)
):
    """인기 콘텐츠 조회 (조회수 기준)"""
    contents = service.get_popular_contents(limit)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/most-liked", response_model=List[ContentResponse])
def get_most_liked_contents(
    limit: int = Query(10, ge=1, le=50, description="조회할 좋아요 많은 콘텐츠 수"),
    service: ContentService = Depends(get_content_service)
):
    """좋아요 많은 콘텐츠 조회"""
    contents = service.get_most_liked_contents(limit)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/recent", response_model=List[ContentResponse])
def get_recent_contents(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 콘텐츠 수"),
    service: ContentService = Depends(get_content_service)
):
    """최근 콘텐츠 조회"""
    contents = service.get_recent_contents(limit)
    return [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in contents]


@router.get("/filter", response_model=PaginatedResponse[ContentResponse])
def get_contents_with_filter(
    content_type: Optional[str] = Query(None, description="콘텐츠 유형"),
    category: Optional[str] = Query(None, description="카테고리"),
    tags: Optional[str] = Query(None, description="태그 (콤마로 구분)"),
    min_view_count: Optional[int] = Query(None, description="최소 조회수"),
    min_like_count: Optional[int] = Query(None, description="최소 좋아요 수"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    service: ContentService = Depends(get_content_service)
):
    """필터 조건에 따른 콘텐츠 조회"""
    tag_list = None
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
    
    result = service.get_contents_with_filter(
        content_type=content_type,
        category=category,
        tags=tag_list,
        min_view_count=min_view_count,
        min_like_count=min_like_count,
        page=page,
        page_size=page_size
    )
    
    items = [ContentResponse(
        id=str(c.id),
        content_data=c.content_data,
        source_url=c.source_url,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at
    ) for c in result.items]
    
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
def get_content_statistics(
    service: ContentService = Depends(get_content_service)
):
    """콘텐츠 통계 조회"""
    return service.get_content_statistics()