"""
Standard pagination and sorting system for list endpoints.

Provides consistent pagination parameters, sorting options, and response
structures for all list-based API operations.
"""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
from fastapi import Query

# Type variable for paginated items
T = TypeVar('T')


class SortOrder(str, Enum):
    """Standard sort order options."""
    ASC = "asc"
    DESC = "desc"
    ASCENDING = "ascending"  # Alternative naming
    DESCENDING = "descending"  # Alternative naming


class CommonSortFields(str, Enum):
    """Common sort fields available across domains."""
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"
    TITLE = "title"
    STATUS = "status"
    PRIORITY = "priority"


class PaginationParams(BaseModel):
    """
    Standard pagination parameters for list endpoints.
    
    Provides consistent pagination interface with validation
    and MongoDB-compatible skip/limit calculations.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "size": 20,
                "sort": "created_at",
                "order": "desc"
            }
        }
    )
    
    page: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Page number (1-based)"
    )
    size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)"
    )
    sort: str = Field(
        default="id",
        description="Field to sort by"
    )
    order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order (asc/desc)"
    )
    
    @validator('sort')
    def validate_sort_field(cls, v):
        """Validate sort field format."""
        if not v or not isinstance(v, str):
            return "id"
        
        # Remove any potential injection attempts and replace dots with underscores
        sanitized = v.replace("$", "").replace(".", "_")
        return sanitized.lower()
    
    @validator('order', pre=True)
    def normalize_order(cls, v):
        """Normalize sort order values."""
        if isinstance(v, str):
            v = v.lower()
            if v in ['asc', 'ascending', '1', 'up']:
                return SortOrder.ASC
            elif v in ['desc', 'descending', '-1', 'down']:
                return SortOrder.DESC
        return v
    
    @property
    def skip(self) -> int:
        """Calculate MongoDB skip value."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get MongoDB limit value."""
        return self.size
    
    @property
    def mongo_sort(self) -> List[tuple]:
        """Get MongoDB sort specification."""
        direction = 1 if self.order in [SortOrder.ASC, SortOrder.ASCENDING] else -1
        return [(self.sort, direction)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "page": self.page,
            "size": self.size,
            "sort": self.sort,
            "order": self.order.value,
            "skip": self.skip,
            "limit": self.limit
        }


class SortParams(BaseModel):
    """Enhanced sorting parameters with multiple sort fields."""
    
    fields: List[str] = Field(
        default=["id"],
        description="List of fields to sort by (in priority order)"
    )
    orders: List[SortOrder] = Field(
        default=[SortOrder.DESC],
        description="Sort orders for each field"
    )
    
    @validator('fields')
    def validate_sort_fields(cls, v):
        """Validate and sanitize sort fields."""
        if not v:
            return ["id"]
        
        sanitized = []
        for field in v:
            if isinstance(field, str):
                sanitized_field = field.replace("$", "").replace(".", "_").lower()
                sanitized.append(sanitized_field)
        
        return sanitized if sanitized else ["id"]
    
    @validator('orders')
    def validate_orders_length(cls, v, values):
        """Ensure orders list matches fields list length."""
        fields = values.get('fields', [])
        if len(v) < len(fields):
            # Pad with DESC for missing orders
            v.extend([SortOrder.DESC] * (len(fields) - len(v)))
        elif len(v) > len(fields):
            # Truncate excess orders
            v = v[:len(fields)]
        return v
    
    @property
    def mongo_sort(self) -> List[tuple]:
        """Get MongoDB sort specification for multiple fields."""
        sort_spec = []
        for field, order in zip(self.fields, self.orders):
            direction = 1 if order in [SortOrder.ASC, SortOrder.ASCENDING] else -1
            sort_spec.append((field, direction))
        return sort_spec


class FilterParams(BaseModel):
    """Standard filtering parameters."""
    
    search: Optional[str] = Field(
        None,
        description="Text search query",
        max_length=200
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status"
    )
    category: Optional[str] = Field(
        None,
        description="Filter by category"
    )
    date_from: Optional[str] = Field(
        None,
        description="Filter from date (ISO format)"
    )
    date_to: Optional[str] = Field(
        None,
        description="Filter to date (ISO format)"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filter by tags"
    )
    
    def to_mongo_filter(self) -> Dict[str, Any]:
        """Convert to MongoDB filter specification."""
        filter_spec = {}
        
        if self.search:
            # Text search - would use MongoDB text index
            filter_spec["$text"] = {"$search": self.search}
        
        if self.status:
            filter_spec["status"] = {"$regex": f"^{self.status}$", "$options": "i"}
        
        if self.category:
            filter_spec["category"] = {"$regex": f"^{self.category}$", "$options": "i"}
        
        if self.date_from or self.date_to:
            date_filter = {}
            if self.date_from:
                date_filter["$gte"] = self.date_from
            if self.date_to:
                date_filter["$lte"] = self.date_to
            filter_spec["created_at"] = date_filter
        
        if self.tags:
            filter_spec["tags"] = {"$in": self.tags}
        
        return filter_spec


