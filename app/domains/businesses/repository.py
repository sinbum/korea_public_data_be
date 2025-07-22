"""
Business Repository implementation.

Implements Repository pattern for business data access with MongoDB.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ...core.interfaces.base_repository import BaseRepository, QueryFilter, SortOption, PaginationResult
from .models import Business, BusinessCreate, BusinessUpdate
from ...core.database import get_database
import logging

logger = logging.getLogger(__name__)


class BusinessRepository(BaseRepository[Business, BusinessCreate, BusinessUpdate]):
    """Repository for business data access operations"""
    
    def __init__(self, db=None):
        """Initialize business repository"""
        super().__init__(db or get_database(), "businesses")
    
    def _to_domain_model(self, doc: Dict[str, Any]) -> Business:
        """Convert MongoDB document to Business domain model"""
        # Convert ObjectId to string id
        doc = self._convert_objectid_to_string(doc)
        return Business(**doc)
    
    def _to_create_dict(self, create_model: BusinessCreate) -> Dict[str, Any]:
        """Convert BusinessCreate to MongoDB document"""
        doc = create_model.dict(by_alias=True, exclude={"id"})
        
        # Ensure is_active is set to True for new businesses
        doc["is_active"] = True
        
        return doc
    
    def _to_update_dict(self, update_model: BusinessUpdate) -> Dict[str, Any]:
        """Convert BusinessUpdate to MongoDB update document"""
        # Only include non-None fields
        update_dict = {}
        for field, value in update_model.dict(exclude_unset=True).items():
            if value is not None:
                update_dict[field] = value
        
        return update_dict
    
    # Specialized query methods
    def find_by_business_id(self, business_id: str) -> Optional[Business]:
        """Find business by business ID"""
        try:
            filters = QueryFilter().eq("business_data.business_id", business_id).eq("is_active", True)
            results = self.get_all(filters=filters, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to find business by business_id {business_id}: {e}")
            return None
    
    def find_by_business_name(self, business_name: str) -> List[Business]:
        """Find businesses by business name (partial match)"""
        try:
            filters = QueryFilter().regex("business_data.business_name", business_name).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find businesses by business_name {business_name}: {e}")
            return []
    
    def find_by_business_type(self, business_type: str) -> List[Business]:
        """Find businesses by business type"""
        try:
            filters = QueryFilter().eq("business_data.business_type", business_type).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find businesses by business_type {business_type}: {e}")
            return []
    
    def find_by_organization(self, organization: str) -> List[Business]:
        """Find businesses by organization"""
        try:
            filters = QueryFilter().eq("business_data.organization", organization).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find businesses by organization {organization}: {e}")
            return []
    
    def find_by_business_field(self, business_field: str) -> List[Business]:
        """Find businesses by business field"""
        try:
            filters = QueryFilter().eq("business_data.business_field", business_field).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find businesses by business_field {business_field}: {e}")
            return []
    
    def find_by_startup_stage(self, startup_stage: str) -> List[Business]:
        """Find businesses by target startup stage"""
        try:
            filters = QueryFilter().eq("business_data.target_startup_stage", startup_stage).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find businesses by startup_stage {startup_stage}: {e}")
            return []
    
    def find_active_businesses(self, page: int = 1, page_size: int = 20) -> PaginationResult[Business]:
        """Get paginated active businesses"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to get active businesses: {e}")
            # Return empty pagination result on error
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def search_businesses(
        self, 
        search_term: str,
        search_fields: List[str] = None
    ) -> List[Business]:
        """Search businesses by term in multiple fields"""
        try:
            if search_fields is None:
                search_fields = [
                    "business_data.business_name",
                    "business_data.description",
                    "business_data.organization",
                    "business_data.business_field"
                ]
            
            # Build OR query for multiple fields
            or_conditions = []
            for field in search_fields:
                or_conditions.append({field: {"$regex": search_term, "$options": "i"}})
            
            # Use raw MongoDB query for complex OR conditions
            query = {
                "$and": [
                    {"is_active": True},
                    {"$or": or_conditions}
                ]
            }
            
            cursor = self.collection.find(query).sort("created_at", -1)
            return [self._to_domain_model(doc) for doc in cursor]
            
        except Exception as e:
            logger.error(f"Failed to search businesses with term '{search_term}': {e}")
            return []
    
    def get_recent_businesses(self, limit: int = 10) -> List[Business]:
        """Get most recent businesses"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent businesses: {e}")
            return []
    
    def check_duplicate(self, business_id: str = None, business_name: str = None) -> bool:
        """Check if business already exists"""
        try:
            if business_id:
                filters = QueryFilter().eq("business_data.business_id", business_id).eq("is_active", True)
                return self.exists(filters)
            
            if business_name:
                filters = QueryFilter().eq("business_data.business_name", business_name).eq("is_active", True)
                return self.exists(filters)
            
            return False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False
    
    def bulk_create_businesses(self, businesses: List[BusinessCreate]) -> List[Business]:
        """Bulk create businesses"""
        try:
            return self.create_many(businesses)
        except Exception as e:
            logger.error(f"Failed to bulk create businesses: {e}")
            return []
    
    def get_businesses_by_filter(
        self,
        business_type: Optional[str] = None,
        organization: Optional[str] = None,
        business_field: Optional[str] = None,
        startup_stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginationResult[Business]:
        """Get businesses by multiple filter criteria"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            if business_type:
                filters.eq("business_data.business_type", business_type)
            
            if organization:
                filters.eq("business_data.organization", organization)
            
            if business_field:
                filters.eq("business_data.business_field", business_field)
            
            if startup_stage:
                filters.eq("business_data.target_startup_stage", startup_stage)
            
            sort = SortOption().desc("created_at")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
            
        except Exception as e:
            logger.error(f"Failed to get businesses by filter: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get business statistics"""
        try:
            total_count = self.count()
            active_count = self.count(QueryFilter().eq("is_active", True))
            
            # Count by business type
            business_type_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$business_data.business_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            business_type_counts = {}
            for result in self.collection.aggregate(business_type_pipeline):
                business_type_counts[result["_id"] or "unknown"] = result["count"]
            
            # Count by organization
            organization_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$business_data.organization",
                    "count": {"$sum": 1}
                }}
            ]
            
            organization_counts = {}
            for result in self.collection.aggregate(organization_pipeline):
                organization_counts[result["_id"] or "unknown"] = result["count"]
            
            # Count by business field
            business_field_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$business_data.business_field",
                    "count": {"$sum": 1}
                }}
            ]
            
            business_field_counts = {}
            for result in self.collection.aggregate(business_field_pipeline):
                business_field_counts[result["_id"] or "unknown"] = result["count"]
            
            return {
                "total_businesses": total_count,
                "active_businesses": active_count,
                "inactive_businesses": total_count - active_count,
                "business_type_breakdown": business_type_counts,
                "organization_breakdown": organization_counts,
                "business_field_breakdown": business_field_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get business statistics: {e}")
            return {
                "total_businesses": 0,
                "active_businesses": 0,
                "inactive_businesses": 0,
                "business_type_breakdown": {},
                "organization_breakdown": {},
                "business_field_breakdown": {}
            }