from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
import logging

from .service import DataSourceService
from ...shared.models.data_source import (
    DataSourceConfig,
    DataCollectionRequest,
    DataCollectionResponse
)
from ...shared.models.base import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/data-sources",
    tags=["동적 데이터 소스 관리"],
    responses={
        404: {"description": "데이터 소스를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)


def get_data_source_service() -> DataSourceService:
    """데이터 소스 서비스 의존성"""
    return DataSourceService()


@router.post(
    "/",
    response_model=DataSourceConfig,
    summary="새 데이터 소스 등록",
    description="새로운 공공데이터 API 소스를 등록합니다."
)
def create_data_source(
    config: DataSourceConfig,
    service: DataSourceService = Depends(get_data_source_service)
):
    """새 데이터 소스 등록"""
    try:
        return service.create_data_source(config)
    except Exception as e:
        logger.error(f"데이터 소스 등록 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 등록에 실패했습니다.")


@router.get(
    "/",
    response_model=List[DataSourceConfig],
    summary="데이터 소스 목록 조회",
    description="등록된 데이터 소스 목록을 조회합니다."
)
def get_data_sources(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(20, ge=1, le=100, description="조회할 항목 수"),
    is_active: bool = Query(True, description="활성 상태 필터"),
    service: DataSourceService = Depends(get_data_source_service)
):
    """데이터 소스 목록 조회"""
    try:
        return service.get_data_sources(skip=skip, limit=limit, is_active=is_active)
    except Exception as e:
        logger.error(f"데이터 소스 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 목록 조회에 실패했습니다.")


@router.get(
    "/{source_id}",
    response_model=DataSourceConfig,
    summary="데이터 소스 상세 조회",
    description="특정 데이터 소스의 상세 정보를 조회합니다."
)
def get_data_source(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service)
):
    """데이터 소스 상세 조회"""
    try:
        source = service.get_data_source_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="데이터 소스를 찾을 수 없습니다.")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터 소스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 조회에 실패했습니다.")


@router.put(
    "/{source_id}",
    response_model=DataSourceConfig,
    summary="데이터 소스 수정",
    description="기존 데이터 소스의 설정을 수정합니다."
)
def update_data_source(
    source_id: str,
    updates: Dict[str, Any],
    service: DataSourceService = Depends(get_data_source_service)
):
    """데이터 소스 수정"""
    try:
        source = service.update_data_source(source_id, updates)
        if not source:
            raise HTTPException(status_code=404, detail="데이터 소스를 찾을 수 없습니다.")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터 소스 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 수정에 실패했습니다.")


@router.delete(
    "/{source_id}",
    response_model=APIResponse,
    summary="데이터 소스 삭제",
    description="데이터 소스를 비활성화합니다."
)
def delete_data_source(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service)
):
    """데이터 소스 삭제"""
    try:
        success = service.delete_data_source(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="데이터 소스를 찾을 수 없습니다.")
        
        return APIResponse(
            success=True,
            message="데이터 소스가 성공적으로 삭제되었습니다."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터 소스 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 삭제에 실패했습니다.")


@router.post(
    "/collect",
    response_model=DataCollectionResponse,
    summary="동적 데이터 수집",
    description="지정된 데이터 소스에서 데이터를 수집합니다."
)
def collect_data(
    request: DataCollectionRequest,
    service: DataSourceService = Depends(get_data_source_service)
):
    """동적 데이터 수집"""
    try:
        return service.collect_data_from_source(request)
    except Exception as e:
        logger.error(f"데이터 수집 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 수집에 실패했습니다.")


@router.post(
    "/init-predefined",
    response_model=APIResponse,
    summary="기본 데이터 소스 초기화",
    description="미리 정의된 데이터 소스들을 등록합니다."
)
def initialize_predefined_sources(
    service: DataSourceService = Depends(get_data_source_service)
):
    """기본 데이터 소스 초기화"""
    try:
        service.create_predefined_sources()
        return APIResponse(
            success=True,
            message="기본 데이터 소스가 성공적으로 초기화되었습니다."
        )
    except Exception as e:
        logger.error(f"기본 데이터 소스 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail="기본 데이터 소스 초기화에 실패했습니다.")


@router.get(
    "/{source_id}/test",
    response_model=DataCollectionResponse,
    summary="데이터 소스 테스트",
    description="데이터 소스 설정을 테스트하고 샘플 데이터를 가져옵니다."
)
def test_data_source(
    source_id: str,
    limit: int = Query(3, ge=1, le=10, description="테스트할 데이터 수"),
    service: DataSourceService = Depends(get_data_source_service)
):
    """데이터 소스 테스트"""
    try:
        request = DataCollectionRequest(
            source_id=source_id,
            params={},
            limit=limit,
            save_to_db=False  # 테스트시에는 저장하지 않음
        )
        return service.collect_data_from_source(request)
    except Exception as e:
        logger.error(f"데이터 소스 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터 소스 테스트에 실패했습니다.")