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
from ...core.cache import announcement_cache, detail_cache, cached
import logging

logger = logging.getLogger(__name__)


class AnnouncementService(BaseService[Announcement, AnnouncementCreate, AnnouncementUpdate, AnnouncementItem]):
    """사업공고 서비스"""
    
    def __init__(self, repository: AnnouncementRepository, api_client: Optional[KStartupAPIClient] = None):
        super().__init__(repository=repository, logger=logger)
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    def fetch_and_save_announcements(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None,
        order_by_latest: bool = True
    ) -> List[Announcement]:
        """K-Startup API에서 사업공고 정보를 가져와 저장"""
        announcements = []
        all_processed_items = []  # 처리된 모든 아이템 (새로 저장 + 중복 스킵)
        
        try:
            # K-Startup API 호출 (동기 방식)
            if order_by_latest:
                # 현재 연도부터 역순으로 조회
                current_year = datetime.now().year
                years_to_try = [str(current_year), str(current_year - 1), None]
                
                for business_year in years_to_try:
                    logger.info(f"사업연도 {business_year or '전체'}로 조회 시도 중...")
                    with self.api_client as client:
                        response = client.get_announcement_information(
                            page_no=page_no,
                            num_of_rows=num_of_rows,
                            business_name=business_name,
                            business_type=business_type
                        )
                    
                    if response.success and response.data and hasattr(response.data, 'data') and response.data.data:
                        logger.info(f"사업연도 {business_year or '전체'}에서 {len(response.data.data)}개 데이터 발견")
                        break
                else:
                    logger.warning("모든 연도에서 데이터를 찾을 수 없음")
                    with self.api_client as client:
                        response = client.get_announcement_information(
                            page_no=page_no,
                            num_of_rows=num_of_rows,
                            business_name=business_name,
                            business_type=business_type
                        )
            else:
                with self.api_client as client:
                    response = client.get_announcement_information(
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
                            # AnnouncementItem 객체에서 실제 데이터 추출
                            announcement_data = self._transform_announcementitem_to_data(item)
                            
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
    
    def _transform_announcementitem_to_data(self, announcement_item) -> dict:
        """AnnouncementItem 객체를 새로운 확장된 데이터 형식으로 변환 (모든 API 필드 활용)"""
        
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
        
        # 모집기간 설정 (레거시 지원)
        recruitment_period = ""
        if announcement_item.start_date and announcement_item.end_date:
            recruitment_period = f"{announcement_item.start_date} ~ {announcement_item.end_date}"
        elif announcement_item.start_date:
            recruitment_period = f"{announcement_item.start_date} ~"
        elif announcement_item.end_date:
            recruitment_period = f"~ {announcement_item.end_date}"
        
        # 통합 문의처 정보 구성
        contact_info = ""
        contact_parts = []
        if announcement_item.contact_department:
            contact_parts.append(announcement_item.contact_department)
        if announcement_item.contact_number:
            contact_parts.append(f"({announcement_item.contact_number})")
        contact_info = " ".join(contact_parts) if contact_parts else None
        
        # 신청 방법 통합 정보 구성
        application_method = ""
        if announcement_item.online_reception:
            application_method = f"온라인 접수 - {announcement_item.online_reception}"
        elif announcement_item.business_guidance_url:
            application_method = f"온라인 접수 - {announcement_item.business_guidance_url}"
        elif announcement_item.business_application_url:
            application_method = f"온라인 접수 - {announcement_item.business_application_url}"
        else:
            application_method = "온라인 접수"
        
        # 상태 판정
        status = "모집중" if getattr(announcement_item, 'recruitment_progress', 'N') == "Y" else "모집종료"
        
        # 제목 처리 - title이 없으면 integrated_business_name이나 기본값 사용
        title = announcement_item.title or announcement_item.integrated_business_name or "제목 없음"
        
        return {
            # === 기본 공고 정보 ===
            "announcement_id": str(announcement_item.announcement_id) if announcement_item.announcement_id else None,
            "title": title,
            "content": announcement_item.content,
            
            # === 일정 정보 ===
            "start_date": announcement_item.start_date,
            "end_date": announcement_item.end_date,
            "announcement_date": convert_date_to_datetime(announcement_item.start_date),
            "deadline": convert_date_to_datetime(announcement_item.end_date),
            
            # === 사업 정보 ===
            "business_category": announcement_item.business_category,
            "integrated_business_name": announcement_item.integrated_business_name,
            "business_overview": announcement_item.content,  # content와 동일
            
            # === 지원 대상 및 조건 ===
            "application_target": announcement_item.application_target,
            "application_target_content": announcement_item.application_target_content,
            "application_exclusion_content": announcement_item.application_exclusion_content,
            "support_target": announcement_item.application_target,  # application_target과 동일
            "business_entry": announcement_item.business_entry,
            "business_target_age": announcement_item.business_target_age,
            "support_region": announcement_item.support_region,
            
            # === 기관 정보 ===
            "organization": announcement_item.organization,
            "supervising_institution": announcement_item.supervising_institution,
            "contact_department": announcement_item.contact_department,
            "contact_number": announcement_item.contact_number,
            "contact_info": contact_info,  # 통합된 문의처 정보
            
            # === URL 정보 ===
            "detail_page_url": announcement_item.detail_page_url,
            "business_guidance_url": announcement_item.business_guidance_url,
            "business_application_url": announcement_item.business_application_url,
            
            # === 신청 방법 정보 ===
            "application_method": application_method,  # 통합된 신청 방법
            "online_reception": announcement_item.online_reception,
            "visit_reception": announcement_item.visit_reception,
            "email_reception": announcement_item.email_reception,
            "fax_reception": announcement_item.fax_reception,
            "postal_reception": announcement_item.postal_reception,
            "other_reception": announcement_item.other_reception,
            
            # === 상태 정보 ===
            "status": status,
            "integrated_announcement": announcement_item.integrated_announcement,
            "recruitment_progress": announcement_item.recruitment_progress,
            "performance_material": announcement_item.performance_material,
            
            # === 레거시 필드 (하위 호환성) ===
            "business_id": str(announcement_item.announcement_id) if announcement_item.announcement_id else None,
            "business_name": title,  # 처리된 title 사용
            "business_type": announcement_item.business_category,  # business_category와 동일
            "recruitment_period": recruitment_period,  # 계산된 모집기간
        }
    
    # 이전 레거시 메서드들은 향후 제거 예정 (K-Startup 클라이언트로 완전 마이그레이션 후)
    
    def get_announcements(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True,
        order_by_latest: bool = True,
        sort_by: Optional[str] = "announcement_date",
        business_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> PaginationResult[Announcement]:
        """저장된 사업공고 목록 조회 (페이지네이션, 기본 최신순, 필터링 지원)"""
        try:
            # Enhanced logging to debug filtering issue
            logger.info(f"Service get_announcements called with: page={page}, page_size={page_size}, is_active={is_active}, business_type='{business_type}', status='{status}', search='{search}'")
            
            # 기본 필터 설정
            filters = QueryFilter()
            if is_active:
                filters.eq("is_active", True)
            else:
                filters.eq("is_active", False)
            
            # business_type 필터 추가
            if business_type:
                logger.info(f"Applying business_type filter: '{business_type}' to field 'announcement_data.business_type'")
                # Try both business_type and business_category fields for compatibility
                filters.eq("announcement_data.business_type", business_type)
                # Also add alternative field name search
                # filters.eq("announcement_data.business_category", business_type)
            
            # status 필터 추가
            if status:
                filters.eq("announcement_data.status", status)
            
            # 검색 필터 추가 (사업명 또는 기관명에서 검색)
            if search:
                # MongoDB regex를 사용한 텍스트 검색
                filters.regex("announcement_data.business_name", search, "i")  # case-insensitive
            
            # Log the final filters being applied
            logger.info(f"Final filters to be applied: {filters.to_dict()}")
            
            # 마감임박순 선택 시 마감일이 오늘 이후인 공고만 필터링
            if sort_by == "end_date":
                from datetime import datetime
                from zoneinfo import ZoneInfo
                
                # 한국시간(Asia/Seoul) 기준으로 오늘 날짜 계산
                korea_tz = ZoneInfo("Asia/Seoul")
                today = datetime.now(korea_tz).strftime("%Y-%m-%d")
                filters.gte("announcement_data.end_date", today)
                logger.info(f"마감임박순 정렬: 오늘({today}, KST) 이후 마감인 공고만 필터링")
            
            # 정렬 설정 (sort_by 파라미터에 따라 announcement_date 또는 end_date 기준)
            from ...core.interfaces.base_repository import SortOption
            if order_by_latest:
                if sort_by == "end_date":
                    # 마감일 기준 정렬 (마감 임박순 - 오늘 이후 마감인 공고만)
                    sort = SortOption().asc("announcement_data.end_date").desc("announcement_data.announcement_id")
                else:
                    # 기본값: 공고일 기준 정렬 (최신 공고순)
                    sort = SortOption().desc("announcement_data.announcement_date").desc("announcement_data.announcement_id")
            else:
                sort = None
            
            result = self.repository.get_paginated(
                page=page, 
                page_size=page_size, 
                filters=filters,
                sort=sort
            )
            
            logger.info(f"Service returning {len(result.items)} items out of {result.total_count} total")
            
            # Log sample of returned items to verify filtering
            if result.items and business_type:
                sample_types = [item.announcement_data.business_type for item in result.items[:5]]
                logger.info(f"Sample business_types in result: {sample_types}")
            
            return result
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