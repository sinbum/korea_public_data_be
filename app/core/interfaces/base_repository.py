"""
Base Repository interface implementing Repository pattern.

Provides abstract data access layer with MongoDB-specific implementation support.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Union
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)


class RepositoryError(Exception):
    """Base exception for repository errors"""
    pass


class QueryFilter:
    """Query filter builder for flexible filtering"""
    
    def __init__(self):
        self.filters: Dict[str, Any] = {}
    
    def eq(self, field: str, value: Any) -> 'QueryFilter':
        """Equal filter"""
        self.filters[field] = value
        return self
    
    def ne(self, field: str, value: Any) -> 'QueryFilter':
        """Not equal filter"""
        self.filters[field] = {"$ne": value}
        return self
    
    def gt(self, field: str, value: Any) -> 'QueryFilter':
        """Greater than filter"""
        self.filters[field] = {"$gt": value}
        return self
    
    def gte(self, field: str, value: Any) -> 'QueryFilter':
        """Greater than or equal filter"""
        self.filters[field] = {"$gte": value}
        return self
    
    def lt(self, field: str, value: Any) -> 'QueryFilter':
        """Less than filter"""
        self.filters[field] = {"$lt": value}
        return self
    
    def lte(self, field: str, value: Any) -> 'QueryFilter':
        """Less than or equal filter"""
        self.filters[field] = {"$lte": value}
        return self
    
    def in_list(self, field: str, values: List[Any]) -> 'QueryFilter':
        """In list filter"""
        self.filters[field] = {"$in": values}
        return self
    
    def regex(self, field: str, pattern: str, options: str = "i") -> 'QueryFilter':
        """Regex filter"""
        self.filters[field] = {"$regex": pattern, "$options": options}
        return self
    
    def exists(self, field: str, exists: bool = True) -> 'QueryFilter':
        """Field exists filter"""
        self.filters[field] = {"$exists": exists}
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB query dict"""
        return self.filters


class SortOption:
    """Sort option builder"""
    
    def __init__(self):
        self.sorts: List[tuple] = []
    
    def asc(self, field: str) -> 'SortOption':
        """Ascending sort"""
        self.sorts.append((field, 1))
        return self
    
    def desc(self, field: str) -> 'SortOption':
        """Descending sort"""
        self.sorts.append((field, -1))
        return self
    
    def to_list(self) -> List[tuple]:
        """Convert to MongoDB sort list"""
        return self.sorts


class PaginationResult(Generic[T]):
    """Pagination result wrapper"""
    
    def __init__(
        self,
        items: List[T],
        total_count: int,
        page: int,
        page_size: int,
        has_next: bool,
        has_previous: bool
    ):
        self.items = items
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.has_next = has_next
        self.has_previous = has_previous
    
    @property
    def total_pages(self) -> int:
        """Calculate total pages"""
        return (self.total_count + self.page_size - 1) // self.page_size
    
    def to_pagination_meta(self) -> Dict[str, Any]:
        """Convert to pagination metadata dictionary"""
        return {
            "total": self.total_count,
            "page": self.page,
            "size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous
        }


