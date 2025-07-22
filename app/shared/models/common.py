"""
Common data models and response formats for the application.

Provides standardized models for API responses, pagination, and data exchange.
"""

from typing import Optional, List, Any, Dict, Generic, TypeVar
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

T = TypeVar('T')


class ResponseStatus(str, Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class APIResponseMeta(BaseModel):
    """Metadata for API responses"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    request_id: Optional[str] = None
    processing_time_ms: Optional[float] = None


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    
    Provides consistent structure for all API responses.
    """
    status: ResponseStatus
    message: Optional[str] = None
    data: Optional[T] = None
    meta: APIResponseMeta = Field(default_factory=APIResponseMeta)
    
    @classmethod
    def success(
        cls,
        data: T,
        message: Optional[str] = None,
        meta: Optional[APIResponseMeta] = None
    ) -> 'APIResponse[T]':
        """Create successful response"""
        return cls(
            status=ResponseStatus.SUCCESS,
            message=message or "Operation completed successfully",
            data=data,
            meta=meta or APIResponseMeta()
        )
    
    @classmethod
    def error(
        cls,
        message: str,
        data: Optional[T] = None,
        meta: Optional[APIResponseMeta] = None
    ) -> 'APIResponse[T]':
        """Create error response"""
        return cls(
            status=ResponseStatus.ERROR,
            message=message,
            data=data,
            meta=meta or APIResponseMeta()
        )
    
    @classmethod
    def warning(
        cls,
        message: str,
        data: Optional[T] = None,
        meta: Optional[APIResponseMeta] = None
    ) -> 'APIResponse[T]':
        """Create warning response"""
        return cls(
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            meta=meta or APIResponseMeta()
        )


class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str
    message: str
    field: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    status: ResponseStatus = ResponseStatus.ERROR
    message: str
    errors: List[ErrorDetail] = Field(default_factory=list)
    meta: APIResponseMeta = Field(default_factory=APIResponseMeta)
    
    def add_error(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Add error detail"""
        self.errors.append(ErrorDetail(
            code=code,
            message=message,
            field=field,
            context=context
        ))


class PaginationInfo(BaseModel):
    """Pagination information"""
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Number of items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    
    @validator('total_pages', always=True)
    def calculate_total_pages(cls, v, values):
        """Calculate total pages based on total items and page size"""
        total_items = values.get('total_items', 0)
        page_size = values.get('page_size', 1)
        return (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    @validator('has_next', always=True)
    def calculate_has_next(cls, v, values):
        """Calculate if there is a next page"""
        page = values.get('page', 1)
        total_pages = values.get('total_pages', 0)
        return page < total_pages
    
    @validator('has_previous', always=True)
    def calculate_has_previous(cls, v, values):
        """Calculate if there is a previous page"""
        page = values.get('page', 1)
        return page > 1


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper.
    
    Standardizes pagination across all API endpoints.
    """
    items: List[T]
    pagination: PaginationInfo
    
    @classmethod
    def create(
        cls,
        items: List[T],
        page: int,
        page_size: int,
        total_items: int
    ) -> 'PaginatedResponse[T]':
        """Create paginated response"""
        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=0,  # Will be calculated by validator
            has_next=False,  # Will be calculated by validator
            has_previous=False  # Will be calculated by validator
        )
        
        return cls(items=items, pagination=pagination)


class DataCollectionResult(BaseModel):
    """Result of data collection operation"""
    total_requested: int = Field(ge=0, description="Total items requested")
    total_collected: int = Field(ge=0, description="Total items successfully collected")
    total_saved: int = Field(ge=0, description="Total items saved to database")
    total_skipped: int = Field(ge=0, description="Total items skipped (duplicates)")
    total_errors: int = Field(ge=0, description="Total items with errors")
    success_rate: float = Field(ge=0, le=1, description="Success rate (0-1)")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    processing_time_seconds: Optional[float] = None
    
    @validator('success_rate', always=True)
    def calculate_success_rate(cls, v, values):
        """Calculate success rate"""
        total_requested = values.get('total_requested', 0)
        total_collected = values.get('total_collected', 0)
        if total_requested == 0:
            return 1.0
        return total_collected / total_requested


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceHealth(BaseModel):
    """Individual service health information"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Overall health check response"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    services: List[ServiceHealth] = Field(default_factory=list)
    uptime_seconds: Optional[float] = None
    
    def add_service_health(
        self,
        name: str,
        status: HealthStatus,
        message: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Add service health information"""
        self.services.append(ServiceHealth(
            name=name,
            status=status,
            message=message,
            response_time_ms=response_time_ms,
            details=details
        ))
        
        # Update overall status based on service statuses
        self._update_overall_status()
    
    def _update_overall_status(self):
        """Update overall health status based on service statuses"""
        if not self.services:
            self.status = HealthStatus.HEALTHY
            return
        
        unhealthy_count = sum(1 for s in self.services if s.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for s in self.services if s.status == HealthStatus.DEGRADED)
        
        if unhealthy_count > 0:
            self.status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY


class ValidationErrorDetail(BaseModel):
    """Validation error detail"""
    field: str
    message: str
    value: Any
    constraint: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    status: ResponseStatus = ResponseStatus.ERROR
    message: str = "Validation failed"
    validation_errors: List[ValidationErrorDetail]
    meta: APIResponseMeta = Field(default_factory=APIResponseMeta)


class FilterOption(BaseModel):
    """Filter option for search/query operations"""
    field: str
    operator: str = "eq"  # eq, ne, gt, gte, lt, lte, in, regex, exists
    value: Any
    case_sensitive: bool = False


class SortOption(BaseModel):
    """Sort option for query operations"""
    field: str
    direction: str = "asc"  # asc, desc
    
    @validator('direction')
    def validate_direction(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Direction must be "asc" or "desc"')
        return v


class QueryOptions(BaseModel):
    """Query options for search operations"""
    filters: List[FilterOption] = Field(default_factory=list)
    sorts: List[SortOption] = Field(default_factory=list)
    search_term: Optional[str] = None
    include_inactive: bool = False
    
    def add_filter(
        self,
        field: str,
        value: Any,
        operator: str = "eq",
        case_sensitive: bool = False
    ):
        """Add filter option"""
        self.filters.append(FilterOption(
            field=field,
            operator=operator,
            value=value,
            case_sensitive=case_sensitive
        ))
    
    def add_sort(self, field: str, direction: str = "asc"):
        """Add sort option"""
        self.sorts.append(SortOption(field=field, direction=direction))


class AuditInfo(BaseModel):
    """Audit information for data tracking"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True)
    metadata: Optional[Dict[str, Any]] = None


class DataSourceInfo(BaseModel):
    """Information about data source"""
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    last_sync: Optional[datetime] = None
    sync_status: Optional[str] = None
    total_records: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None