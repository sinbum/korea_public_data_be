"""
Repository interface definitions.

Provides abstract interfaces for data access layer following Repository pattern.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Protocol, Optional, List, Dict, Any, Union
from pydantic import BaseModel

# Type variables
T = TypeVar('T', bound=BaseModel)  # Domain model type
FilterT = TypeVar('FilterT')  # Filter type
SortT = TypeVar('SortT')  # Sort type


class IRepository(Protocol[T]):
    """
    Base repository interface using Protocol for duck typing.
    
    Defines the contract for basic CRUD operations.
    """
    
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID."""
        ...
    
    async def create(self, item_data: T) -> Dict[str, Any]:
        """Create new item."""
        ...
    
    async def update(self, item_id: str, item_data: T) -> Optional[Dict[str, Any]]:
        """Update existing item."""
        ...
    
    async def delete(self, item_id: str) -> bool:
        """Delete item by ID."""
        ...
    
    async def exists(self, item_id: str) -> bool:
        """Check if item exists."""
        ...


class IQueryableRepository(IRepository[T], Protocol):
    """
    Extended repository interface with querying capabilities.
    
    Adds support for filtering, sorting, and pagination.
    """
    
    async def get_list(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get paginated list with filtering and sorting."""
        ...
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count items matching filters."""
        ...
    
    async def find_by_field(self, field_name: str, field_value: Any) -> List[Dict[str, Any]]:
        """Find items by specific field value."""
        ...
    
    async def find_one_by_field(self, field_name: str, field_value: Any) -> Optional[Dict[str, Any]]:
        """Find single item by specific field value."""
        ...


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository implementation.
    
    Provides common patterns and utilities for repository implementations.
    """
    
    def __init__(self, collection_name: str, database=None, logger=None):
        """
        Initialize repository with database dependencies.
        
        Args:
            collection_name: Name of the database collection/table
            database: Database connection instance
            logger: Logger instance
        """
        self._collection_name = collection_name
        self._database = database
        self._logger = logger
    
    @property
    def collection_name(self) -> str:
        """Get collection name."""
        return self._collection_name
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID from storage."""
        pass
    
    @abstractmethod
    async def create(self, item_data: T) -> Dict[str, Any]:
        """Create new item in storage."""
        pass
    
    @abstractmethod
    async def update(self, item_id: str, item_data: T) -> Optional[Dict[str, Any]]:
        """Update existing item in storage."""
        pass
    
    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete item from storage."""
        pass
    
    @abstractmethod
    async def get_list(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get paginated list from storage."""
        pass
    
    async def exists(self, item_id: str) -> bool:
        """
        Check if item exists by ID.
        
        Default implementation using get_by_id.
        Can be overridden for performance optimization.
        """
        result = await self.get_by_id(item_id)
        return result is not None
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count items matching filters.
        
        Default implementation using get_list.
        Should be overridden for performance optimization.
        """
        _, total = await self.get_list(offset=0, limit=1, filters=filters)
        return total
    
    # Utility methods for subclasses
    def _validate_id(self, item_id: str) -> None:
        """Validate item ID format."""
        if not item_id or not isinstance(item_id, str) or len(item_id.strip()) == 0:
            raise ValueError("유효하지 않은 ID입니다.")
    
    def _validate_pagination_params(self, offset: int, limit: int) -> None:
        """Validate pagination parameters."""
        if offset < 0:
            raise ValueError("오프셋은 0 이상이어야 합니다.")
        if limit < 1 or limit > 100:
            raise ValueError("제한값은 1-100 사이여야 합니다.")
    
    def _sanitize_filters(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sanitize filter parameters."""
        if not filters:
            return {}
        
        # Remove None values and empty strings
        sanitized = {}
        for key, value in filters.items():
            if value is not None and value != "":
                # Handle special filter operators
                if isinstance(value, dict):
                    # Handle MongoDB-style operators like {"$gte": value}
                    sanitized[key] = value
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _build_sort_criteria(self, sort_by: Optional[str], sort_order: str) -> Optional[Dict[str, int]]:
        """Build sort criteria for database query."""
        if not sort_by:
            return None
        
        # Normalize sort order
        order = 1 if sort_order.lower() in ["asc", "ascending", "1"] else -1
        
        return {sort_by: order}
    
    def _convert_objectid_to_string(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert MongoDB ObjectId to string.
        
        Utility method for MongoDB repositories.
        """
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc
    
    def _log_info(self, message: str, **kwargs) -> None:
        """Log info message if logger is available."""
        if self._logger:
            self._logger.info(f"[{self._collection_name}] {message}", extra=kwargs)
    
    def _log_error(self, message: str, **kwargs) -> None:
        """Log error message if logger is available."""
        if self._logger:
            self._logger.error(f"[{self._collection_name}] {message}", extra=kwargs)
    
    def _log_warning(self, message: str, **kwargs) -> None:
        """Log warning message if logger is available."""
        if self._logger:
            self._logger.warning(f"[{self._collection_name}] {message}", extra=kwargs)


class MongoRepository(BaseRepository[T]):
    """
    MongoDB-specific repository implementation.
    
    Provides MongoDB-specific query building and data handling.
    """
    
    def __init__(self, collection_name: str, database=None, logger=None):
        super().__init__(collection_name, database, logger)
        self._collection = None
        if database:
            self._collection = database[collection_name]
    
    @property
    def collection(self):
        """Get MongoDB collection instance."""
        if self._collection is None and self._database is not None:
            self._collection = self._database[self._collection_name]
        return self._collection
    
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID from MongoDB."""
        self._validate_id(item_id)
        
        try:
            from bson import ObjectId
            doc = self.collection.find_one({"_id": ObjectId(item_id)})
            if doc:
                return self._convert_objectid_to_string(doc)
            return None
        except Exception as e:
            self._log_error(f"Error getting item by ID {item_id}: {e}")
            return None
    
    async def create(self, item_data: T) -> Dict[str, Any]:
        """Create new item in MongoDB."""
        try:
            # Convert Pydantic model to dict
            if hasattr(item_data, 'model_dump'):
                doc_data = item_data.model_dump(exclude_unset=True)
            else:
                doc_data = item_data.dict(exclude_unset=True)
            
            # Add timestamp
            from datetime import datetime
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            
            # Insert document
            result = self.collection.insert_one(doc_data)
            
            # Return created document
            created_doc = self.collection.find_one({"_id": result.inserted_id})
            return self._convert_objectid_to_string(created_doc)
            
        except Exception as e:
            self._log_error(f"Error creating item: {e}")
            raise
    
    async def update(self, item_id: str, item_data: T) -> Optional[Dict[str, Any]]:
        """Update existing item in MongoDB."""
        self._validate_id(item_id)
        
        try:
            from bson import ObjectId
            
            # Convert Pydantic model to dict
            if hasattr(item_data, 'model_dump'):
                update_data = item_data.model_dump(exclude_unset=True)
            else:
                update_data = item_data.dict(exclude_unset=True)
            
            # Add update timestamp
            from datetime import datetime
            update_data["updated_at"] = datetime.utcnow()
            
            # Update document
            result = self.collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                return None
            
            # Return updated document
            updated_doc = self.collection.find_one({"_id": ObjectId(item_id)})
            return self._convert_objectid_to_string(updated_doc)
            
        except Exception as e:
            self._log_error(f"Error updating item {item_id}: {e}")
            return None
    
    async def delete(self, item_id: str) -> bool:
        """Delete item from MongoDB."""
        self._validate_id(item_id)
        
        try:
            from bson import ObjectId
            result = self.collection.delete_one({"_id": ObjectId(item_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            self._log_error(f"Error deleting item {item_id}: {e}")
            return False
    
    async def get_list(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get paginated list from MongoDB."""
        self._validate_pagination_params(offset, limit)
        
        try:
            # Build MongoDB query
            query = self._build_mongo_query(filters)
            sort_criteria = self._build_sort_criteria(sort_by, sort_order)
            
            # Execute query with pagination
            cursor = self.collection.find(query)
            
            if sort_criteria:
                cursor = cursor.sort(list(sort_criteria.items()))
            
            # Get total count
            total_count = self.collection.count_documents(query)
            
            # Apply pagination
            cursor = cursor.skip(offset).limit(limit)
            
            # Convert results
            items = []
            for doc in cursor:
                items.append(self._convert_objectid_to_string(doc))
            
            return items, total_count
            
        except Exception as e:
            self._log_error(f"Error getting list: {e}")
            return [], 0
    
    def _build_mongo_query(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build MongoDB query from filters."""
        if not filters:
            return {}
        
        query = {}
        sanitized_filters = self._sanitize_filters(filters)
        
        for key, value in sanitized_filters.items():
            if isinstance(value, dict):
                # Handle operators like {"$gte": value}
                query[key] = value
            elif isinstance(value, str) and len(value) > 0:
                # Text search with regex for partial matching
                query[key] = {"$regex": value, "$options": "i"}
            else:
                # Exact match
                query[key] = value
        
        return query