class BaseRepository(ABC, Generic[T, CreateT, UpdateT]):
    """
    Abstract base repository implementing Repository pattern.
    
    Provides common CRUD operations with MongoDB-specific optimizations.
    """
    
    def __init__(self, db: Database, collection_name: str):
        self.db = db
        self.collection: Collection = db[collection_name]
        self.collection_name = collection_name
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def _to_domain_model(self, doc: Dict[str, Any]) -> T:
        """Convert MongoDB document to domain model"""
        pass
    
    @abstractmethod
    def _to_create_dict(self, create_model: CreateT) -> Dict[str, Any]:
        """Convert create model to MongoDB document"""
        pass
    
    @abstractmethod
    def _to_update_dict(self, update_model: UpdateT) -> Dict[str, Any]:
        """Convert update model to MongoDB update document"""
        pass
    
    # Common CRUD operations
    def create(self, create_model: CreateT) -> T:
        """Create new document"""
        try:
            doc = self._to_create_dict(create_model)
            doc["created_at"] = datetime.utcnow()
            doc["updated_at"] = datetime.utcnow()
            
            result = self.collection.insert_one(doc)
            
            # Retrieve the created document
            created_doc = self.collection.find_one({"_id": result.inserted_id})
            if not created_doc:
                raise RepositoryError("Failed to retrieve created document")
            
            return self._to_domain_model(created_doc)
            
        except Exception as e:
            logger.error(f"Failed to create document in {self.collection_name}: {e}")
            raise RepositoryError(f"Create operation failed: {e}")
    
    def get_by_id(self, id_value: Union[str, ObjectId]) -> Optional[T]:
        """Get document by ID"""
        try:
            if isinstance(id_value, str):
                id_value = ObjectId(id_value)
            
            doc = self.collection.find_one({"_id": id_value})
            if doc:
                return self._to_domain_model(doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by ID in {self.collection_name}: {e}")
            return None
    
    def get_all(
        self,
        filters: Optional[QueryFilter] = None,
        sort: Optional[SortOption] = None,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[T]:
        """Get all documents with optional filtering and pagination"""
        try:
            query = filters.to_dict() if filters else {}
            cursor = self.collection.find(query)
            
            if sort:
                cursor = cursor.sort(sort.to_list())
            
            if skip > 0:
                cursor = cursor.skip(skip)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return [self._to_domain_model(doc) for doc in cursor]
            
        except Exception as e:
            logger.error(f"Failed to get documents in {self.collection_name}: {e}")
            raise RepositoryError(f"Query operation failed: {e}")
    
    def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[QueryFilter] = None,
        sort: Optional[SortOption] = None
    ) -> PaginationResult[T]:
        """Get paginated documents"""
        try:
            query = filters.to_dict() if filters else {}
            
            # Get total count
            total_count = self.collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * page_size
            has_previous = page > 1
            has_next = skip + page_size < total_count
            
            # Get documents
            cursor = self.collection.find(query)
            
            if sort:
                cursor = cursor.sort(sort.to_list())
            
            cursor = cursor.skip(skip).limit(page_size)
            items = [self._to_domain_model(doc) for doc in cursor]
            
            return PaginationResult(
                items=items,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=has_next,
                has_previous=has_previous
            )
            
        except Exception as e:
            logger.error(f"Failed to get paginated documents in {self.collection_name}: {e}")
            raise RepositoryError(f"Pagination operation failed: {e}")
    
    def update_by_id(self, id_value: Union[str, ObjectId], update_model: UpdateT) -> Optional[T]:
        """Update document by ID"""
        try:
            if isinstance(id_value, str):
                id_value = ObjectId(id_value)
            
            update_dict = self._to_update_dict(update_model)
            if not update_dict:
                return self.get_by_id(id_value)  # No changes
            
            update_dict["updated_at"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"_id": id_value},
                {"$set": update_dict}
            )
            
            if result.modified_count > 0:
                return self.get_by_id(id_value)
            return None
            
        except Exception as e:
            logger.error(f"Failed to update document in {self.collection_name}: {e}")
            raise RepositoryError(f"Update operation failed: {e}")
    
    def delete_by_id(self, id_value: Union[str, ObjectId], soft_delete: bool = True) -> bool:
        """Delete document by ID (soft delete by default)"""
        try:
            if isinstance(id_value, str):
                id_value = ObjectId(id_value)
            
            if soft_delete:
                # Soft delete by setting is_active to False
                result = self.collection.update_one(
                    {"_id": id_value},
                    {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
                )
                return result.modified_count > 0
            else:
                # Hard delete
                result = self.collection.delete_one({"_id": id_value})
                return result.deleted_count > 0
                
        except Exception as e:
            logger.error(f"Failed to delete document in {self.collection_name}: {e}")
            raise RepositoryError(f"Delete operation failed: {e}")
    
    def exists(self, filters: QueryFilter) -> bool:
        """Check if document exists"""
        try:
            query = filters.to_dict()
            return self.collection.count_documents(query, limit=1) > 0
        except Exception as e:
            logger.error(f"Failed to check existence in {self.collection_name}: {e}")
            return False
    
    def count(self, filters: Optional[QueryFilter] = None) -> int:
        """Count documents"""
        try:
            query = filters.to_dict() if filters else {}
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count documents in {self.collection_name}: {e}")
            return 0
    
    # Utility methods
    def _convert_objectid_to_string(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB _id to string id field"""
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc
    
    def _prepare_update_dict(self, update_model: UpdateT) -> Dict[str, Any]:
        """Prepare update dictionary, excluding None values"""
        update_dict = update_model.dict(exclude_unset=True)
        return {k: v for k, v in update_dict.items() if v is not None}
    
    # Batch operations
    def create_many(self, create_models: List[CreateT]) -> List[T]:
        """Create multiple documents"""
        try:
            docs = []
            now = datetime.utcnow()
            
            for model in create_models:
                doc = self._to_create_dict(model)
                doc["created_at"] = now
                doc["updated_at"] = now
                docs.append(doc)
            
            result = self.collection.insert_many(docs)
            
            # Retrieve created documents
            created_docs = self.collection.find({"_id": {"$in": result.inserted_ids}})
            return [self._to_domain_model(doc) for doc in created_docs]
            
        except Exception as e:
            logger.error(f"Failed to create multiple documents in {self.collection_name}: {e}")
            raise RepositoryError(f"Bulk create operation failed: {e}")