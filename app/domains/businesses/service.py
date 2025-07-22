"""
Business Service implementation.

Provides business logic for business-related operations using Repository pattern.
"""

from typing import List, Optional
from .models import Business, BusinessCreate, BusinessUpdate
from .repository import BusinessRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class BusinessService:
    """사업정보 서비스"""
    
    def __init__(self, repository: BusinessRepository):
        self.repository = repository
    
    def fetch_and_save_businesses(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_field: Optional[str] = None,
        organization: Optional[str] = None
    ) -> List[Business]:
        """공공데이터에서 사업정보를 가져와 저장"""
        businesses = []
        
        try:
            # K-Startup API 호출
            with KStartupAPIClient() as client:
                response = client.get_business_information(
                    page_no=page_no,
                    num_of_rows=num_of_rows,
                    business_field=business_field,
                    organization=organization
                )
                
                if not response.success:
                    logger.error(f"API 호출 실패: {response.error}")
                    return businesses
                
                logger.info(f"API 응답: {len(response.data.data)}건 조회")
                
                # 응답 데이터 처리
                for item in response.data.data:
                    try:
                        # 공공데이터 응답을 우리 모델에 맞게 변환
                        business_data = self._transform_api_data(item.dict())
                        
                        # 중복 체크
                        business_id = business_data.get("business_id")
                        business_name = business_data.get("business_name")
                        
                        is_duplicate = self.repository.check_duplicate(
                            business_id=business_id,
                            business_name=business_name
                        )
                        
                        if is_duplicate:
                            logger.info(f"중복 데이터 스킵: {business_name}")
                            continue
                        
                        # 새 사업정보 생성
                        business_create = BusinessCreate(
                            business_data=business_data,
                            source_url=f"K-Startup-사업정보-{business_id or 'unknown'}"
                        )
                        
                        # Repository를 통해 저장
                        business = self.repository.create(business_create)
                        businesses.append(business)
                        
                        logger.info(f"새로운 사업정보 저장: {business_name}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"K-Startup API 호출 실패: {e}")
            
        return businesses
    
    def _transform_api_data(self, api_item: dict) -> dict:
        """K-Startup API 응답을 내부 모델로 변환"""
        return {
            "business_id": api_item.get("business_id"),
            "business_name": api_item.get("business_name"),
            "business_type": api_item.get("business_type"),
            "organization": api_item.get("organization"),
            "business_field": api_item.get("business_field"),
            "description": api_item.get("description"),
            "target_startup_stage": api_item.get("target_startup_stage"),
            "support_scale": api_item.get("support_scale"),
            "support_period": api_item.get("support_period"),
            "eligibility": api_item.get("eligibility"),
            "selection_method": api_item.get("selection_method"),
            "benefits": api_item.get("benefits", []),
            "website_url": api_item.get("website_url"),
            "contact_department": api_item.get("contact_department"),
            "contact_phone": api_item.get("contact_phone"),
            "contact_email": api_item.get("contact_email")
        }
    
    def get_businesses(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True
    ) -> PaginationResult[Business]:
        """저장된 사업정보 목록 조회 (페이지네이션)"""
        try:
            if is_active:
                return self.repository.find_active_businesses(page=page, page_size=page_size)
            else:
                filters = QueryFilter().eq("is_active", False)
                return self.repository.get_paginated(page=page, page_size=page_size, filters=filters)
        except Exception as e:
            logger.error(f"사업정보 목록 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_business_by_id(self, business_id: str) -> Optional[Business]:
        """ID로 사업정보 조회"""
        try:
            return self.repository.get_by_id(business_id)
        except Exception as e:
            logger.error(f"사업정보 조회 오류: {e}")
            return None
    
    def create_business(self, business_data: BusinessCreate) -> Business:
        """새 사업정보 생성"""
        try:
            return self.repository.create(business_data)
        except Exception as e:
            logger.error(f"사업정보 생성 오류: {e}")
            raise
    
    def update_business(
        self, 
        business_id: str, 
        update_data: BusinessUpdate
    ) -> Optional[Business]:
        """사업정보 수정"""
        try:
            return self.repository.update_by_id(business_id, update_data)
        except Exception as e:
            logger.error(f"사업정보 수정 오류: {e}")
            return None
    
    def delete_business(self, business_id: str) -> bool:
        """사업정보 삭제 (비활성화)"""
        try:
            return self.repository.delete_by_id(business_id, soft_delete=True)
        except Exception as e:
            logger.error(f"사업정보 삭제 오류: {e}")
            return False
    
    # 추가 비즈니스 로직 메서드들
    def search_businesses(self, search_term: str) -> List[Business]:
        """사업정보 검색"""
        try:
            return self.repository.search_businesses(search_term)
        except Exception as e:
            logger.error(f"사업정보 검색 오류: {e}")
            return []
    
    def get_businesses_by_type(self, business_type: str) -> List[Business]:
        """사업 유형별 사업정보 조회"""
        try:
            return self.repository.find_by_business_type(business_type)
        except Exception as e:
            logger.error(f"유형별 사업정보 조회 오류: {e}")
            return []
    
    def get_businesses_by_organization(self, organization: str) -> List[Business]:
        """주관기관별 사업정보 조회"""
        try:
            return self.repository.find_by_organization(organization)
        except Exception as e:
            logger.error(f"주관기관별 사업정보 조회 오류: {e}")
            return []
    
    def get_businesses_by_field(self, business_field: str) -> List[Business]:
        """사업분야별 사업정보 조회"""
        try:
            return self.repository.find_by_business_field(business_field)
        except Exception as e:
            logger.error(f"사업분야별 사업정보 조회 오류: {e}")
            return []
    
    def get_businesses_by_startup_stage(self, startup_stage: str) -> List[Business]:
        """창업단계별 사업정보 조회"""
        try:
            return self.repository.find_by_startup_stage(startup_stage)
        except Exception as e:
            logger.error(f"창업단계별 사업정보 조회 오류: {e}")
            return []
    
    def get_recent_businesses(self, limit: int = 10) -> List[Business]:
        """최근 사업정보 조회"""
        try:
            return self.repository.get_recent_businesses(limit)
        except Exception as e:
            logger.error(f"최근 사업정보 조회 오류: {e}")
            return []
    
    def get_businesses_with_filter(
        self,
        business_type: Optional[str] = None,
        organization: Optional[str] = None,
        business_field: Optional[str] = None,
        startup_stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginationResult[Business]:
        """필터 조건에 따른 사업정보 조회"""
        try:
            return self.repository.get_businesses_by_filter(
                business_type=business_type,
                organization=organization,
                business_field=business_field,
                startup_stage=startup_stage,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            logger.error(f"필터 조건별 사업정보 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_business_statistics(self) -> dict:
        """사업정보 통계 조회"""
        try:
            return self.repository.get_statistics()
        except Exception as e:
            logger.error(f"사업정보 통계 조회 오류: {e}")
            return {}
    
    def bulk_create_businesses(self, businesses: List[BusinessCreate]) -> List[Business]:
        """대량 사업정보 생성"""
        try:
            return self.repository.bulk_create_businesses(businesses)
        except Exception as e:
            logger.error(f"대량 사업정보 생성 오류: {e}")
            return []