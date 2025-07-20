from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from .service import AnnouncementService
from .models import AnnouncementResponse, AnnouncementCreate, AnnouncementUpdate
from ...shared.schemas import APIResponse, ErrorResponse, DataCollectionResult, PaginatedResponse

router = APIRouter(
    prefix="/announcements",
    tags=["사업공고"],
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        404: {"model": ErrorResponse, "description": "리소스를 찾을 수 없음"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"}
    }
)


def get_announcement_service() -> AnnouncementService:
    return AnnouncementService()


@router.post(
    "/fetch",
    response_model=List[AnnouncementResponse],
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
    """,
    response_description="성공적으로 수집된 사업공고 목록"
)
def fetch_announcements(
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
        announcements = service.fetch_and_save_announcements(
            page_no=page_no,
            num_of_rows=num_of_rows,
            business_name=business_name,
            business_type=business_type
        )
        return [AnnouncementResponse(
            id=str(a.id),
            announcement_data=a.announcement_data,
            source_url=a.source_url,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at
        ) for a in announcements]
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[AnnouncementResponse],
    status_code=status.HTTP_200_OK,
    summary="사업공고 목록 조회",
    description="""
    저장된 사업공고 목록을 페이지네이션과 함께 조회합니다.
    
    **주요 기능:**
    - 페이지네이션 지원 (skip/limit)
    - 활성/비활성 상태 필터링
    - 최신 데이터 우선 정렬
    
    **사용 시나리오:**
    - 웹사이트 메인 페이지 공고 목록
    - 관리자 페이지 데이터 관리
    - 모바일 앱 목록 화면
    """,
    response_description="사업공고 목록"
)
def get_announcements(
    skip: int = Query(
        0, 
        ge=0, 
        description="건너뛸 데이터 수 (페이지네이션용)",
        example=0
    ),
    limit: int = Query(
        20, 
        ge=1, 
        le=100, 
        description="조회할 데이터 수 (최대 100개)",
        example=20
    ),
    is_active: bool = Query(
        True, 
        description="활성 상태 필터 (True: 활성, False: 비활성)",
        example=True
    ),
    service: AnnouncementService = Depends(get_announcement_service)
):
    """
    저장된 사업공고 목록을 조회합니다.
    
    페이지네이션을 지원하며, 활성 상태에 따른 필터링이 가능합니다.
    """
    announcements = service.get_announcements(skip=skip, limit=limit, is_active=is_active)
    return [AnnouncementResponse(
        id=str(a.id),
        announcement_data=a.announcement_data,
        source_url=a.source_url,
        is_active=a.is_active,
        created_at=a.created_at,
        updated_at=a.updated_at
    ) for a in announcements]


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_200_OK,
    summary="특정 사업공고 상세 조회",
    description="""
    MongoDB ObjectId를 사용하여 특정 사업공고의 상세 정보를 조회합니다.
    
    **주요 기능:**
    - 고유 ID로 정확한 데이터 조회
    - 전체 공고 상세 정보 반환
    - 404 에러 자동 처리
    
    **사용 시나리오:**
    - 공고 상세 페이지 조회
    - 특정 공고 정보 확인
    - 관리 시스템에서 개별 데이터 조회
    """,
    response_description="사업공고 상세 정보",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "해당 ID의 사업공고를 찾을 수 없음"
        }
    }
)
def get_announcement(
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
    announcement = service.get_announcement_by_id(announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=404, 
            detail="해당 ID의 사업공고를 찾을 수 없습니다"
        )
    
    return AnnouncementResponse(
        id=str(announcement.id),
        announcement_data=announcement.announcement_data,
        source_url=announcement.source_url,
        is_active=announcement.is_active,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at
    )


@router.post("/", response_model=AnnouncementResponse)
def create_announcement(
    announcement_data: AnnouncementCreate,
    service: AnnouncementService = Depends(get_announcement_service)
):
    """새 사업공고 생성"""
    announcement = service.create_announcement(announcement_data)
    return AnnouncementResponse(
        id=str(announcement.id),
        announcement_data=announcement.announcement_data,
        source_url=announcement.source_url,
        is_active=announcement.is_active,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at
    )


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: str,
    update_data: AnnouncementUpdate,
    service: AnnouncementService = Depends(get_announcement_service)
):
    """사업공고 수정"""
    announcement = service.update_announcement(announcement_id, update_data)
    if not announcement:
        raise HTTPException(status_code=404, detail="사업공고를 찾을 수 없습니다")
    
    return AnnouncementResponse(
        id=str(announcement.id),
        announcement_data=announcement.announcement_data,
        source_url=announcement.source_url,
        is_active=announcement.is_active,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at
    )


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    service: AnnouncementService = Depends(get_announcement_service)
):
    """사업공고 삭제 (비활성화)"""
    success = service.delete_announcement(announcement_id)
    if not success:
        raise HTTPException(status_code=404, detail="사업공고를 찾을 수 없습니다")
    
    return {"message": "사업공고가 삭제되었습니다"}