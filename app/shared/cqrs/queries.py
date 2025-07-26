"""
Query pattern implementation for CQRS.

Queries represent read operations that don't change system state.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Any, Dict, List, Protocol
from pydantic import BaseModel
from datetime import datetime
import uuid

# Type variables
TResult = TypeVar('TResult')
TQuery = TypeVar('TQuery', bound='Query')


class Query(BaseModel, ABC):
    """
    Base query class.
    
    Queries represent read operations that don't change system state.
    They should be immutable and contain all necessary parameters.
    """
    
    # Query metadata
    query_id: str = None
    timestamp: datetime = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __init__(self, **data):
        if not data.get('query_id'):
            data['query_id'] = str(uuid.uuid4())
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)
    
    class Config:
        # Queries should be immutable
        frozen = True
        # Allow arbitrary types for flexibility
        arbitrary_types_allowed = True


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """
    Abstract base class for query handlers.
    
    Each query should have exactly one handler that processes it.
    """
    
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """
        Handle the query and return result.
        
        Args:
            query: The query to handle
            
        Returns:
            Query execution result
        """
        pass
    
    async def can_handle(self, query: Query) -> bool:
        """
        Check if this handler can process the given query.
        
        Default implementation checks query type.
        Can be overridden for more complex logic.
        """
        return isinstance(query, self._get_query_type())
    
    def _get_query_type(self) -> type:
        """Get the query type this handler processes."""
        # Extract from Generic type arguments
        import typing
        orig_bases = getattr(self.__class__, '__orig_bases__', ())
        for base in orig_bases:
            if hasattr(base, '__args__') and len(base.__args__) >= 1:
                return base.__args__[0]
        return Query


class IQueryBus(Protocol):
    """
    Query bus interface.
    
    Responsible for routing queries to appropriate handlers.
    """
    
    async def execute(self, query: Query) -> Any:
        """Execute a query and return the result."""
        ...
    
    def register_handler(self, query_type: type, handler: QueryHandler) -> None:
        """Register a query handler for a specific query type."""
        ...
    
    def unregister_handler(self, query_type: type) -> None:
        """Unregister a query handler."""
        ...


# Domain-specific query base classes

class AnnouncementQuery(Query):
    """Base class for announcement-related queries."""
    pass


class BusinessQuery(Query):
    """Base class for business-related queries."""
    pass


class ContentQuery(Query):
    """Base class for content-related queries."""
    pass


class StatisticsQuery(Query):
    """Base class for statistics-related queries."""
    pass


# Specific query implementations

class GetAnnouncementByIdQuery(AnnouncementQuery):
    """Query to get announcement by ID."""
    
    announcement_id: str


class GetAnnouncementListQuery(AnnouncementQuery):
    """Query to get paginated announcement list."""
    
    page: int = 1
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class GetActiveAnnouncementsQuery(AnnouncementQuery):
    """Query to get active announcements."""
    
    page: int = 1
    limit: int = 20


class GetAnnouncementsByCategoryQuery(AnnouncementQuery):
    """Query to get announcements by category."""
    
    category_code: str
    page: int = 1
    limit: int = 20


class GetAnnouncementsByDateRangeQuery(AnnouncementQuery):
    """Query to get announcements by date range."""
    
    start_date: datetime
    end_date: datetime
    page: int = 1
    limit: int = 20


class SearchAnnouncementsQuery(AnnouncementQuery):
    """Query to search announcements by text."""
    
    query_text: str
    page: int = 1
    limit: int = 20


class GetBusinessByIdQuery(BusinessQuery):
    """Query to get business by ID."""
    
    business_id: str


class GetBusinessListQuery(BusinessQuery):
    """Query to get paginated business list."""
    
    page: int = 1
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class GetBusinessesByCategoryQuery(BusinessQuery):
    """Query to get businesses by category."""
    
    category: str
    page: int = 1
    limit: int = 20


class GetBusinessesByOrganizationQuery(BusinessQuery):
    """Query to get businesses by organization."""
    
    organization_name: str
    page: int = 1
    limit: int = 20


class GetBusinessStatisticsQuery(BusinessQuery):
    """Query to get business statistics."""
    pass


class SearchBusinessesQuery(BusinessQuery):
    """Query to search businesses by text."""
    
    query_text: str
    page: int = 1
    limit: int = 20


class GetContentByIdQuery(ContentQuery):
    """Query to get content by ID."""
    
    content_id: str


class GetContentListQuery(ContentQuery):
    """Query to get paginated content list."""
    
    page: int = 1
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class GetContentsByTypeQuery(ContentQuery):
    """Query to get contents by type."""
    
    content_type_code: str
    page: int = 1
    limit: int = 20


class GetPopularContentsQuery(ContentQuery):
    """Query to get popular contents."""
    
    page: int = 1
    limit: int = 20


class GetContentStatisticsQuery(ContentQuery):
    """Query to get content statistics."""
    pass


class SearchContentsQuery(ContentQuery):
    """Query to search contents by text."""
    
    query_text: str
    page: int = 1
    limit: int = 20


class GetStatisticsByIdQuery(StatisticsQuery):
    """Query to get statistics by ID."""
    
    statistics_id: str


class GetStatisticsListQuery(StatisticsQuery):
    """Query to get paginated statistics list."""
    
    page: int = 1
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class GetStatisticsByCategoryQuery(StatisticsQuery):
    """Query to get statistics by category."""
    
    category: str
    page: int = 1
    limit: int = 20


class GetStatisticsByPeriodQuery(StatisticsQuery):
    """Query to get statistics by period."""
    
    year: int
    month: Optional[int] = None
    page: int = 1
    limit: int = 20


class GetTrendAnalysisQuery(StatisticsQuery):
    """Query to get trend analysis."""
    
    category: str
    start_year: int
    end_year: int


class GetSummaryStatisticsQuery(StatisticsQuery):
    """Query to get summary statistics."""
    pass


class CalculateGrowthRateQuery(StatisticsQuery):
    """Query to calculate growth rate."""
    
    category: str
    year: int
    comparison_year: int