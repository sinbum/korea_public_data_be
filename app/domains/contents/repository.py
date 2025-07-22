"""
Content Repository implementation.

Implements Repository pattern for content data access with MongoDB.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ...core.interfaces.base_repository import BaseRepository, QueryFilter, SortOption, PaginationResult
from .models import Content, ContentCreate, ContentUpdate
from ...core.database import get_database
import logging

logger = logging.getLogger(__name__)


class ContentRepository(BaseRepository[Content, ContentCreate, ContentUpdate]):
    """Repository for content data access operations"""
    
    def __init__(self, db=None):
        """Initialize content repository"""
        super().__init__(db or get_database(), "contents")
    
    def _to_domain_model(self, doc: Dict[str, Any]) -> Content:
        """Convert MongoDB document to Content domain model"""
        # Convert ObjectId to string id
        doc = self._convert_objectid_to_string(doc)
        return Content(**doc)
    
    def _to_create_dict(self, create_model: ContentCreate) -> Dict[str, Any]:
        """Convert ContentCreate to MongoDB document"""
        doc = create_model.dict(by_alias=True, exclude={"id"})
        
        # Ensure is_active is set to True for new contents
        doc["is_active"] = True
        
        return doc
    
    def _to_update_dict(self, update_model: ContentUpdate) -> Dict[str, Any]:
        """Convert ContentUpdate to MongoDB update document"""
        # Only include non-None fields
        update_dict = {}
        for field, value in update_model.dict(exclude_unset=True).items():
            if value is not None:
                update_dict[field] = value
        
        return update_dict
    
    # Specialized query methods
    def find_by_content_id(self, content_id: str) -> Optional[Content]:
        """Find content by content ID"""
        try:
            filters = QueryFilter().eq("content_data.content_id", content_id).eq("is_active", True)
            results = self.get_all(filters=filters, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to find content by content_id {content_id}: {e}")
            return None
    
    def find_by_title(self, title: str) -> List[Content]:
        """Find contents by title (partial match)"""
        try:
            filters = QueryFilter().regex("content_data.title", title).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find contents by title {title}: {e}")
            return []
    
    def find_by_content_type(self, content_type: str) -> List[Content]:
        """Find contents by content type"""
        try:
            filters = QueryFilter().eq("content_data.content_type", content_type).eq("is_active", True)
            sort = SortOption().desc("content_data.published_date")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find contents by content_type {content_type}: {e}")
            return []
    
    def find_by_category(self, category: str) -> List[Content]:
        """Find contents by category"""
        try:
            filters = QueryFilter().eq("content_data.category", category).eq("is_active", True)
            sort = SortOption().desc("content_data.published_date")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find contents by category {category}: {e}")
            return []
    
    def find_by_tags(self, tags: List[str]) -> List[Content]:
        """Find contents by tags"""
        try:
            filters = QueryFilter().in_list("content_data.tags", tags).eq("is_active", True)
            sort = SortOption().desc("content_data.published_date")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find contents by tags {tags}: {e}")
            return []
    
    def find_active_contents(self, page: int = 1, page_size: int = 20) -> PaginationResult[Content]:
        """Get paginated active contents"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("content_data.published_date")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to get active contents: {e}")
            # Return empty pagination result on error
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def find_by_date_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Content]:
        """Find contents within date range"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            if start_date:
                filters.gte("content_data.published_date", start_date)
            
            if end_date:
                filters.lte("content_data.published_date", end_date)
            
            sort = SortOption().desc("content_data.published_date")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find contents by date range: {e}")
            return []
    
    def get_popular_contents(self, limit: int = 10) -> List[Content]:
        """Get most popular contents (by view count)"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("content_data.view_count")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get popular contents: {e}")
            return []
    
    def get_most_liked_contents(self, limit: int = 10) -> List[Content]:
        """Get most liked contents"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("content_data.like_count")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get most liked contents: {e}")
            return []
    
    def search_contents(
        self, 
        search_term: str,
        search_fields: List[str] = None
    ) -> List[Content]:
        """Search contents by term in multiple fields"""
        try:
            if search_fields is None:
                search_fields = [
                    "content_data.title",
                    "content_data.description",
                    "content_data.category",
                    "content_data.tags"
                ]
            
            # Build OR query for multiple fields
            or_conditions = []
            for field in search_fields:
                if field == "content_data.tags":
                    # For array fields, use $in operator
                    or_conditions.append({field: {"$in": [search_term]}})
                else:
                    or_conditions.append({field: {"$regex": search_term, "$options": "i"}})
            
            # Use raw MongoDB query for complex OR conditions
            query = {
                "$and": [
                    {"is_active": True},
                    {"$or": or_conditions}
                ]
            }
            
            cursor = self.collection.find(query).sort("content_data.published_date", -1)
            return [self._to_domain_model(doc) for doc in cursor]
            
        except Exception as e:
            logger.error(f"Failed to search contents with term '{search_term}': {e}")
            return []
    
    def get_recent_contents(self, limit: int = 10) -> List[Content]:
        """Get most recent contents"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("content_data.published_date")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent contents: {e}")
            return []
    
    def check_duplicate(self, content_id: str = None, title: str = None) -> bool:
        """Check if content already exists"""
        try:
            if content_id:
                filters = QueryFilter().eq("content_data.content_id", content_id).eq("is_active", True)
                return self.exists(filters)
            
            if title:
                filters = QueryFilter().eq("content_data.title", title).eq("is_active", True)
                return self.exists(filters)
            
            return False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False
    
    def bulk_create_contents(self, contents: List[ContentCreate]) -> List[Content]:
        """Bulk create contents"""
        try:
            return self.create_many(contents)
        except Exception as e:
            logger.error(f"Failed to bulk create contents: {e}")
            return []
    
    def increment_view_count(self, content_id: str) -> bool:
        """Increment view count for content"""
        try:
            result = self.collection.update_one(
                {
                    "content_data.content_id": content_id,
                    "is_active": True
                },
                {
                    "$inc": {"content_data.view_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to increment view count for content_id {content_id}: {e}")
            return False
    
    def increment_like_count(self, content_id: str) -> bool:
        """Increment like count for content"""
        try:
            result = self.collection.update_one(
                {
                    "content_data.content_id": content_id,
                    "is_active": True
                },
                {
                    "$inc": {"content_data.like_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to increment like count for content_id {content_id}: {e}")
            return False
    
    def get_contents_by_filter(
        self,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_view_count: Optional[int] = None,
        min_like_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginationResult[Content]:
        """Get contents by multiple filter criteria"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            if content_type:
                filters.eq("content_data.content_type", content_type)
            
            if category:
                filters.eq("content_data.category", category)
            
            if tags:
                filters.in_list("content_data.tags", tags)
            
            if min_view_count is not None:
                filters.gte("content_data.view_count", min_view_count)
            
            if min_like_count is not None:
                filters.gte("content_data.like_count", min_like_count)
            
            sort = SortOption().desc("content_data.published_date")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
            
        except Exception as e:
            logger.error(f"Failed to get contents by filter: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get content statistics"""
        try:
            total_count = self.count()
            active_count = self.count(QueryFilter().eq("is_active", True))
            
            # Count by content type
            content_type_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$content_data.content_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            content_type_counts = {}
            for result in self.collection.aggregate(content_type_pipeline):
                content_type_counts[result["_id"] or "unknown"] = result["count"]
            
            # Count by category
            category_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$content_data.category",
                    "count": {"$sum": 1}
                }}
            ]
            
            category_counts = {}
            for result in self.collection.aggregate(category_pipeline):
                category_counts[result["_id"] or "unknown"] = result["count"]
            
            # Get total views and likes
            aggregation_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": None,
                    "total_views": {"$sum": "$content_data.view_count"},
                    "total_likes": {"$sum": "$content_data.like_count"},
                    "avg_views": {"$avg": "$content_data.view_count"},
                    "avg_likes": {"$avg": "$content_data.like_count"}
                }}
            ]
            
            engagement_stats = list(self.collection.aggregate(aggregation_pipeline))
            engagement = engagement_stats[0] if engagement_stats else {
                "total_views": 0,
                "total_likes": 0,
                "avg_views": 0,
                "avg_likes": 0
            }
            
            return {
                "total_contents": total_count,
                "active_contents": active_count,
                "inactive_contents": total_count - active_count,
                "content_type_breakdown": content_type_counts,
                "category_breakdown": category_counts,
                "total_views": engagement.get("total_views", 0),
                "total_likes": engagement.get("total_likes", 0),
                "avg_views_per_content": round(engagement.get("avg_views", 0), 2),
                "avg_likes_per_content": round(engagement.get("avg_likes", 0), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get content statistics: {e}")
            return {
                "total_contents": 0,
                "active_contents": 0,
                "inactive_contents": 0,
                "content_type_breakdown": {},
                "category_breakdown": {},
                "total_views": 0,
                "total_likes": 0,
                "avg_views_per_content": 0,
                "avg_likes_per_content": 0
            }