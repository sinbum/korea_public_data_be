"""
통계 라우터 구현.

표준화된 응답, 페이지네이션, 에러 처리를 포함한 
통계 관련 작업을 위한 완전한 RESTful API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import StatisticsService
from .schemas import (
    StatisticsResponse,
    StatisticsCreate,
    StatisticsUpdate,
    StatisticsOverview,
    MonthlyReport,
    YearlyReport,
    AggregatedMetrics
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
from ...core.dependencies import get_statistics_service

router = APIRouter(
    prefix="/statistics",
    tags=["통계"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"},
        422: {"description": "입력 데이터 검증 오류"},
        500: {"description": "서버 내부 오류"}
    }
)


@router.post(
    "/fetch",
    response_model=BaseResponse[List[StatisticsResponse]],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 통계 수집",
    description="""
    K-Startup API에서 통계 데이터를 가져와 데이터베이스에 저장합니다.
    
    **주요 기능:**
    - 공공데이터 API 실시간 호출
    - 중복 데이터 자동 감지 및 스킵
    - 새로운 데이터만 저장
    - 다양한 필터 조건 지원
    
    **사용 시나리오:**
    - 정기적인 데이터 동기화
    - 특정 연도/월의 통계만 수집
    - 신규 통계 즉시 확인
    """,
    response_description="성공적으로 수집된 통계 목록"
)
async def fetch_statistics(
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
    year: Optional[int] = Query(
        None, 
        description="연도로 필터링",
        example=2024
    ),
    month: Optional[int] = Query(
        None, 
        ge=1, 
        le=12, 
        description="월로 필터링",
        example=3
    ),
    order_by_latest: bool = Query(
        True,
        description="최신순으로 데이터 조회 (최신 등록일시부터 조회)",
        example=True
    ),
    service: StatisticsService = Depends(get_statistics_service)
):
    """
    K-Startup API에서 통계를 실시간으로 가져와 저장
    
    중복된 데이터는 자동으로 스킵되며, 새로운 데이터만 데이터베이스에 저장됩니다.
    """
    try:
        statistics_list = service.fetch_and_save_statistics(
            page_no=page_no,
            num_of_rows=num_of_rows,
            year=year,
            month=month,
            order_by_latest=order_by_latest
        )
        
        response_data = []
        for s in statistics_list:
            # Ensure statistical_data is properly serialized
            if hasattr(s.statistical_data, 'model_dump'):
                statistical_data_dict = s.statistical_data.model_dump(mode='json')
            elif isinstance(s.statistical_data, dict):
                statistical_data_dict = s.statistical_data
            else:
                # Convert to dict if it's some other type
                statistical_data_dict = dict(s.statistical_data) if s.statistical_data else {}
            
            # Create plain dictionary instead of Pydantic model
            response_item = {
                "id": str(s.id),
                "statistical_data": statistical_data_dict,
                "source_url": s.source_url,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            response_data.append(response_item)
        
        return success_response(
            data=response_data,
            message=f"총 {len(response_data)}개의 통계가 성공적으로 수집되었습니다"
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
    response_model=PaginatedResponse[StatisticsResponse],
    summary="통계 목록 조회",
    description="""
    저장된 통계 목록을 페이지네이션과 함께 조회합니다.
    
    **주요 기능:**
    - 표준 페이지네이션 지원 (page, size, sort, order)
    - 다양한 필터링 옵션 (검색, 통계 유형, 기간, 연도)
    - 정렬 옵션 지원
    
    **사용 시나리오:**
    - 웹사이트 메인 페이지 통계 목록
    - 관리자 페이지 데이터 관리
    - 모바일 앱 목록 화면
    """,
    response_description="페이지네이션된 통계 목록"
)
async def get_statistics(
    pagination: PaginationParams = Depends(),
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    stat_type: Optional[str] = Query(None, description="통계 유형 필터"),
    period: Optional[str] = Query(None, description="기간 필터"),
    year: Optional[int] = Query(None, description="연도 필터"),
    month: Optional[int] = Query(None, ge=1, le=12, description="월 필터"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    order_by_latest: bool = Query(True, description="최신순 정렬 (기본값: True)"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """
    저장된 통계 목록을 조회합니다.
    
    표준 페이지네이션과 필터링을 지원합니다.
    """
    try:
        # 필터 조건 구성
        filters = {
            "keyword": keyword,
            "stat_type": stat_type,
            "period": period,
            "year": year,
            "month": month,
            "is_active": is_active
        }
        # None 값 제거
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = await service.get_statistics_paginated(pagination, filters)
        
        items = [StatisticsResponse(
            id=str(s.id),
            statistical_data=s.statistical_data,
            source_url=s.source_url,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in result.items]
        
        return PaginatedResponse(
            success=True,
            items=items,
            message="통계 목록 조회 성공",
            pagination=result.to_pagination_meta()
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/{statistics_id}",
    response_model=BaseResponse[StatisticsResponse],
    summary="특정 통계 상세 조회",
    description="""
    MongoDB ObjectId를 사용하여 특정 통계의 상세 정보를 조회합니다.
    
    **주요 기능:**
    - 고유 ID로 정확한 데이터 조회
    - 전체 통계 상세 정보 반환
    - 표준 에러 응답 포맷
    
    **사용 시나리오:**
    - 통계 상세 페이지 조회
    - 특정 통계 확인
    - 관리 시스템에서 개별 데이터 조회
    """,
    response_description="통계 상세 정보"
)
async def get_statistics_by_id(
    statistics_id: str = Path(
        ...,
        description="조회할 통계의 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    ),
    service: StatisticsService = Depends(get_statistics_service)
):
    """
    특정 통계의 상세 정보를 조회합니다.
    
    MongoDB ObjectId를 사용하여 정확한 데이터를 반환합니다.
    """
    try:
        statistics = service.get_statistics_by_id(statistics_id)
        if not statistics:
            raise NotFoundException("statistics", statistics_id, f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
        
        data = StatisticsResponse(
            id=str(statistics.id),
            statistical_data=statistics.statistical_data,
            source_url=statistics.source_url,
            is_active=statistics.is_active,
            created_at=statistics.created_at,
            updated_at=statistics.updated_at
        )
        
        return success_response(
            data=data,
            message="통계 상세 정보 조회 성공"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/",
    response_model=CreatedResponse[StatisticsResponse],
    status_code=status.HTTP_201_CREATED,
    summary="새 통계 생성",
    description="새로운 통계를 생성합니다.",
    response_description="생성된 통계 정보"
)
async def create_statistics(
    statistics_data: StatisticsCreate,
    service: StatisticsService = Depends(get_statistics_service)
):
    """새 통계 생성"""
    try:
        statistics = service.create_statistics(statistics_data)
        
        data = StatisticsResponse(
            id=str(statistics.id),
            statistical_data=statistics.statistical_data,
            source_url=statistics.source_url,
            is_active=statistics.is_active,
            created_at=statistics.created_at,
            updated_at=statistics.updated_at
        )
        
        return CreatedResponse(
            success=True,
            data=data,
            message="통계가 성공적으로 생성되었습니다",
            resource_id=str(statistics.id)
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.put(
    "/{statistics_id}",
    response_model=BaseResponse[StatisticsResponse],
    summary="통계 수정",
    description="기존 통계를 수정합니다.",
    response_description="수정된 통계 정보"
)
async def update_statistics(
    statistics_id: str = Path(..., description="수정할 통계 ID"),
    update_data: StatisticsUpdate = ...,
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 수정"""
    try:
        statistics = service.update_statistics(statistics_id, update_data)
        if not statistics:
            raise NotFoundException("statistics", statistics_id, f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
        
        data = StatisticsResponse(
            id=str(statistics.id),
            statistical_data=statistics.statistical_data,
            source_url=statistics.source_url,
            is_active=statistics.is_active,
            created_at=statistics.created_at,
            updated_at=statistics.updated_at
        )
        
        return success_response(
            data=data,
            message="통계가 성공적으로 수정되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 수정 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete(
    "/{statistics_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="통계 삭제",
    description="통계를 삭제(비활성화)합니다.",
    response_description="삭제 성공 메시지"
)
async def delete_statistics(
    statistics_id: str = Path(..., description="삭제할 통계 ID"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 삭제 (비활성화)"""
    try:
        success = service.delete_statistics(statistics_id)
        if not success:
            raise NotFoundException("statistics", statistics_id, f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
        
        return success_response(
            data={"statistics_id": statistics_id, "deleted": True},
            message="통계가 성공적으로 삭제되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {statistics_id}에 해당하는 통계를 찾을 수 없습니다")
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/recent",
    response_model=BaseResponse[List[StatisticsResponse]],
    summary="최근 통계 조회",
    description="최근에 등록된 통계 목록을 조회합니다."
)
async def get_recent_statistics(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 통계 수"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """최근 통계 조회"""
    try:
        statistics_list = service.get_recent_statistics(limit)
        
        response_data = [StatisticsResponse(
            id=str(s.id),
            statistical_data=s.statistical_data,
            source_url=s.source_url,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in statistics_list]
        
        return success_response(
            data=response_data,
            message=f"최근 {len(response_data)}개의 통계를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최근 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/year/{year}",
    response_model=BaseResponse[List[StatisticsResponse]],
    summary="연도별 통계 조회",
    description="특정 연도의 통계 목록을 조회합니다."
)
async def get_statistics_by_year(
    year: int = Path(..., description="조회할 연도", example=2024),
    service: StatisticsService = Depends(get_statistics_service)
):
    """연도별 통계 조회"""
    try:
        statistics_list = service.get_statistics_by_year(year)
        
        response_data = [StatisticsResponse(
            id=str(s.id),
            statistical_data=s.statistical_data,
            source_url=s.source_url,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in statistics_list]
        
        return success_response(
            data=response_data,
            message=f"{year}년도 {len(response_data)}개의 통계를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"연도별 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/overview",
    response_model=BaseResponse[StatisticsOverview],
    summary="통계 개요 조회",
    description="전체 통계에 대한 개요 정보를 조회합니다."
)
async def get_statistics_overview(
    service: StatisticsService = Depends(get_statistics_service)
):
    """통계 개요 조회"""
    try:
        overview = await service.get_statistics_overview()
        return success_response(
            data=overview,
            message="통계 개요 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 개요 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/aggregated-metrics",
    response_model=BaseResponse[AggregatedMetrics],
    summary="집계 지표 조회",
    description="통계 데이터의 집계 지표를 조회합니다."
)
async def get_aggregated_metrics(
    stat_type: Optional[str] = Query(None, description="통계 유형 필터"),
    year: Optional[int] = Query(None, description="연도 필터"),
    service: StatisticsService = Depends(get_statistics_service)
):
    """집계 지표 조회"""
    try:
        metrics = await service.get_aggregated_metrics(stat_type, year)
        return success_response(
            data=metrics,
            message="집계 지표 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"집계 지표 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/report/monthly/{year}/{month}",
    response_model=BaseResponse[MonthlyReport],
    summary="월별 리포트 생성",
    description="특정 연월의 상세 통계 리포트를 생성합니다."
)
async def generate_monthly_report(
    year: int = Path(..., description="연도", example=2024),
    month: int = Path(..., ge=1, le=12, description="월", example=3),
    service: StatisticsService = Depends(get_statistics_service)
):
    """월별 리포트 생성"""
    try:
        report = await service.generate_monthly_report(year, month)
        return success_response(
            data=report,
            message=f"{year}년 {month}월 리포트 생성 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"월별 리포트 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/report/yearly/{year}",
    response_model=BaseResponse[YearlyReport],
    summary="연별 리포트 생성",
    description="특정 연도의 상세 통계 리포트를 생성합니다."
)
async def generate_yearly_report(
    year: int = Path(..., description="연도", example=2024),
    service: StatisticsService = Depends(get_statistics_service)
):
    """연별 리포트 생성"""
    try:
        report = await service.generate_yearly_report(year)
        return success_response(
            data=report,
            message=f"{year}년도 리포트 생성 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"연별 리포트 생성 중 오류가 발생했습니다: {str(e)}"
        )