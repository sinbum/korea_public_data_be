"""
Statistics Router implementation.

Provides REST API endpoints for statistics-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import StatisticsService
from .models import StatisticsResponse, StatisticsCreate, StatisticsUpdate
from ...shared.schemas import PaginatedResponse
from ...core.dependencies import get_statistics_service

router = APIRouter(
    prefix="/statistics",
    tags=["통계"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)


# DI function is imported from dependencies module


@router.post(
    "/fetch",
    response_model=List[StatisticsResponse],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 통계 수집",
    description="K-Startup API에서 통계 데이터를 가져와 데이터베이스에 저장합니다."
)
def fetch_statistics(
    page_no: int = Query(1, ge=1, description="조회할 페이지 번호"),
    num_of_rows: int = Query(10, ge=1, le=100, description="한 페이지당 결과 수"),
    year: Optional[int] = Query(None, description="연도 필터"),
    month: Optional[int] = Query(None, ge=1, le=12, description="월 필터"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """K-Startup API에서 통계를 가져와 저장"""
    try:
        statistics_list = service.fetch_and_save_statistics(
            page_no=page_no,
            num_of_rows=num_of_rows,
            year=year,
            month=month
        )
        return [StatisticsResponse(
            id=str(s.id),
            statistical_data=s.statistical_data,
            source_url=s.source_url,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in statistics_list]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=PaginatedResponse[StatisticsResponse],
    status_code=status.HTTP_200_OK,
    summary="통계 목록 조회"
)
def get_statistics(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    is_active: bool = Query(True, description="활성 상태 필터"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """저장된 통계 목록을 조회합니다."""
    result = service.get_statistics(page=page, page_size=page_size, is_active=is_active)
    
    items = [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in result.items]
    
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
    "/{statistics_id}",
    response_model=StatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 통계 상세 조회"
)
def get_statistics_by_id(
    statistics_id: str = Path(..., description="조회할 통계의 고유 ID"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """특정 통계의 상세 정보를 조회합니다."""
    statistics = service.get_statistics_by_id(statistics_id)
    if not statistics:
        raise HTTPException(
            status_code=404,
            detail="해당 ID의 통계를 찾을 수 없습니다"
        )
    
    return StatisticsResponse(
        id=str(statistics.id),
        statistical_data=statistics.statistical_data,
        source_url=statistics.source_url,
        is_active=statistics.is_active,
        created_at=statistics.created_at,
        updated_at=statistics.updated_at
    )


@router.post("/", response_model=StatisticsResponse)
def create_statistics(
    statistics_data: StatisticsCreate,
    service: StatisticsService = Depends(get_statistics_service)
):
    """새 통계 생성"""
    statistics = service.create_statistics(statistics_data)
    return StatisticsResponse(
        id=str(statistics.id),
        statistical_data=statistics.statistical_data,
        source_url=statistics.source_url,
        is_active=statistics.is_active,
        created_at=statistics.created_at,
        updated_at=statistics.updated_at
    )


@router.put("/{statistics_id}", response_model=StatisticsResponse)
def update_statistics(
    statistics_id: str,
    update_data: StatisticsUpdate,
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 수정"""
    statistics = service.update_statistics(statistics_id, update_data)
    if not statistics:
        raise HTTPException(status_code=404, detail="통계를 찾을 수 없습니다")
    
    return StatisticsResponse(
        id=str(statistics.id),
        statistical_data=statistics.statistical_data,
        source_url=statistics.source_url,
        is_active=statistics.is_active,
        created_at=statistics.created_at,
        updated_at=statistics.updated_at
    )


@router.delete("/{statistics_id}")
def delete_statistics(
    statistics_id: str,
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 삭제 (비활성화)"""
    success = service.delete_statistics(statistics_id)
    if not success:
        raise HTTPException(status_code=404, detail="통계를 찾을 수 없습니다")
    
    return {"message": "통계가 삭제되었습니다"}


@router.get("/search/{search_term}", response_model=List[StatisticsResponse])
def search_statistics(
    search_term: str = Path(..., description="검색어"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 검색"""
    statistics_list = service.search_statistics(search_term)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/type/{stat_type}", response_model=List[StatisticsResponse])
def get_statistics_by_type(
    stat_type: str = Path(..., description="통계 유형"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 유형별 조회"""
    statistics_list = service.get_statistics_by_type(stat_type)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/year/{year}", response_model=List[StatisticsResponse])
def get_statistics_by_year(
    year: int = Path(..., description="연도"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """연도별 통계 조회"""
    statistics_list = service.get_statistics_by_year(year)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/year-month/{year}/{month}", response_model=List[StatisticsResponse])
def get_statistics_by_year_month(
    year: int = Path(..., description="연도"),
    month: int = Path(..., ge=1, le=12, description="월"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """연월별 통계 조회"""
    statistics_list = service.get_statistics_by_year_month(year, month)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/period/{period}", response_model=List[StatisticsResponse])
def get_statistics_by_period(
    period: str = Path(..., description="기간"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """기간별 통계 조회"""
    statistics_list = service.get_statistics_by_period(period)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/recent", response_model=List[StatisticsResponse])
def get_recent_statistics(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 통계 수"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """최근 통계 조회"""
    statistics_list = service.get_recent_statistics(limit)
    return [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in statistics_list]


@router.get("/filter", response_model=PaginatedResponse[StatisticsResponse])
def get_statistics_with_filter(
    stat_type: Optional[str] = Query(None, description="통계 유형"),
    period: Optional[str] = Query(None, description="기간"),
    year: Optional[int] = Query(None, description="연도"),
    month: Optional[int] = Query(None, ge=1, le=12, description="월"),
    min_total_count: Optional[int] = Query(None, description="최소 총 건수"),
    min_success_rate: Optional[float] = Query(None, description="최소 성공률"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 데이터 수"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """필터 조건에 따른 통계 조회"""
    result = service.get_statistics_with_filter(
        stat_type=stat_type,
        period=period,
        year=year,
        month=month,
        min_total_count=min_total_count,
        min_success_rate=min_success_rate,
        page=page,
        page_size=page_size
    )
    
    items = [StatisticsResponse(
        id=str(s.id),
        statistical_data=s.statistical_data,
        source_url=s.source_url,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at
    ) for s in result.items]
    
    return PaginatedResponse(
        items=items,
        total_count=result.total_count,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        has_next=result.has_next,
        has_previous=result.has_previous
    )


@router.get("/aggregated-metrics", response_model=dict)
def get_aggregated_metrics(
    stat_type: Optional[str] = Query(None, description="통계 유형"),
    year: Optional[int] = Query(None, description="연도"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """집계 지표 조회"""
    return service.get_aggregated_metrics(stat_type, year)


@router.get("/overview", response_model=dict)
def get_statistics_overview(
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 개요 조회"""
    return service.get_statistics_overview()


@router.get("/report/monthly/{year}/{month}", response_model=dict)
def generate_monthly_report(
    year: int = Path(..., description="연도"),
    month: int = Path(..., ge=1, le=12, description="월"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """월별 리포트 생성"""
    return service.generate_monthly_report(year, month)


@router.get("/report/yearly/{year}", response_model=dict)
def generate_yearly_report(
    year: int = Path(..., description="연도"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """연별 리포트 생성"""
    return service.generate_yearly_report(year)