class PaginatedResult(BaseModel, Generic[T]):
    """
    Result container for paginated queries.
    
    Contains the items, total count, and calculated pagination metadata.
    """
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    size: int = Field(..., description="Items per page", ge=1)
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.size <= 0:
            return 0
        return (self.total + self.size - 1) // self.size
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1
    
    @property
    def is_first_page(self) -> bool:
        """Check if this is the first page."""
        return self.page == 1
    
    @property
    def is_last_page(self) -> bool:
        """Check if this is the last page."""
        return self.page >= self.total_pages
    
    @property
    def next_page(self) -> Optional[int]:
        """Get next page number if available."""
        return self.page + 1 if self.has_next else None
    
    @property
    def previous_page(self) -> Optional[int]:
        """Get previous page number if available."""
        return self.page - 1 if self.has_previous else None
    
    def to_pagination_meta(self) -> Dict[str, Any]:
        """Convert to pagination metadata dictionary."""
        return {
            "total": self.total,
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
            "is_first_page": self.is_first_page,
            "is_last_page": self.is_last_page,
            "next_page": self.next_page,
            "previous_page": self.previous_page
        }


# FastAPI dependency functions for query parameters
def PaginationDep(
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("id", description="Sort field"),
    order: SortOrder = Query(SortOrder.DESC, description="Sort order")
) -> PaginationParams:
    """FastAPI dependency for pagination parameters."""
    return PaginationParams(page=page, size=size, sort=sort, order=order)


def FilterDep(
    search: Optional[str] = Query(None, max_length=200, description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[str] = Query(None, description="Date from (ISO format)"),
    date_to: Optional[str] = Query(None, description="Date to (ISO format)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags")
) -> FilterParams:
    """FastAPI dependency for filter parameters."""
    return FilterParams(
        search=search,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        tags=tags
    )


# Utility functions for pagination
def paginate_query_result(
    items: List[Any],
    total: int,
    pagination: PaginationParams
) -> PaginatedResult:
    """
    Create paginated result from query results.
    
    Args:
        items: List of items from the query
        total: Total count of items (without pagination)
        pagination: Pagination parameters used
        
    Returns:
        PaginatedResult with metadata
    """
    return PaginatedResult(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size
    )


def build_pagination_links(
    base_url: str,
    pagination_result: PaginatedResult,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[str]]:
    """
    Build pagination navigation links.
    
    Args:
        base_url: Base URL for the endpoint
        pagination_result: Paginated result with metadata
        query_params: Additional query parameters to preserve
        
    Returns:
        Dictionary with navigation links
    """
    query_params = query_params or {}
    
    def build_url(page: int) -> str:
        params = {**query_params, "page": str(page)}
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"
    
    links = {
        "self": build_url(pagination_result.page),
        "first": build_url(1) if pagination_result.total > 0 else None,
        "last": build_url(pagination_result.total_pages) if pagination_result.total_pages > 0 else None,
        "next": build_url(pagination_result.next_page) if pagination_result.has_next else None,
        "previous": build_url(pagination_result.previous_page) if pagination_result.has_previous else None
    }
    
    return links


class PaginationHelper:
    """Helper class for common pagination operations."""
    
    @staticmethod
    def validate_pagination_params(
        page: int,
        size: int,
        max_size: int = 100
    ) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters.
        
        Args:
            page: Page number
            size: Page size
            max_size: Maximum allowed page size
            
        Returns:
            Tuple of (validated_page, validated_size)
        """
        page = max(1, page)
        size = max(1, min(size, max_size))
        return page, size
    
    @staticmethod
    def calculate_offset_limit(page: int, size: int) -> tuple[int, int]:
        """
        Calculate offset and limit for database queries.
        
        Args:
            page: Page number (1-based)
            size: Page size
            
        Returns:
            Tuple of (offset, limit)
        """
        offset = (page - 1) * size
        limit = size
        return offset, limit
    
    @staticmethod
    def create_empty_result(pagination: PaginationParams) -> PaginatedResult:
        """Create empty paginated result."""
        return PaginatedResult(
            items=[],
            total=0,
            page=pagination.page,
            size=pagination.size
        )