"""
Business Service implementation.

Provides business logic for business-related operations using Repository pattern.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Business, BusinessCreate, BusinessUpdate
from .repository import BusinessRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import BusinessItem
from ...shared.interfaces.base_service import BaseService
from ...shared.interfaces.domain_services import IBusinessService
from ...shared.schemas import PaginatedResponse, DataCollectionResult
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class BusinessService(BaseService[Business, BusinessCreate, BusinessUpdate, BusinessItem]):
    """사업정보 서비스"""
    
    def __init__(self, repository: BusinessRepository, api_client: Optional[KStartupAPIClient] = None):
        super().__init__(repository=repository, logger=logger)
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    # BaseService 추상 메소드 구현
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """ID로 사업정보 데이터 조회"""
        return await self.repository.get_by_id(item_id)
    
    async def _fetch_list(
        self, 
        page: int, 
        limit: int, 
        query_params: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int]:
        """페이지네이션된 사업정보 목록 조회"""
        filters = query_params.get("filters", {})
        sort_by = query_params.get("sort_by")
        sort_order = query_params.get("sort_order", "desc")
        
        offset = (page - 1) * limit
        return await self.repository.get_list(
            offset=offset,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def _save_new_item(self, domain_data: Business) -> Dict[str, Any]:
        """새 사업정보 저장"""
        return await self.repository.create(domain_data)
    
    async def _save_updated_item(self, item_id: str, domain_data: Business) -> Dict[str, Any]:
        """사업정보 업데이트"""
        return await self.repository.update(item_id, domain_data)
    
    async def _delete_item(self, item_id: str) -> bool:
        """사업정보 삭제"""
        return await self.repository.delete(item_id)
    
    async def _transform_to_response(self, raw_data: Dict[str, Any]) -> BusinessItem:
        """원본 데이터를 응답 모델로 변환"""
        return BusinessItem(**raw_data)
    
    async def _transform_to_domain(self, input_data) -> Business:
        """입력 데이터를 도메인 모델로 변환"""
        if isinstance(input_data, BusinessCreate):
            return Business(**input_data.model_dump())
        elif isinstance(input_data, BusinessUpdate):
            return Business(**input_data.model_dump(exclude_unset=True))
        else:
            return Business(**input_data)
    
    # 도메인별 특화 메소드들
    async def fetch_businesses_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 사업정보 데이터 수집"""
        start_time = datetime.utcnow()
        result = DataCollectionResult(
            total_fetched=0,
            new_items=0,
            updated_items=0,
            skipped_items=0,
            errors=[],
            collection_time=0.0
        )
        
        try:
            # API 호출 로직 (기존 fetch_and_save_businesses 로직을 async로 변환)
            businesses = self.fetch_and_save_businesses(page_no, num_of_rows)
            result.total_fetched = len(businesses)
            result.new_items = len(businesses)
            
        except Exception as e:
            result.errors.append(str(e))
            self._log_error(f"사업정보 데이터 수집 실패: {e}")
        
        end_time = datetime.utcnow()
        result.collection_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def get_businesses_by_category(
        self,
        category: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """사업 카테고리별 목록 조회"""
        filters = {"business_category": category}
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_businesses_by_organization(
        self,
        organization_name: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """주관기관별 사업정보 목록 조회"""
        filters = {"host_organization": organization_name}
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_business_statistics(self) -> Dict[str, Any]:
        """사업정보 통계 조회"""
        total_count = await self.repository.count()
        # 추가 통계 계산 로직
        return {
            "total_businesses": total_count,
            "categories": {}  # 카테고리별 통계 등
        }
    
    async def search_businesses(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """사업정보 텍스트 검색"""
        filters = {
            "$or": [
                {"business_name": {"$regex": query, "$options": "i"}},
                {"host_organization": {"$regex": query, "$options": "i"}}
            ]
        }
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def fetch_and_save_businesses(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_field: Optional[str] = None,
        organization: Optional[str] = None,
        order_by_latest: bool = True
    ) -> List[Business]:
        """공공데이터에서 사업정보를 가져와 저장 (최신순 지원)"""
        businesses = []
        response = None
        
        try:
            # 최신순 조회를 위한 로직
            if order_by_latest:
                # 현재 연도부터 역순으로 조회
                current_year = datetime.now().year
                years_to_try = [str(current_year), str(current_year - 1), None]  # None은 전체 조회
                
                for business_year in years_to_try:
                    logger.info(f"사업연도 {business_year or '전체'}로 조회 시도 중...")
                    
                    response = await self.api_client.async_get_business_information(
                        page_no=page_no,
                        num_of_rows=num_of_rows,
                        business_field=business_field,
                        organization=organization
                    )
                    
                    if response.success and response.data.data:
                        logger.info(f"사업연도 {business_year or '전체'}에서 {len(response.data.data)}건 조회됨")
                        break
                    
                    if not response.success:
                        logger.warning(f"사업연도 {business_year or '전체'} 조회 실패: {response.error}")
            else:
                # 기존 방식 (연도 필터 없이 조회)
                response = await self.api_client.async_get_business_information(
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
                    # BusinessItem 객체에서 실제 데이터 추출
                    business_data = self._transform_businessitem_to_data(item)
                    
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
    
    def _transform_businessitem_to_data(self, business_item: BusinessItem) -> dict:
        """BusinessItem 객체를 내부 데이터 형식으로 변환 (실제 사용 가능한 필드만 매핑)"""
        return {
            # 기본 정보 (실제 사용 가능한 필드들)
            "business_id": business_item.id,
            "business_name": business_item.business_name,
            "business_type": business_item.business_category,
            "organization": business_item.host_organization,
            "business_field": business_item.business_category,
            "description": business_item.business_intro,
            "target_startup_stage": business_item.support_target,
            "support_scale": business_item.support_budget,
            "support_period": business_item.business_year,
            "eligibility": business_item.support_target,
            "selection_method": business_item.selection_method,
            "benefits": business_item.support_content.split(',') if business_item.support_content else [],
            "website_url": business_item.detail_page_url,
            "business_feature": business_item.business_feature,
            
            # 지원 관련 정보 (실제 사용 가능한 필드들)
            "support_content": business_item.support_content,
            "supervising_institution": business_item.supervising_institution,
            "application_period": business_item.application_period,
            "selection_criteria": business_item.selection_criteria,
            
            # 연락처 정보 (실제 사용 가능한 필드들)
            "contact_department": business_item.contact_department,
            "contact_phone": business_item.contact_phone,
            "contact_email": business_item.contact_email,
            
            # 메타데이터 (실제 사용 가능한 필드들)
            "created_date": business_item.created_date,
            "updated_date": business_item.updated_date
        }
    
    def get_businesses(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True,
        order_by_latest: bool = True
    ) -> PaginationResult[Business]:
        """저장된 사업정보 목록 조회 (페이지네이션, 기본 최신순)"""
        try:
            # 기본 필터 설정
            filters = QueryFilter()
            if is_active:
                filters.eq("is_active", True)
            else:
                filters.eq("is_active", False)
            
            # 최신순 정렬 설정 (기본값)
            from ...core.interfaces.base_repository import SortOption
            sort = SortOption().desc("created_at") if order_by_latest else None
            
            return self.repository.get_paginated(
                page=page, 
                page_size=page_size, 
                filters=filters,
                sort=sort
            )
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