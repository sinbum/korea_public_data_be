"""
Domain-specific service interfaces.

Defines contracts for each domain service following domain-driven design principles.
"""

from abc import ABC
from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime

from ..schemas import PaginatedResponse, DataCollectionResult
from ..models.kstartup import AnnouncementItem, BusinessItem, ContentItem, StatisticalItem


class IAnnouncementService(Protocol):
    """
    Announcement service interface.
    
    Defines contract for announcement-related business operations.
    """
    
    # Basic CRUD operations
    async def get_announcement_by_id(self, announcement_id: str) -> Optional[AnnouncementItem]:
        """공고 ID로 단일 공고 조회"""
        ...
    
    async def get_announcements(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> PaginatedResponse[AnnouncementItem]:
        """페이지네이션된 공고 목록 조회"""
        ...
    
    async def create_announcement(self, announcement_data: Dict[str, Any]) -> AnnouncementItem:
        """새 공고 생성"""
        ...
    
    async def update_announcement(
        self, 
        announcement_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[AnnouncementItem]:
        """기존 공고 업데이트"""
        ...
    
    async def delete_announcement(self, announcement_id: str) -> bool:
        """공고 삭제"""
        ...
    
    # Domain-specific operations
    async def fetch_announcements_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 공고 데이터 수집"""
        ...
    
    async def get_active_announcements(
        self,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """활성 상태의 공고 목록 조회"""
        ...
    
    async def get_announcements_by_category(
        self,
        category_code: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """카테고리별 공고 목록 조회"""
        ...
    
    async def get_announcements_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """날짜 범위별 공고 목록 조회"""
        ...
    
    async def search_announcements(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[AnnouncementItem]:
        """공고 텍스트 검색"""
        ...


class IBusinessService(Protocol):
    """
    Business service interface.
    
    Defines contract for business information operations.
    """
    
    # Basic CRUD operations
    async def get_business_by_id(self, business_id: str) -> Optional[BusinessItem]:
        """사업 ID로 단일 사업정보 조회"""
        ...
    
    async def get_businesses(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> PaginatedResponse[BusinessItem]:
        """페이지네이션된 사업정보 목록 조회"""
        ...
    
    async def create_business(self, business_data: Dict[str, Any]) -> BusinessItem:
        """새 사업정보 생성"""
        ...
    
    async def update_business(
        self, 
        business_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[BusinessItem]:
        """기존 사업정보 업데이트"""
        ...
    
    async def delete_business(self, business_id: str) -> bool:
        """사업정보 삭제"""
        ...
    
    # Domain-specific operations
    async def fetch_businesses_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 사업정보 데이터 수집"""
        ...
    
    async def get_businesses_by_category(
        self,
        category: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """사업 카테고리별 목록 조회"""
        ...
    
    async def get_businesses_by_organization(
        self,
        organization_name: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """주관기관별 사업정보 목록 조회"""
        ...
    
    async def get_business_statistics(self) -> Dict[str, Any]:
        """사업정보 통계 조회"""
        ...
    
    async def search_businesses(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[BusinessItem]:
        """사업정보 텍스트 검색"""
        ...


class IContentService(Protocol):
    """
    Content service interface.
    
    Defines contract for content management operations.
    """
    
    # Basic CRUD operations
    async def get_content_by_id(self, content_id: str) -> Optional[ContentItem]:
        """콘텐츠 ID로 단일 콘텐츠 조회"""
        ...
    
    async def get_contents(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> PaginatedResponse[ContentItem]:
        """페이지네이션된 콘텐츠 목록 조회"""
        ...
    
    async def create_content(self, content_data: Dict[str, Any]) -> ContentItem:
        """새 콘텐츠 생성"""
        ...
    
    async def update_content(
        self, 
        content_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[ContentItem]:
        """기존 콘텐츠 업데이트"""
        ...
    
    async def delete_content(self, content_id: str) -> bool:
        """콘텐츠 삭제"""
        ...
    
    # Domain-specific operations
    async def fetch_contents_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 콘텐츠 데이터 수집"""
        ...
    
    async def get_contents_by_type(
        self,
        content_type_code: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """콘텐츠 타입별 목록 조회"""
        ...
    
    async def get_popular_contents(
        self,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """인기 콘텐츠 목록 조회"""
        ...
    
    async def like_content(self, content_id: str) -> bool:
        """콘텐츠 좋아요"""
        ...
    
    async def unlike_content(self, content_id: str) -> bool:
        """콘텐츠 좋아요 취소"""
        ...
    
    async def get_content_statistics(self) -> Dict[str, Any]:
        """콘텐츠 통계 조회"""
        ...
    
    async def search_contents(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[ContentItem]:
        """콘텐츠 텍스트 검색"""
        ...


class IStatisticsService(Protocol):
    """
    Statistics service interface.
    
    Defines contract for statistics data operations.
    """
    
    # Basic CRUD operations
    async def get_statistics_by_id(self, statistics_id: str) -> Optional[StatisticalItem]:
        """통계 ID로 단일 통계 조회"""
        ...
    
    async def get_statistics(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> PaginatedResponse[StatisticalItem]:
        """페이지네이션된 통계 목록 조회"""
        ...
    
    async def create_statistics(self, statistics_data: Dict[str, Any]) -> StatisticalItem:
        """새 통계 생성"""
        ...
    
    async def update_statistics(
        self, 
        statistics_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[StatisticalItem]:
        """기존 통계 업데이트"""
        ...
    
    async def delete_statistics(self, statistics_id: str) -> bool:
        """통계 삭제"""
        ...
    
    # Domain-specific operations
    async def fetch_statistics_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 통계 데이터 수집"""
        ...
    
    async def get_statistics_by_category(
        self,
        category: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[StatisticalItem]:
        """카테고리별 통계 목록 조회"""
        ...
    
    async def get_statistics_by_period(
        self,
        year: int,
        month: Optional[int] = None,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[StatisticalItem]:
        """기간별 통계 목록 조회"""
        ...
    
    async def get_trend_analysis(
        self,
        category: str,
        start_year: int,
        end_year: int
    ) -> Dict[str, Any]:
        """통계 트렌드 분석"""
        ...
    
    async def get_summary_statistics(self) -> Dict[str, Any]:
        """요약 통계 조회"""
        ...
    
    async def calculate_growth_rate(
        self,
        category: str,
        year: int,
        comparison_year: int
    ) -> Dict[str, Any]:
        """성장률 계산"""
        ...


# Abstract base classes for domain services
class BaseAnnouncementService(ABC):
    """Base class for announcement service implementations."""
    pass


class BaseBusinessService(ABC):
    """Base class for business service implementations.""" 
    pass


class BaseContentService(ABC):
    """Base class for content service implementations."""
    pass


class BaseStatisticsService(ABC):
    """Base class for statistics service implementations."""
    pass