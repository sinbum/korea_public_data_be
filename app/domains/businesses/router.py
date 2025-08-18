"""
기업정보 라우터 구현.

표준화된 응답, 페이지네이션, 에러 처리를 포함한 
기업 관련 작업을 위한 완전한 RESTful API 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, BackgroundTasks
from typing import List, Optional
from .service import BusinessService
from .batch_service import BusinessBatchService
from .schemas import (
    BusinessResponse,
    BusinessCreate,
    BusinessUpdate,
    BusinessStats
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
from ...core.dependencies import get_business_service, get_business_batch_service

router = APIRouter(
    prefix="/businesses",
    tags=["사업정보"],
    responses={
        400: {"description": "잘못된 요청"},
        404: {"description": "리소스를 찾을 수 없음"}, 
        422: {"description": "입력 데이터 검증 오류"},
        500: {"description": "서버 내부 오류"}
    }
)


@router.post(
    "/fetch",
    response_model=BaseResponse[List[BusinessResponse]],
    status_code=status.HTTP_200_OK,
    summary="K-Startup에서 사업정보 수집",
    description="""
    K-Startup API에서 사업정보 데이터를 가져와 데이터베이스에 저장합니다.
    
    **주요 기능:**
    - 공공데이터 API 실시간 호출
    - 중복 데이터 자동 감지 및 스킵
    - 새로운 데이터만 저장
    - 다양한 필터 조건 지원
    
    **사용 시나리오:**
    - 정기적인 데이터 동기화
    - 특정 사업분야의 사업정보만 수집
    - 신규 사업정보 즉시 확인
    """,
    response_description="성공적으로 수집된 사업정보 목록"
)
async def fetch_businesses(
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
    business_field: Optional[str] = Query(
        None, 
        description="사업분야로 필터링",
        example="인공지능"
    ),
    organization: Optional[str] = Query(
        None, 
        description="주관기관으로 필터링",
        example="중소벤처기업부"
    ),
    order_by_latest: bool = Query(
        True,
        description="최신순으로 데이터 조회 (최신 사업연도부터 조회)",
        example=True
    ),
    service: BusinessService = Depends(get_business_service)
):
    """
    K-Startup API에서 사업정보를 실시간으로 가져와 저장
    
    중복된 데이터는 자동으로 스킵되며, 새로운 데이터만 데이터베이스에 저장됩니다.
    """
    try:
        businesses = await service.fetch_and_save_businesses(
            page_no=page_no,
            num_of_rows=num_of_rows,
            business_field=business_field,
            organization=organization,
            order_by_latest=order_by_latest
        )
        
        response_data = []
        for b in businesses:
            # Ensure business_data is properly serialized
            if hasattr(b.business_data, 'model_dump'):
                business_data_dict = b.business_data.model_dump(mode='json')
            elif isinstance(b.business_data, dict):
                business_data_dict = b.business_data
            else:
                # Convert to dict if it's some other type
                business_data_dict = dict(b.business_data) if b.business_data else {}
            
            # Create plain dictionary instead of Pydantic model
            response_item = {
                "id": str(b.id),
                "business_data": business_data_dict,
                "source_url": b.source_url,
                "is_active": b.is_active,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None
            }
            response_data.append(response_item)
        
        return success_response(
            data=response_data,
            message=f"총 {len(response_data)}개의 사업정보가 성공적으로 수집되었습니다"
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
    "/recent",
    response_model=BaseResponse[List[BusinessResponse]],
    summary="최근 사업정보 조회",
    description="최근에 등록된 사업정보 목록을 조회합니다."
)
async def get_recent_businesses(
    limit: int = Query(10, ge=1, le=50, description="조회할 최근 사업정보 수"),
    service: BusinessService = Depends(get_business_service)
):
    """최근 사업정보 조회"""
    try:
        businesses = service.get_recent_businesses(limit)
        
        response_data = []
        for b in businesses:
            # Ensure business_data is properly serialized
            if hasattr(b.business_data, 'model_dump'):
                business_data_dict = b.business_data.model_dump(mode='json')
            elif isinstance(b.business_data, dict):
                business_data_dict = b.business_data
            else:
                # Convert to dict if it's some other type
                business_data_dict = dict(b.business_data) if b.business_data else {}
            
            # Create plain dictionary instead of Pydantic model
            response_item = {
                "id": str(b.id),
                "business_data": business_data_dict,
                "source_url": b.source_url,
                "is_active": b.is_active,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None
            }
            response_data.append(response_item)
        
        return success_response(
            data=response_data,
            message=f"최근 {len(response_data)}개의 사업정보를 조회했습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최근 사업정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=BaseResponse[BusinessStats],
    summary="사업정보 통계 조회",
    description="사업정보에 대한 통계 정보를 조회합니다."
)
async def get_business_statistics(
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 통계 조회"""
    try:
        stats = service.get_business_statistics()
        return success_response(
            data=stats,
            message="사업정보 통계 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=PaginatedResponse[BusinessResponse],
    summary="사업정보 목록 조회",
    description="""
    저장된 사업정보 목록을 페이지네이션과 함께 조회합니다.
    
    **주요 기능:**
    - 표준 페이지네이션 지원 (page, size, sort, order)
    - 다양한 필터링 옵션 (검색, 사업분야, 주관기관, 창업단계)
    - 정렬 옵션 지원
    
    **사용 시나리오:**
    - 웹사이트 메인 페이지 사업정보 목록
    - 관리자 페이지 데이터 관리
    - 모바일 앱 목록 화면
    """,
    response_description="페이지네이션된 사업정보 목록"
)
async def get_businesses(
    pagination: PaginationParams = Depends(),
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    business_field: Optional[str] = Query(None, description="사업분야 필터"),
    organization: Optional[str] = Query(None, description="주관기관 필터"),
    startup_stage: Optional[str] = Query(None, description="창업단계 필터"),
    is_active: Optional[bool] = Query(None, description="활성 상태 필터"),
    order_by_latest: bool = Query(True, description="최신순 정렬 (기본값: True)"),
    service: BusinessService = Depends(get_business_service)
):
    """
    저장된 사업정보 목록을 조회합니다.
    
    표준 페이지네이션과 필터링을 지원합니다.
    """
    try:
        # 필터 조건 구성
        filters = {
            "keyword": keyword,
            "business_field": business_field,
            "organization": organization,
            "startup_stage": startup_stage,
            "is_active": is_active
        }
        # None 값 제거
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Use the simpler get_businesses method for now
        result = service.get_businesses(
            page=pagination.page,
            page_size=pagination.size,
            is_active=is_active if is_active is not None else True,
            order_by_latest=order_by_latest
        )
        
        items = []
        for b in result.items:
            # Ensure business_data is properly serialized
            if hasattr(b.business_data, 'model_dump'):
                business_data_dict = b.business_data.model_dump(mode='json')
            elif isinstance(b.business_data, dict):
                business_data_dict = b.business_data
            else:
                # Convert to dict if it's some other type
                business_data_dict = dict(b.business_data) if b.business_data else {}
            
            # Create plain dictionary instead of Pydantic model
            item = {
                "id": str(b.id),
                "business_data": business_data_dict,
                "source_url": b.source_url,
                "is_active": b.is_active,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None
            }
            items.append(item)
        
        return PaginatedResponse(
            success=True,
            items=items,
            message="사업정보 목록 조회 성공",
            pagination=result.to_pagination_meta()
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업정보 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/{business_id}",
    response_model=BaseResponse[BusinessResponse],
    summary="특정 사업정보 상세 조회",
    description="""
    MongoDB ObjectId를 사용하여 특정 사업정보의 상세 정보를 조회합니다.
    
    **주요 기능:**
    - 고유 ID로 정확한 데이터 조회
    - 전체 사업정보 상세 정보 반환
    - 표준 에러 응답 포맷
    
    **사용 시나리오:**
    - 사업정보 상세 페이지 조회
    - 특정 사업정보 확인
    - 관리 시스템에서 개별 데이터 조회
    """,
    response_description="사업정보 상세 정보"
)
async def get_business(
    business_id: str = Path(
        ...,
        description="조회할 사업정보의 고유 ID (MongoDB ObjectId)",
        example="65f1a2b3c4d5e6f7a8b9c0d1"
    ),
    service: BusinessService = Depends(get_business_service)
):
    """
    특정 사업정보의 상세 정보를 조회합니다.
    
    MongoDB ObjectId를 사용하여 정확한 데이터를 반환합니다.
    """
    try:
        business = service.get_business_by_id(business_id)
        if not business:
            raise NotFoundException("business", business_id, f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
        
        # Ensure business_data is properly serialized
        if hasattr(business.business_data, 'model_dump'):
            business_data_dict = business.business_data.model_dump(mode='json')
        elif isinstance(business.business_data, dict):
            business_data_dict = business.business_data
        else:
            # Convert to dict if it's some other type
            business_data_dict = dict(business.business_data) if business.business_data else {}
        
        # Create plain dictionary instead of Pydantic model
        data = {
            "id": str(business.id),
            "business_data": business_data_dict,
            "source_url": business.source_url,
            "is_active": business.is_active,
            "created_at": business.created_at.isoformat() if business.created_at else None,
            "updated_at": business.updated_at.isoformat() if business.updated_at else None
        }
        
        return success_response(
            data=data,
            message="사업정보 상세 정보 조회 성공"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/",
    response_model=CreatedResponse[BusinessResponse],
    status_code=status.HTTP_201_CREATED,
    summary="새 사업정보 생성",
    description="새로운 사업정보를 생성합니다.",
    response_description="생성된 사업정보 정보"
)
async def create_business(
    business_data: BusinessCreate,
    service: BusinessService = Depends(get_business_service)
):
    """새 사업정보 생성"""
    try:
        business = service.create_business(business_data)
        
        # Ensure business_data is properly serialized
        if hasattr(business.business_data, 'model_dump'):
            business_data_dict = business.business_data.model_dump(mode='json')
        elif isinstance(business.business_data, dict):
            business_data_dict = business.business_data
        else:
            # Convert to dict if it's some other type
            business_data_dict = dict(business.business_data) if business.business_data else {}
        
        # Create plain dictionary instead of Pydantic model
        data = {
            "id": str(business.id),
            "business_data": business_data_dict,
            "source_url": business.source_url,
            "is_active": business.is_active,
            "created_at": business.created_at.isoformat() if business.created_at else None,
            "updated_at": business.updated_at.isoformat() if business.updated_at else None
        }
        
        return CreatedResponse(
            success=True,
            data=data,
            message="사업정보가 성공적으로 생성되었습니다",
            resource_id=str(business.id)
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업정보 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.put(
    "/{business_id}",
    response_model=BaseResponse[BusinessResponse],
    summary="사업정보 수정",
    description="기존 사업정보를 수정합니다.",
    response_description="수정된 사업정보 정보"
)
async def update_business(
    business_id: str = Path(..., description="수정할 사업정보 ID"),
    update_data: BusinessUpdate = ...,
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 수정"""
    try:
        business = service.update_business(business_id, update_data)
        if not business:
            raise NotFoundException("business", business_id, f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
        
        # Ensure business_data is properly serialized
        if hasattr(business.business_data, 'model_dump'):
            business_data_dict = business.business_data.model_dump(mode='json')
        elif isinstance(business.business_data, dict):
            business_data_dict = business.business_data
        else:
            # Convert to dict if it's some other type
            business_data_dict = dict(business.business_data) if business.business_data else {}
        
        # Create plain dictionary instead of Pydantic model
        data = {
            "id": str(business.id),
            "business_data": business_data_dict,
            "source_url": business.source_url,
            "is_active": business.is_active,
            "created_at": business.created_at.isoformat() if business.created_at else None,
            "updated_at": business.updated_at.isoformat() if business.updated_at else None
        }
        
        return success_response(
            data=data,
            message="사업정보가 성공적으로 수정되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업정보 수정 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete(
    "/{business_id}",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="사업정보 삭제",
    description="사업정보를 삭제(비활성화)합니다.",
    response_description="삭제 성공 메시지"
)
async def delete_business(
    business_id: str = Path(..., description="삭제할 사업정보 ID"),
    service: BusinessService = Depends(get_business_service)
):
    """사업정보 삭제 (비활성화)"""
    try:
        success = service.delete_business(business_id)
        if not success:
            raise NotFoundException("business", business_id, f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
        
        return success_response(
            data={"business_id": business_id, "deleted": True},
            message="사업정보가 성공적으로 삭제되었습니다"
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"ID {business_id}에 해당하는 사업정보를 찾을 수 없습니다")
    except BusinessLogicException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"사업정보 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/batch-collect",
    response_model=BaseResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    summary="사업정보 대량 수집",
    description="""
    K-Startup API에서 모든 사업정보 데이터를 대량으로 수집합니다.
    
    **주요 기능:**
    - 최대 1,231개의 사업정보 데이터 수집 가능
    - 비동기 배치 처리로 높은 성능
    - 진행률 추적 및 모니터링
    - 중복 데이터 자동 감지 및 스킵
    - 벌크 삽입으로 최적화된 성능
    - 에러 발생 시 개별 삽입 폴백
    
    **처리 방식:**
    - 동시 요청 수: 최대 5개
    - 페이지당 처리량: 100개 항목
    - 청크 단위 처리: 15페이지씩 배치
    - 메모리 최적화된 중간 규모 처리
    
    **예상 소요 시간:**
    - 전체 데이터: 약 3-8분
    - 500개 항목: 약 1-3분
    
    **참고사항:**
    - 백그라운드에서 실행되며 즉시 응답 반환
    - 진행 상황은 로그를 통해 모니터링 가능
    """,
    response_description="배치 수집 작업 시작 확인 메시지",
    responses={
        202: {
            "model": BaseResponse[dict],
            "description": "배치 수집 작업이 성공적으로 시작됨",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "success",
                        "data": {
                            "task_id": "business_batch_collect_20250814_123456",
                            "estimated_total": 1231,
                            "max_pages": 13,
                            "batch_size": 100,
                            "status": "started"
                        },
                        "message": "사업정보 대량 수집 작업이 시작되었습니다",
                        "timestamp": "2025-08-14T12:34:56Z"
                    }
                }
            }
        }
    }
)
async def batch_collect_businesses(
    background_tasks: BackgroundTasks,
    max_pages: Optional[int] = Query(
        None,
        ge=1,
        le=50,
        description="수집할 최대 페이지 수 (None이면 모든 데이터, 테스트용도로 제한 가능)",
        example=5
    ),
    business_type: Optional[str] = Query(
        None,
        description="사업 유형으로 필터링",
        example="정부지원사업"
    ),
    organization: Optional[str] = Query(
        None,
        description="주관기관으로 필터링",
        example="창업진흥원"
    ),
    batch_service: BusinessBatchService = Depends(get_business_batch_service)
):
    """
    사업정보 대량 수집 배치 작업 시작
    
    백그라운드에서 비동기로 대량 데이터 수집을 실행합니다.
    """
    try:
        from datetime import datetime
        import uuid
        
        # 작업 ID 생성
        task_id = f"business_batch_collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 예상 총량 계산
        estimated_total = 1231
        if max_pages:
            estimated_total = min(estimated_total, max_pages * 100)
        
        # 백그라운드 작업 시작
        async def batch_collection_task():
            """배치 수집 백그라운드 작업"""
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"사업정보 배치 수집 작업 시작: {task_id}")
                
                result = await batch_service.collect_all_businesses(
                    max_pages=max_pages,
                    business_type=business_type,
                    organization=organization
                )
                
                logger.info(f"사업정보 배치 수집 작업 완료: {task_id} - {result}")
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"사업정보 배치 수집 작업 오류: {task_id} - {e}")
        
        # 백그라운드 태스크 추가
        background_tasks.add_task(batch_collection_task)
        
        return success_response(
            data={
                "task_id": task_id,
                "estimated_total": estimated_total,
                "max_pages": max_pages or "unlimited",
                "batch_size": 100,
                "status": "started",
                "filters": {
                    "business_type": business_type,
                    "organization": organization
                }
            },
            message="사업정보 대량 수집 작업이 백그라운드에서 시작되었습니다"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"배치 수집 작업 시작 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/batch-statistics",
    response_model=BaseResponse[dict],
    summary="수집 통계 조회",
    description="현재 데이터베이스에 저장된 사업정보 수집 통계를 조회합니다.",
)
async def get_batch_collection_statistics(
    batch_service: BusinessBatchService = Depends(get_business_batch_service)
):
    """배치 수집 통계 조회"""
    try:
        stats = await batch_service.get_collection_statistics()
        return success_response(
            data=stats,
            message="수집 통계 조회 성공"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )