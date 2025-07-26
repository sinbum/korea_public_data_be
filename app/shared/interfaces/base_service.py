"""
Base service interface and abstract implementation.

Provides common service patterns and abstractions following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import (
    TypeVar, Generic, Protocol, Optional, List, Dict, Any, 
    Union, Callable, Awaitable
)
from pydantic import BaseModel
from datetime import datetime

from ..schemas import PaginatedResponse, PaginationMeta
from ..exceptions import DataValidationError, KoreanPublicAPIError

# Type variables for generic implementations
T = TypeVar('T', bound=BaseModel)  # Domain model type
CreateT = TypeVar('CreateT', bound=BaseModel)  # Create request type
UpdateT = TypeVar('UpdateT', bound=BaseModel)  # Update request type
ResponseT = TypeVar('ResponseT', bound=BaseModel)  # Response type


class IBaseService(Protocol[T, CreateT, UpdateT, ResponseT]):
    """
    Base service interface using Protocol for duck typing.
    
    Defines the contract that all domain services should implement.
    """
    
    async def get_by_id(self, item_id: str) -> Optional[ResponseT]:
        """ID로 단일 항목 조회"""
        ...
    
    async def get_list(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> PaginatedResponse[ResponseT]:
        """페이지네이션된 목록 조회"""
        ...
    
    async def create(self, create_data: CreateT) -> ResponseT:
        """새 항목 생성"""
        ...
    
    async def update(self, item_id: str, update_data: UpdateT) -> Optional[ResponseT]:
        """기존 항목 업데이트"""
        ...
    
    async def delete(self, item_id: str) -> bool:
        """항목 삭제"""
        ...
    
    async def exists(self, item_id: str) -> bool:
        """항목 존재 여부 확인"""
        ...


class BaseService(ABC, Generic[T, CreateT, UpdateT, ResponseT]):
    """
    Base service abstract class implementing common patterns.
    
    Provides template methods and common functionality for domain services.
    Uses Template Method pattern for extensible business logic.
    """
    
    def __init__(self, repository=None, logger=None):
        """
        Initialize base service with dependencies.
        
        Args:
            repository: Data access repository
            logger: Logger instance
        """
        self._repository = repository
        self._logger = logger
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    # Template method pattern - defines the algorithm structure
    async def get_by_id(self, item_id: str) -> Optional[ResponseT]:
        """
        Get single item by ID with validation and transformation.
        
        Template method that can be extended by subclasses.
        """
        # Pre-processing hook
        await self._before_get_by_id(item_id)
        
        # Validation
        self._validate_id(item_id)
        
        # Data retrieval
        raw_data = await self._fetch_by_id(item_id)
        if not raw_data:
            return None
        
        # Post-processing and transformation
        result = await self._transform_to_response(raw_data)
        
        # Post-processing hook
        await self._after_get_by_id(item_id, result)
        
        return result
    
    async def get_list(
        self,
        page: int = 1,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> PaginatedResponse[ResponseT]:
        """
        Get paginated list with filtering and sorting.
        
        Template method with extensible filtering logic.
        """
        # Pre-processing hook
        await self._before_get_list(page, limit, filters, sort_by, sort_order)
        
        # Validation
        self._validate_pagination_params(page, limit)
        filters = self._sanitize_filters(filters or {})
        
        # Build query
        query_params = await self._build_query_params(filters, sort_by, sort_order)
        
        # Data retrieval
        items, total_count = await self._fetch_list(page, limit, query_params)
        
        # Transform items
        response_items = []
        for item in items:
            transformed = await self._transform_to_response(item)
            if transformed:
                response_items.append(transformed)
        
        # Build pagination metadata
        total_pages = (total_count + limit - 1) // limit
        meta = PaginationMeta(
            page=page,
            limit=limit,
            total=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        result = PaginatedResponse[ResponseT](
            success=True,
            message="조회 성공",
            data=response_items,
            meta=meta
        )
        
        # Post-processing hook
        await self._after_get_list(result)
        
        return result
    
    async def create(self, create_data: CreateT) -> ResponseT:
        """
        Create new item with validation and business logic.
        
        Template method with validation and transformation hooks.
        """
        # Pre-processing hook
        await self._before_create(create_data)
        
        # Validation
        await self._validate_create_data(create_data)
        
        # Business logic validation
        await self._validate_business_rules_for_create(create_data)
        
        # Transform to domain model
        domain_data = await self._transform_to_domain(create_data)
        
        # Persist data
        created_item = await self._save_new_item(domain_data)
        
        # Transform to response
        result = await self._transform_to_response(created_item)
        
        # Post-processing hook and events
        await self._after_create(result)
        await self._emit_event("item_created", result)
        
        return result
    
    async def update(self, item_id: str, update_data: UpdateT) -> Optional[ResponseT]:
        """
        Update existing item with validation and business logic.
        
        Template method with comprehensive validation.
        """
        # Pre-processing hook
        await self._before_update(item_id, update_data)
        
        # Validation
        self._validate_id(item_id)
        await self._validate_update_data(update_data)
        
        # Check existence
        existing_item = await self._fetch_by_id(item_id)
        if not existing_item:
            return None
        
        # Business logic validation
        await self._validate_business_rules_for_update(item_id, update_data, existing_item)
        
        # Transform and merge
        update_domain_data = await self._transform_to_domain(update_data)
        merged_data = await self._merge_update_data(existing_item, update_domain_data)
        
        # Persist changes
        updated_item = await self._save_updated_item(item_id, merged_data)
        
        # Transform to response
        result = await self._transform_to_response(updated_item)
        
        # Post-processing hook and events
        await self._after_update(item_id, result)
        await self._emit_event("item_updated", {"id": item_id, "data": result})
        
        return result
    
    async def delete(self, item_id: str) -> bool:
        """
        Delete item with validation and cleanup.
        
        Template method with soft delete support.
        """
        # Pre-processing hook
        await self._before_delete(item_id)
        
        # Validation
        self._validate_id(item_id)
        
        # Check existence
        existing_item = await self._fetch_by_id(item_id)
        if not existing_item:
            return False
        
        # Business logic validation
        await self._validate_business_rules_for_delete(item_id, existing_item)
        
        # Perform deletion
        success = await self._delete_item(item_id)
        
        if success:
            # Post-processing hook and events
            await self._after_delete(item_id)
            await self._emit_event("item_deleted", {"id": item_id})
        
        return success
    
    async def exists(self, item_id: str) -> bool:
        """Check if item exists by ID."""
        self._validate_id(item_id)
        return await self._check_existence(item_id)
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch raw data by ID from repository."""
        pass
    
    @abstractmethod
    async def _fetch_list(
        self, 
        page: int, 
        limit: int, 
        query_params: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int]:
        """Fetch paginated list and total count from repository."""
        pass
    
    @abstractmethod
    async def _save_new_item(self, domain_data: T) -> Dict[str, Any]:
        """Save new item to repository."""
        pass
    
    @abstractmethod
    async def _save_updated_item(self, item_id: str, domain_data: T) -> Dict[str, Any]:
        """Save updated item to repository."""
        pass
    
    @abstractmethod
    async def _delete_item(self, item_id: str) -> bool:
        """Delete item from repository."""
        pass
    
    @abstractmethod
    async def _transform_to_response(self, raw_data: Dict[str, Any]) -> ResponseT:
        """Transform raw data to response model."""
        pass
    
    @abstractmethod
    async def _transform_to_domain(self, input_data: Union[CreateT, UpdateT]) -> T:
        """Transform input data to domain model."""
        pass
    
    # Hook methods that can be overridden by subclasses
    async def _before_get_by_id(self, item_id: str) -> None:
        """Hook called before get_by_id operation."""
        pass
    
    async def _after_get_by_id(self, item_id: str, result: Optional[ResponseT]) -> None:
        """Hook called after get_by_id operation."""
        pass
    
    async def _before_get_list(self, page: int, limit: int, filters: Optional[Dict[str, Any]], sort_by: Optional[str], sort_order: str) -> None:
        """Hook called before get_list operation."""
        pass
    
    async def _after_get_list(self, result: PaginatedResponse[ResponseT]) -> None:
        """Hook called after get_list operation."""
        pass
    
    async def _before_create(self, create_data: CreateT) -> None:
        """Hook called before create operation."""
        pass
    
    async def _after_create(self, result: ResponseT) -> None:
        """Hook called after create operation."""
        pass
    
    async def _before_update(self, item_id: str, update_data: UpdateT) -> None:
        """Hook called before update operation."""
        pass
    
    async def _after_update(self, item_id: str, result: ResponseT) -> None:
        """Hook called after update operation."""
        pass
    
    async def _before_delete(self, item_id: str) -> None:
        """Hook called before delete operation."""
        pass
    
    async def _after_delete(self, item_id: str) -> None:
        """Hook called after delete operation."""
        pass
    
    # Validation methods that can be overridden
    def _validate_id(self, item_id: str) -> None:
        """Validate item ID format."""
        if not item_id or not isinstance(item_id, str) or len(item_id.strip()) == 0:
            raise DataValidationError("유효하지 않은 ID입니다.", field_name="id")
    
    def _validate_pagination_params(self, page: int, limit: int) -> None:
        """Validate pagination parameters."""
        if page < 1:
            raise DataValidationError("페이지 번호는 1 이상이어야 합니다.", field_name="page")
        if limit < 1 or limit > 100:
            raise DataValidationError("페이지 크기는 1-100 사이여야 합니다.", field_name="limit")
    
    def _sanitize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and validate filter parameters."""
        # Remove None values and empty strings
        return {k: v for k, v in filters.items() if v is not None and v != ""}
    
    async def _validate_create_data(self, create_data: CreateT) -> None:
        """Validate create data. Override in subclasses for domain-specific validation."""
        pass
    
    async def _validate_update_data(self, update_data: UpdateT) -> None:
        """Validate update data. Override in subclasses for domain-specific validation."""
        pass
    
    async def _validate_business_rules_for_create(self, create_data: CreateT) -> None:
        """Validate business rules for create operation."""
        pass
    
    async def _validate_business_rules_for_update(self, item_id: str, update_data: UpdateT, existing_item: Dict[str, Any]) -> None:
        """Validate business rules for update operation."""
        pass
    
    async def _validate_business_rules_for_delete(self, item_id: str, existing_item: Dict[str, Any]) -> None:
        """Validate business rules for delete operation."""
        pass
    
    # Utility methods
    async def _build_query_params(self, filters: Dict[str, Any], sort_by: Optional[str], sort_order: str) -> Dict[str, Any]:
        """Build query parameters for repository. Override in subclasses."""
        return {
            "filters": filters,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    
    async def _merge_update_data(self, existing_item: Dict[str, Any], update_data: T) -> T:
        """Merge update data with existing item. Override in subclasses."""
        return update_data
    
    async def _check_existence(self, item_id: str) -> bool:
        """Check if item exists. Default implementation using fetch_by_id."""
        result = await self._fetch_by_id(item_id)
        return result is not None
    
    # Event handling methods
    def _register_event_handler(self, event_name: str, handler: Callable) -> None:
        """Register event handler for domain events."""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
    
    async def _emit_event(self, event_name: str, data: Any) -> None:
        """Emit domain event to registered handlers."""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    if callable(handler):
                        if hasattr(handler, '__call__') and hasattr(handler.__call__, '__annotations__'):
                            # Check if handler is async
                            import inspect
                            if inspect.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"Error in event handler {event_name}: {e}")
    
    # Logging helper methods
    def _log_info(self, message: str, **kwargs) -> None:
        """Log info message if logger is available."""
        if self._logger:
            self._logger.info(message, extra=kwargs)
    
    def _log_error(self, message: str, **kwargs) -> None:
        """Log error message if logger is available."""
        if self._logger:
            self._logger.error(message, extra=kwargs)
    
    def _log_warning(self, message: str, **kwargs) -> None:
        """Log warning message if logger is available."""
        if self._logger:
            self._logger.warning(message, extra=kwargs)