"""
Base Service interface implementing service layer patterns.

Provides abstract business logic layer with common operations and error handling.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Union
from pydantic import BaseModel, ValidationError
import logging
from datetime import datetime

from .base_repository import BaseRepository, QueryFilter, SortOption, PaginationResult
from .base_api_client import BaseAPIClient, APIResponse

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)  # Domain model
CreateT = TypeVar('CreateT', bound=BaseModel)  # Create DTO
UpdateT = TypeVar('UpdateT', bound=BaseModel)  # Update DTO
ResponseT = TypeVar('ResponseT', bound=BaseModel)  # Response DTO


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class ValidationError(ServiceError):
    """Validation error in service layer"""
    pass


class NotFoundError(ServiceError):
    """Resource not found error"""
    pass


class ConflictError(ServiceError):
    """Resource conflict error"""
    pass


class ExternalServiceError(ServiceError):
    """External service error"""
    pass


class ServiceResult(Generic[T]):
    """Service operation result wrapper"""
    
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        errors: Optional[List[str]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.errors = errors or []
    
    @classmethod
    def success_result(cls, data: T) -> 'ServiceResult[T]':
        """Create successful result"""
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, error: str, errors: Optional[List[str]] = None) -> 'ServiceResult[T]':
        """Create error result"""
        return cls(success=False, error=error, errors=errors)


class BaseService(ABC, Generic[T, CreateT, UpdateT, ResponseT]):
    """
    Abstract base service implementing business logic patterns.
    
    Provides common CRUD operations with validation, transformation,
    and error handling.
    """
    
    def __init__(
        self,
        repository: BaseRepository[T, CreateT, UpdateT],
        api_client: Optional[BaseAPIClient] = None
    ):
        self.repository = repository
        self.api_client = api_client
    
    # Abstract methods for data transformation
    @abstractmethod
    def _to_response_model(self, domain_model: T) -> ResponseT:
        """Convert domain model to response DTO"""
        pass
    
    @abstractmethod
    def _validate_create_data(self, create_data: CreateT) -> List[str]:
        """Validate create data, return list of error messages"""
        pass
    
    @abstractmethod
    def _validate_update_data(self, update_data: UpdateT) -> List[str]:
        """Validate update data, return list of error messages"""
        pass
    
    # Business logic hooks (optional to override)
    def _before_create(self, create_data: CreateT) -> CreateT:
        """Hook executed before create operation"""
        return create_data
    
    def _after_create(self, created_item: T) -> T:
        """Hook executed after create operation"""
        return created_item
    
    def _before_update(self, id_value: str, update_data: UpdateT) -> UpdateT:
        """Hook executed before update operation"""
        return update_data
    
    def _after_update(self, updated_item: T) -> T:
        """Hook executed after update operation"""
        return updated_item
    
    def _before_delete(self, id_value: str) -> None:
        """Hook executed before delete operation"""
        pass
    
    def _after_delete(self, id_value: str) -> None:
        """Hook executed after delete operation"""
        pass
    
    # CRUD operations with business logic
    def create(self, create_data: CreateT) -> ServiceResult[ResponseT]:
        """Create new item with validation and business logic"""
        try:
            # Validate input data
            validation_errors = self._validate_create_data(create_data)
            if validation_errors:
                return ServiceResult.error_result(
                    "Validation failed",
                    validation_errors
                )
            
            # Execute before-create hook
            create_data = self._before_create(create_data)
            
            # Create via repository
            created_item = self.repository.create(create_data)
            
            # Execute after-create hook
            created_item = self._after_create(created_item)
            
            # Transform to response model
            response_model = self._to_response_model(created_item)
            
            return ServiceResult.success_result(response_model)
            
        except Exception as e:
            logger.error(f"Create operation failed: {e}")
            return ServiceResult.error_result(f"Create operation failed: {str(e)}")
    
    def get_by_id(self, id_value: str) -> ServiceResult[ResponseT]:
        """Get item by ID"""
        try:
            item = self.repository.get_by_id(id_value)
            if not item:
                return ServiceResult.error_result("Item not found")
            
            response_model = self._to_response_model(item)
            return ServiceResult.success_result(response_model)
            
        except Exception as e:
            logger.error(f"Get by ID operation failed: {e}")
            return ServiceResult.error_result(f"Get operation failed: {str(e)}")
    
    def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> ServiceResult[List[ResponseT]]:
        """Get all items with optional filtering and sorting"""
        try:
            # Build query filter
            query_filter = QueryFilter()
            if filters:
                for key, value in filters.items():
                    if isinstance(value, str):
                        query_filter.regex(key, value)  # Enable partial matching for strings
                    else:
                        query_filter.eq(key, value)
            
            # Build sort option
            sort_option = None
            if sort_by:
                sort_option = SortOption()
                if sort_desc:
                    sort_option.desc(sort_by)
                else:
                    sort_option.asc(sort_by)
            
            # Get items from repository
            items = self.repository.get_all(
                filters=query_filter,
                sort=sort_option,
                skip=skip,
                limit=limit
            )
            
            # Transform to response models
            response_models = [self._to_response_model(item) for item in items]
            
            return ServiceResult.success_result(response_models)
            
        except Exception as e:
            logger.error(f"Get all operation failed: {e}")
            return ServiceResult.error_result(f"Get all operation failed: {str(e)}")
    
    def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> ServiceResult[PaginationResult[ResponseT]]:
        """Get paginated items"""
        try:
            # Build query filter
            query_filter = QueryFilter()
            if filters:
                for key, value in filters.items():
                    if isinstance(value, str):
                        query_filter.regex(key, value)
                    else:
                        query_filter.eq(key, value)
            
            # Build sort option
            sort_option = None
            if sort_by:
                sort_option = SortOption()
                if sort_desc:
                    sort_option.desc(sort_by)
                else:
                    sort_option.asc(sort_by)
            
            # Get paginated items from repository
            pagination_result = self.repository.get_paginated(
                page=page,
                page_size=page_size,
                filters=query_filter,
                sort=sort_option
            )
            
            # Transform items to response models
            response_items = [self._to_response_model(item) for item in pagination_result.items]
            
            # Create new pagination result with transformed items
            response_pagination = PaginationResult(
                items=response_items,
                total_count=pagination_result.total_count,
                page=pagination_result.page,
                page_size=pagination_result.page_size,
                has_next=pagination_result.has_next,
                has_previous=pagination_result.has_previous
            )
            
            return ServiceResult.success_result(response_pagination)
            
        except Exception as e:
            logger.error(f"Get paginated operation failed: {e}")
            return ServiceResult.error_result(f"Pagination operation failed: {str(e)}")
    
    def update(self, id_value: str, update_data: UpdateT) -> ServiceResult[ResponseT]:
        """Update item with validation and business logic"""
        try:
            # Check if item exists
            existing_item = self.repository.get_by_id(id_value)
            if not existing_item:
                return ServiceResult.error_result("Item not found")
            
            # Validate input data
            validation_errors = self._validate_update_data(update_data)
            if validation_errors:
                return ServiceResult.error_result(
                    "Validation failed",
                    validation_errors
                )
            
            # Execute before-update hook
            update_data = self._before_update(id_value, update_data)
            
            # Update via repository
            updated_item = self.repository.update_by_id(id_value, update_data)
            if not updated_item:
                return ServiceResult.error_result("Update failed")
            
            # Execute after-update hook
            updated_item = self._after_update(updated_item)
            
            # Transform to response model
            response_model = self._to_response_model(updated_item)
            
            return ServiceResult.success_result(response_model)
            
        except Exception as e:
            logger.error(f"Update operation failed: {e}")
            return ServiceResult.error_result(f"Update operation failed: {str(e)}")
    
    def delete(self, id_value: str, soft_delete: bool = True) -> ServiceResult[bool]:
        """Delete item with business logic"""
        try:
            # Check if item exists
            existing_item = self.repository.get_by_id(id_value)
            if not existing_item:
                return ServiceResult.error_result("Item not found")
            
            # Execute before-delete hook
            self._before_delete(id_value)
            
            # Delete via repository
            success = self.repository.delete_by_id(id_value, soft_delete=soft_delete)
            if not success:
                return ServiceResult.error_result("Delete operation failed")
            
            # Execute after-delete hook
            self._after_delete(id_value)
            
            return ServiceResult.success_result(True)
            
        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return ServiceResult.error_result(f"Delete operation failed: {str(e)}")
    
    # External API integration methods
    def fetch_from_external_api(self, **kwargs) -> ServiceResult[List[ResponseT]]:
        """Fetch data from external API and optionally save to repository"""
        try:
            if not self.api_client:
                return ServiceResult.error_result("External API client not configured")
            
            # Make API request
            api_response = self._make_api_request(**kwargs)
            if not api_response.success:
                return ServiceResult.error_result(f"External API error: {api_response.error}")
            
            # Process and save data if needed
            processed_items = self._process_external_data(api_response.data)
            
            return ServiceResult.success_result(processed_items)
            
        except Exception as e:
            logger.error(f"External API fetch failed: {e}")
            return ServiceResult.error_result(f"External API fetch failed: {str(e)}")
    
    @abstractmethod
    def _make_api_request(self, **kwargs) -> APIResponse:
        """Make specific API request (must be implemented by subclasses)"""
        pass
    
    @abstractmethod
    def _process_external_data(self, external_data: Any) -> List[ResponseT]:
        """Process external API data (must be implemented by subclasses)"""
        pass
    
    # Utility methods
    def exists(self, filters: Dict[str, Any]) -> bool:
        """Check if item exists with given filters"""
        try:
            query_filter = QueryFilter()
            for key, value in filters.items():
                query_filter.eq(key, value)
            
            return self.repository.exists(query_filter)
        except Exception as e:
            logger.error(f"Exists check failed: {e}")
            return False
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count items with optional filters"""
        try:
            query_filter = None
            if filters:
                query_filter = QueryFilter()
                for key, value in filters.items():
                    query_filter.eq(key, value)
            
            return self.repository.count(query_filter)
        except Exception as e:
            logger.error(f"Count operation failed: {e}")
            return 0