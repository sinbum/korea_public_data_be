from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Announcement, AnnouncementCreate, AnnouncementUpdate
from .repository import AnnouncementRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import KStartupAnnouncementResponse, AnnouncementItem
from ...shared.interfaces.base_service import BaseService
from ...shared.interfaces.domain_services import IAnnouncementService
from ...shared.schemas import PaginatedResponse, DataCollectionResult
from ...shared.pagination import PaginationParams, FilterParams, PaginatedResult
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class AnnouncementService(BaseService[Announcement, AnnouncementCreate, AnnouncementUpdate, AnnouncementItem]):
    """사업공고 서비스"""
    
    def __init__(self, repository: AnnouncementRepository, api_client: Optional[KStartupAPIClient] = None):
        super().__init__(repository=repository, logger=logger)
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    async def fetch_and_save_announcements(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> List[Announcement]:
        """K-Startup API에서 사업공고 정보를 가져와 저장"""
        announcements = []
        all_processed_items = []  # 처리된 모든 아이템 (새로 저장 + 중복 스킵)
        
        try:
            # K-Startup API 호출 (새로운 클라이언트 사용)
            response = await self.api_client.async_get_announcement_information(
                page_no=page_no,
                num_of_rows=num_of_rows,
                business_name=business_name,
                business_type=business_type
            )
            
            logger.info(f"K-Startup API 응답: {response.total_count}건 중 {response.current_count}건 조회")
            
            # 응답 데이터 처리
            if response.data:
                # response.data가 리스트인지 확인, 아니면 data 필드에서 리스트 추출
                items_to_process = []
                if isinstance(response.data, list):
                    items_to_process = response.data
                elif hasattr(response.data, 'data') and isinstance(response.data.data, list):
                    items_to_process = response.data.data
                elif isinstance(response.data, dict) and 'data' in response.data:
                    items_to_process = response.data['data']
                else:
                    logger.warning(f"Unexpected response.data type: {type(response.data)}")
                    
                for item in items_to_process:
                    try:
                        # AnnouncementItem 객체인지 확인
                        if hasattr(item, 'announcement_id'):
                            # K-Startup 응답을 우리 모델에 맞게 변환
                            announcement_data = self._transform_kstartup_data(item)
                            
                            # 중복 체크
                            business_id = announcement_data.get("business_id")
                            business_name_val = announcement_data.get("business_name")
                            
                            # 중복 체크 수행
                            is_duplicate = self.repository.check_duplicate(
                                business_id=business_id,
                                business_name=business_name_val
                            )
                            
                            if is_duplicate:
                                logger.info(f"중복 데이터 스킵: {business_name_val}")
                                # 중복이어도 기존 데이터를 찾아서 반환 리스트에 추가
                                existing_announcement = self.repository.find_by_business_id(business_id)
                                if existing_announcement:
                                    all_processed_items.append(existing_announcement)
                                continue
                            
                            # 새 공고 생성
                            announcement_create = AnnouncementCreate(
                                announcement_data=announcement_data,
                                source_url=f"K-Startup-사업공고-{business_id or 'unknown'}"
                            )
                            
                            # Repository를 통해 저장
                            announcement = self.repository.create(announcement_create)
                            announcements.append(announcement)
                            all_processed_items.append(announcement)
                            
                            logger.info(f"새로운 사업공고 저장: {business_name_val}")
                        else:
                            logger.debug(f"AnnouncementItem이 아닌 데이터 스킵: {type(item)} - {item}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"K-Startup API 호출 실패: {e}")
            # API 호출 실패시 빈 리스트 반환
            
        # 새로 저장된 데이터와 기존 데이터 모두 반환
        return all_processed_items if all_processed_items else announcements
    
    # BaseService 추상 메소드 구현
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """ID로 공고 데이터 조회"""
        return await self.repository.get_by_id(item_id)
    
    async def _fetch_list(
        self, 
        page: int, 
        limit: int, 
        query_params: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int]:
        """페이지네이션된 공고 목록 조회"""
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
    
    async def _save_new_item(self, domain_data: Announcement) -> Dict[str, Any]:
        """새 공고 저장"""
        return await self.repository.create(domain_data)
    
    async def _save_updated_item(self, item_id: str, domain_data: Announcement) -> Dict[str, Any]:
        """공고 업데이트"""
        return await self.repository.update(item_id, domain_data)
    
    async def _delete_item(self, item_id: str) -> bool:
        """공고 삭제"""
        return await self.repository.delete(item_id)
    
    async def _transform_to_response(self, raw_data: Dict[str, Any]) -> AnnouncementItem:
        """원본 데이터를 응답 모델로 변환"""
        return AnnouncementItem(**raw_data)
    
    async def _transform_to_domain(self, input_data) -> Announcement:
        """입력 데이터를 도메인 모델로 변환"""
        if isinstance(input_data, AnnouncementCreate):
            return Announcement(**input_data.model_dump())
        elif isinstance(input_data, AnnouncementUpdate):
            return Announcement(**input_data.model_dump(exclude_unset=True))
        else:
            return Announcement(**input_data)
    
    # 도메인별 특화 메소드들
    async def fetch_announcements_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 공고 데이터 수집"""
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
            announcements = await self.fetch_and_save_announcements(page_no, num_of_rows)
            result.total_fetched = len(announcements)
            result.new_items = len(announcements)  # 실제로는 새로운 것만 카운트해야 함
            
        except Exception as e:
            result.errors.append(str(e))
            self._log_error(f"공고 데이터 수집 실패: {e}")
        
        end_time = datetime.utcnow()
        result.collection_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def get_active_announcements(
        self,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """활성 상태의 공고 목록 조회"""
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        filters = {
            "end_date": {"$gte": current_date}  # 종료일이 현재일 이후인 것
        }
        
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_announcements_by_category(
        self,
        category_code: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """카테고리별 공고 목록 조회"""
        filters = {"business_category_code": category_code}
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_announcements_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """날짜 범위별 공고 목록 조회"""
        filters = {
            "start_date": {"$gte": start_date.strftime("%Y-%m-%d")},
            "end_date": {"$lte": end_date.strftime("%Y-%m-%d")}
        }
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def search_announcements(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """공고 텍스트 검색"""
        filters = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"organization_name": {"$regex": query, "$options": "i"}}
            ]
        }
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    def _transform_kstartup_data(self, kstartup_item) -> dict:
        """K-Startup API 응답을 내부 모델로 변환"""
        # AnnouncementItem 모델의 실제 필드명 사용
        
        # 모집기간 설정
        recruitment_period = ""
        if kstartup_item.start_date and kstartup_item.end_date:
            recruitment_period = f"{kstartup_item.start_date} ~ {kstartup_item.end_date}"
        elif kstartup_item.start_date:
            recruitment_period = f"{kstartup_item.start_date} ~"
        elif kstartup_item.end_date:
            recruitment_period = f"~ {kstartup_item.end_date}"
        
        # 지원 대상 정보 구성
        support_target = ""
        if kstartup_item.application_target:
            support_target = kstartup_item.application_target
        elif kstartup_item.application_target_content:
            support_target = kstartup_item.application_target_content
        
        # 신청 방법 정보 구성
        application_method = ""
        if kstartup_item.online_reception:
            application_method = kstartup_item.online_reception
        elif kstartup_item.business_guidance_url:
            application_method = f"온라인 접수 - {kstartup_item.business_guidance_url}"
        else:
            application_method = "온라인 접수"
        
        # 날짜 변환 헬퍼 함수
        def convert_date_to_datetime(date_str):
            if date_str and isinstance(date_str, str):
                try:
                    from datetime import datetime
                    # YYYY-MM-DD 형식을 datetime으로 변환
                    if len(date_str) == 10 and '-' in date_str:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    pass
            return None
        
        return {
            "business_id": kstartup_item.announcement_id or str(kstartup_item.id) if kstartup_item.id else None,
            "business_name": kstartup_item.integrated_business_name or kstartup_item.title,
            "business_type": kstartup_item.business_category or "창업지원",
            "business_overview": kstartup_item.content or kstartup_item.integrated_business_name,
            "support_target": support_target,
            "recruitment_period": recruitment_period,
            "application_method": application_method,
            "contact_info": kstartup_item.organization or kstartup_item.contact_department,
            "announcement_date": convert_date_to_datetime(kstartup_item.start_date),
            "deadline": convert_date_to_datetime(kstartup_item.end_date),
            "status": "모집중" if kstartup_item.recruitment_progress == "Y" else "모집종료"
        }
    
    # 이전 레거시 메서드들은 향후 제거 예정 (K-Startup 클라이언트로 완전 마이그레이션 후)
    
    def get_announcements(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True
    ) -> PaginationResult[Announcement]:
        """저장된 사업공고 목록 조회 (페이지네이션)"""
        try:
            if is_active:
                return self.repository.find_active_announcements(page=page, page_size=page_size)
            else:
                filters = QueryFilter().eq("is_active", False)
                return self.repository.get_paginated(page=page, page_size=page_size, filters=filters)
        except Exception as e:
            logger.error(f"공고 목록 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_announcements_paginated(
        self, 
        pagination: PaginationParams, 
        filters: FilterParams
    ) -> PaginatedResult[Announcement]:
        """새로운 표준 페이지네이션을 사용한 공고 목록 조회"""
        try:
            # FilterParams를 MongoDB 필터로 변환
            mongo_filter = filters.to_mongo_filter()
            
            # 기본적으로 활성 상태 공고만 조회
            if "is_active" not in mongo_filter:
                mongo_filter["is_active"] = True
            
            # MongoDB 쿼리 수행
            collection = self.repository.collection
            
            # 총 개수 조회
            total = collection.count_documents(mongo_filter)
            
            # 페이지네이션된 결과 조회
            cursor = collection.find(mongo_filter)
            
            # 정렬 적용
            if pagination.sort:
                sort_spec = pagination.mongo_sort
                cursor = cursor.sort(sort_spec)
            
            # 페이지네이션 적용
            cursor = cursor.skip(pagination.skip).limit(pagination.limit)
            
            # 결과를 Announcement 객체로 변환
            items = []
            for doc in cursor:
                # MongoDB _id를 문자열 id로 변환
                if "_id" in doc:
                    doc["id"] = str(doc["_id"])
                    del doc["_id"]
                
                announcement = Announcement(**doc)
                items.append(announcement)
            
            return PaginatedResult(
                items=items,
                total=total,
                page=pagination.page,
                size=pagination.size
            )
            
        except Exception as e:
            logger.error(f"페이지네이션 공고 목록 조회 오류: {e}")
            # 빈 결과 반환
            return PaginatedResult(
                items=[],
                total=0,
                page=pagination.page,
                size=pagination.size
            )
    
    def get_announcement_by_id(self, announcement_id: str) -> Optional[Announcement]:
        """ID로 사업공고 조회"""
        try:
            return self.repository.get_by_id(announcement_id)
        except Exception as e:
            logger.error(f"공고 조회 오류: {e}")
            return None
    
    def create_announcement(self, announcement_data: AnnouncementCreate) -> Announcement:
        """새 사업공고 생성"""
        try:
            return self.repository.create(announcement_data)
        except Exception as e:
            logger.error(f"공고 생성 오류: {e}")
            raise
    
    def update_announcement(
        self, 
        announcement_id: str, 
        update_data: AnnouncementUpdate
    ) -> Optional[Announcement]:
        """사업공고 수정"""
        try:
            return self.repository.update_by_id(announcement_id, update_data)
        except Exception as e:
            logger.error(f"공고 수정 오류: {e}")
            return None
    
    def delete_announcement(self, announcement_id: str) -> bool:
        """사업공고 삭제 (비활성화)"""
        try:
            return self.repository.delete_by_id(announcement_id, soft_delete=True)
        except Exception as e:
            logger.error(f"공고 삭제 오류: {e}")
            return False
    
    # 추가 비즈니스 로직 메서드들
    def search_announcements(self, search_term: str) -> List[Announcement]:
        """공고 검색"""
        try:
            return self.repository.search_announcements(search_term)
        except Exception as e:
            logger.error(f"공고 검색 오류: {e}")
            return []
    
    def get_announcements_by_type(self, business_type: str) -> List[Announcement]:
        """사업 유형별 공고 조회"""
        try:
            return self.repository.find_by_business_type(business_type)
        except Exception as e:
            logger.error(f"유형별 공고 조회 오류: {e}")
            return []
    
    def get_recent_announcements(self, limit: int = 10) -> List[Announcement]:
        """최근 공고 조회"""
        try:
            return self.repository.get_recent_announcements(limit)
        except Exception as e:
            logger.error(f"최근 공고 조회 오류: {e}")
            return []
    
    def get_announcement_statistics(self) -> dict:
        """공고 통계 조회"""
        try:
            return self.repository.get_statistics()
        except Exception as e:
            logger.error(f"공고 통계 조회 오류: {e}")
            return {}