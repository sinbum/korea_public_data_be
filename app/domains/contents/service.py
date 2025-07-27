"""
Content Service implementation.

Provides business logic for content-related operations using Repository pattern.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Content, ContentCreate, ContentUpdate
from .repository import ContentRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import ContentItem
from ...shared.interfaces.base_service import BaseService
from ...shared.interfaces.domain_services import IContentService
from ...shared.schemas import PaginatedResponse, DataCollectionResult
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class ContentService(BaseService[Content, ContentCreate, ContentUpdate, ContentItem]):
    """콘텐츠 서비스"""
    
    def __init__(self, repository: ContentRepository, api_client: Optional[KStartupAPIClient] = None):
        super().__init__(repository=repository, logger=logger)
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    # BaseService 추상 메소드 구현
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """ID로 콘텐츠 데이터 조회"""
        return await self.repository.get_by_id(item_id)
    
    async def _fetch_list(
        self, 
        page: int, 
        limit: int, 
        query_params: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int]:
        """페이지네이션된 콘텐츠 목록 조회"""
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
    
    async def _save_new_item(self, domain_data: Content) -> Dict[str, Any]:
        """새 콘텐츠 저장"""
        return await self.repository.create(domain_data)
    
    async def _save_updated_item(self, item_id: str, domain_data: Content) -> Dict[str, Any]:
        """콘텐츠 업데이트"""
        return await self.repository.update(item_id, domain_data)
    
    async def _delete_item(self, item_id: str) -> bool:
        """콘텐츠 삭제"""
        return await self.repository.delete(item_id)
    
    async def _transform_to_response(self, raw_data: Dict[str, Any]) -> ContentItem:
        """원본 데이터를 응답 모델로 변환"""
        return ContentItem(**raw_data)
    
    async def _transform_to_domain(self, input_data) -> Content:
        """입력 데이터를 도메인 모델로 변환"""
        if isinstance(input_data, ContentCreate):
            return Content(**input_data.model_dump())
        elif isinstance(input_data, ContentUpdate):
            return Content(**input_data.model_dump(exclude_unset=True))
        else:
            return Content(**input_data)
    
    # 도메인별 특화 메소드들
    async def fetch_contents_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 콘텐츠 데이터 수집"""
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
            contents = self.fetch_and_save_contents(page_no, num_of_rows)
            result.total_fetched = len(contents)
            result.new_items = len(contents)
            
        except Exception as e:
            result.errors.append(str(e))
            self._log_error(f"콘텐츠 데이터 수집 실패: {e}")
        
        end_time = datetime.utcnow()
        result.collection_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def get_contents_paginated(
        self,
        pagination_params,
        filters: Optional[Dict[str, Any]] = None
    ):
        """페이지네이션된 콘텐츠 목록 조회"""
        try:
            # Apply filters 
            query_filter = QueryFilter()
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        query_filter.eq(key, value)
            
            # Get paginated results using repository
            result = self.repository.get_paginated(
                page=pagination_params.page,
                page_size=pagination_params.size,
                filters=query_filter
            )
            
            return result
            
        except Exception as e:
            logger.error(f"콘텐츠 페이지네이션 조회 오류: {e}")
            raise
    
    async def get_contents_by_type(
        self,
        content_type_code: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """콘텐츠 타입별 목록 조회"""
        filters = {"content_type_code": content_type_code}
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_popular_contents(
        self,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """인기 콘텐츠 목록 조회"""
        # 인기도 기준으로 정렬 (예: 좋아요 수, 조회수 등)
        filters = {}
        return await self.get_list(page=page, limit=limit, filters=filters, sort_by="like_count")
    
    async def like_content(self, content_id: str) -> bool:
        """콘텐츠 좋아요"""
        try:
            # 좋아요 수 증가 로직
            content = await self._fetch_by_id(content_id)
            if content:
                like_count = content.get("like_count", 0) + 1
                await self.repository.update(content_id, {"like_count": like_count})
                return True
            return False
        except Exception as e:
            self._log_error(f"콘텐츠 좋아요 실패: {e}")
            return False
    
    async def get_content_statistics(self) -> Dict[str, Any]:
        """콘텐츠 통계 조회"""
        total_count = await self.repository.count()
        return {
            "total_contents": total_count,
            "content_types": {}  # 타입별 통계 등
        }
    
    async def search_contents(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """콘텐츠 텍스트 검색"""
        filters = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"summary": {"$regex": query, "$options": "i"}}
            ]
        }
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    def fetch_and_save_contents(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        order_by_latest: bool = True
    ) -> List[Content]:
        """공공데이터에서 콘텐츠 정보를 가져와 저장"""
        contents = []
        
        try:
            # K-Startup API 호출 - 최신순의 경우 높은 페이지 번호부터 시작
            if order_by_latest and page_no == 1:
                # 최신 데이터를 가져오기 위해 높은 페이지 번호부터 시작
                # 총 페이지 수를 모르므로 큰 번호부터 시도
                pages_to_try = [20, 15, 10, 5, 1]  # 큰 페이지부터 시도
                response = None
                
                with KStartupAPIClient() as client:
                    for try_page in pages_to_try:
                        logger.info(f"콘텐츠 페이지 {try_page}로 조회 시도 중...")
                        temp_response = client.get_content_information(
                            page_no=try_page,
                            num_of_rows=num_of_rows,
                            content_type=content_type,
                            category=category,
                            order_by_latest=order_by_latest
                        )
                        
                        if temp_response.success and temp_response.data and hasattr(temp_response.data, 'data') and temp_response.data.data:
                            logger.info(f"콘텐츠 페이지 {try_page}에서 {len(temp_response.data.data)}개 데이터 발견")
                            response = temp_response
                            break
                    
                    if not response:
                        logger.warning("모든 페이지에서 콘텐츠 데이터를 찾을 수 없음")
                        response = client.get_content_information(
                            page_no=page_no,
                            num_of_rows=num_of_rows,
                            content_type=content_type,
                            category=category,
                            order_by_latest=order_by_latest
                        )
            else:
                # 기존 방식 (특정 페이지 요청 시)
                with KStartupAPIClient() as client:
                    response = client.get_content_information(
                        page_no=page_no,
                        num_of_rows=num_of_rows,
                        content_type=content_type,
                        category=category,
                        order_by_latest=order_by_latest
                    )
                
                if not response.success:
                    logger.error(f"API 호출 실패: {response.error}")
                    return contents
                
                logger.info(f"API 응답: {len(response.data.data)}건 조회")
                
                # 응답 데이터 처리
                for item in response.data.data:
                    try:
                        # ContentItem 객체에서 실제 데이터 추출
                        content_data = self._transform_contentitem_to_data(item)
                        
                        # 중복 체크
                        content_id = content_data.get("content_id")
                        title = content_data.get("title")
                        
                        is_duplicate = self.repository.check_duplicate(
                            content_id=content_id,
                            title=title
                        )
                        
                        if is_duplicate:
                            logger.info(f"중복 데이터 스킵: {title}")
                            continue
                        
                        # 새 콘텐츠 생성
                        content_create = ContentCreate(
                            content_data=content_data,
                            source_url=f"K-Startup-콘텐츠-{content_id or 'unknown'}"
                        )
                        
                        # Repository를 통해 저장
                        content = self.repository.create(content_create)
                        contents.append(content)
                        
                        logger.info(f"새로운 콘텐츠 저장: {title}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"K-Startup API 호출 실패: {e}")
            
        return contents
    
    def _transform_contentitem_to_data(self, content_item: ContentItem) -> dict:
        """ContentItem 객체를 내부 데이터 형식으로 변환 (실제 사용 가능한 필드만 매핑)"""
        published_date = None
        if content_item.register_date:
            try:
                # register_date가 이미 검증된 형식이므로 datetime으로 변환
                published_date = datetime.fromisoformat(content_item.register_date.replace(' ', 'T'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format: {content_item.register_date}")
        
        update_date = None
        if content_item.update_date:
            try:
                update_date = datetime.fromisoformat(content_item.update_date.replace(' ', 'T'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid update date format: {content_item.update_date}")
        
        # tags 처리 (콤마로 구분된 문자열을 리스트로 변환)
        tags_list = []
        if content_item.tags:
            tags_list = [tag.strip() for tag in content_item.tags.split(',') if tag.strip()]
        
        return {
            # 기본 정보 (실제 사용 가능한 필드들)
            "content_id": content_item.id,
            "title": content_item.title,
            "content_type": content_item.content_type,
            "category": content_item.category,
            "description": content_item.content_summary,
            "content_url": content_item.detail_page_url,
            "thumbnail_url": None,  # API에서 제공하지 않는 필드
            "tags": tags_list,
            "view_count": content_item.view_count or 0,
            "like_count": 0,  # API에서 제공하지 않는 필드
            "published_date": published_date,
            
            # 상세 정보 (실제 사용 가능한 필드들)
            "content_summary": content_item.content_summary,
            "content_body": content_item.content_body,
            "file_name": content_item.file_name,
            "author": content_item.author,
            "update_date": update_date,
            "publish_status": content_item.publish_status
        }
        
    def _transform_api_data(self, api_item: dict) -> dict:
        """K-Startup API 응답을 내부 모델로 변환 (레거시 메서드)"""
        published_date = None
        if api_item.get("published_date"):
            try:
                published_date = datetime.fromisoformat(api_item["published_date"])
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format: {api_item.get('published_date')}")
        
        return {
            "content_id": api_item.get("content_id"),
            "title": api_item.get("title"),
            "content_type": api_item.get("content_type"),
            "category": api_item.get("category"),
            "description": api_item.get("description"),
            "content_url": api_item.get("content_url"),
            "thumbnail_url": api_item.get("thumbnail_url"),
            "tags": api_item.get("tags", []),
            "view_count": api_item.get("view_count", 0),
            "like_count": api_item.get("like_count", 0),
            "published_date": published_date
        }
    
    def get_contents(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True,
        order_by_latest: bool = True
    ) -> PaginationResult[Content]:
        """저장된 콘텐츠 목록 조회 (페이지네이션, 기본 최신순)"""
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
            logger.error(f"콘텐츠 목록 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_content_by_id(self, content_id: str) -> Optional[Content]:
        """ID로 콘텐츠 조회"""
        try:
            content = self.repository.get_by_id(content_id)
            
            # 조회수 증가
            if content:
                self.repository.increment_view_count(content.content_data.content_id)
            
            return content
        except Exception as e:
            logger.error(f"콘텐츠 조회 오류: {e}")
            return None
    
    def create_content(self, content_data: ContentCreate) -> Content:
        """새 콘텐츠 생성"""
        try:
            return self.repository.create(content_data)
        except Exception as e:
            logger.error(f"콘텐츠 생성 오류: {e}")
            raise
    
    def update_content(
        self, 
        content_id: str, 
        update_data: ContentUpdate
    ) -> Optional[Content]:
        """콘텐츠 수정"""
        try:
            return self.repository.update_by_id(content_id, update_data)
        except Exception as e:
            logger.error(f"콘텐츠 수정 오류: {e}")
            return None
    
    def delete_content(self, content_id: str) -> bool:
        """콘텐츠 삭제 (비활성화)"""
        try:
            return self.repository.delete_by_id(content_id, soft_delete=True)
        except Exception as e:
            logger.error(f"콘텐츠 삭제 오류: {e}")
            return False
    
    # 추가 비즈니스 로직 메서드들
    def search_contents(self, search_term: str) -> List[Content]:
        """콘텐츠 검색"""
        try:
            return self.repository.search_contents(search_term)
        except Exception as e:
            logger.error(f"콘텐츠 검색 오류: {e}")
            return []
    
    def get_contents_by_type(self, content_type: str) -> List[Content]:
        """콘텐츠 유형별 조회"""
        try:
            return self.repository.find_by_content_type(content_type)
        except Exception as e:
            logger.error(f"유형별 콘텐츠 조회 오류: {e}")
            return []
    
    def get_contents_by_category(self, category: str) -> List[Content]:
        """카테고리별 콘텐츠 조회"""
        try:
            return self.repository.find_by_category(category)
        except Exception as e:
            logger.error(f"카테고리별 콘텐츠 조회 오류: {e}")
            return []
    
    def get_contents_by_tags(self, tags: List[str]) -> List[Content]:
        """태그별 콘텐츠 조회"""
        try:
            return self.repository.find_by_tags(tags)
        except Exception as e:
            logger.error(f"태그별 콘텐츠 조회 오류: {e}")
            return []
    
    def get_popular_contents(self, limit: int = 10) -> List[Content]:
        """인기 콘텐츠 조회 (조회수 기준)"""
        try:
            return self.repository.get_popular_contents(limit)
        except Exception as e:
            logger.error(f"인기 콘텐츠 조회 오류: {e}")
            return []
    
    def get_most_liked_contents(self, limit: int = 10) -> List[Content]:
        """좋아요 많은 콘텐츠 조회"""
        try:
            return self.repository.get_most_liked_contents(limit)
        except Exception as e:
            logger.error(f"좋아요 많은 콘텐츠 조회 오류: {e}")
            return []
    
    def get_recent_contents(self, limit: int = 10) -> List[Content]:
        """최근 콘텐츠 조회"""
        try:
            return self.repository.get_recent_contents(limit)
        except Exception as e:
            logger.error(f"최근 콘텐츠 조회 오류: {e}")
            return []
    
    def get_contents_by_date_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Content]:
        """날짜 범위별 콘텐츠 조회"""
        try:
            return self.repository.find_by_date_range(start_date, end_date)
        except Exception as e:
            logger.error(f"날짜 범위별 콘텐츠 조회 오류: {e}")
            return []
    
    def get_contents_with_filter(
        self,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_view_count: Optional[int] = None,
        min_like_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginationResult[Content]:
        """필터 조건에 따른 콘텐츠 조회"""
        try:
            return self.repository.get_contents_by_filter(
                content_type=content_type,
                category=category,
                tags=tags,
                min_view_count=min_view_count,
                min_like_count=min_like_count,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            logger.error(f"필터 조건별 콘텐츠 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def like_content(self, content_id: str) -> bool:
        """콘텐츠 좋아요"""
        try:
            return self.repository.increment_like_count(content_id)
        except Exception as e:
            logger.error(f"콘텐츠 좋아요 오류: {e}")
            return False
    
    def get_content_statistics(self) -> dict:
        """콘텐츠 통계 조회"""
        try:
            return self.repository.get_statistics()
        except Exception as e:
            logger.error(f"콘텐츠 통계 조회 오류: {e}")
            return {}
    
    def bulk_create_contents(self, contents: List[ContentCreate]) -> List[Content]:
        """대량 콘텐츠 생성"""
        try:
            return self.repository.bulk_create_contents(contents)
        except Exception as e:
            logger.error(f"대량 콘텐츠 생성 오류: {e}")
            return []