"""
Announcement Repository implementation.

Implements Repository pattern for announcement data access with MongoDB.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo.database import Database
from ...core.interfaces.base_repository import BaseRepository, QueryFilter, SortOption, PaginationResult
from .models import Announcement, AnnouncementCreate, AnnouncementUpdate
from ...core.database import get_database
import logging

logger = logging.getLogger(__name__)


class AnnouncementRepository(BaseRepository[Announcement, AnnouncementCreate, AnnouncementUpdate]):
    """Repository for announcement data access operations"""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize announcement repository"""
        super().__init__(db if db is not None else get_database(), "announcements")
    
    def _to_domain_model(self, doc: Dict[str, Any]) -> Announcement:
        """Convert MongoDB document to Announcement domain model"""
        # Convert ObjectId to string id
        doc = self._convert_objectid_to_string(doc)
        return Announcement(**doc)
    
    def _to_create_dict(self, create_model: AnnouncementCreate) -> Dict[str, Any]:
        """Convert AnnouncementCreate to MongoDB document"""
        doc = create_model.dict(by_alias=True, exclude={"id"})
        
        # Ensure is_active is set to True for new announcements
        doc["is_active"] = True
        
        return doc
    
    def _to_update_dict(self, update_model: AnnouncementUpdate) -> Dict[str, Any]:
        """Convert AnnouncementUpdate to MongoDB update document"""
        # Only include non-None fields
        update_dict = {}
        for field, value in update_model.dict(exclude_unset=True).items():
            if value is not None:
                update_dict[field] = value
        
        return update_dict
    
    # Specialized query methods
    def find_by_business_id(self, business_id: str) -> Optional[Announcement]:
        """Find announcement by business ID"""
        try:
            filters = QueryFilter().eq("announcement_data.business_id", business_id).eq("is_active", True)
            results = self.get_all(filters=filters, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to find announcement by business_id {business_id}: {e}")
            return None
    
    def find_by_business_name(self, business_name: str) -> List[Announcement]:
        """Find announcements by business name (partial match)"""
        try:
            filters = QueryFilter().regex("announcement_data.business_name", business_name).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find announcements by business_name {business_name}: {e}")
            return []
    
    def find_by_business_type(self, business_type: str) -> List[Announcement]:
        """Find announcements by business type"""
        try:
            filters = QueryFilter().eq("announcement_data.business_type", business_type).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find announcements by business_type {business_type}: {e}")
            return []
    
    def find_active_announcements(self, page: int = 1, page_size: int = 20) -> PaginationResult[Announcement]:
        """Get paginated active announcements"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to get active announcements: {e}")
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
    ) -> List[Announcement]:
        """Find announcements within date range"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            if start_date:
                filters.gte("announcement_data.announcement_date", start_date)
            
            if end_date:
                filters.lte("announcement_data.announcement_date", end_date)
            
            sort = SortOption().desc("announcement_data.announcement_date")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find announcements by date range: {e}")
            return []
    
    def find_by_status(self, status: str) -> List[Announcement]:
        """Find announcements by status"""
        try:
            filters = QueryFilter().eq("announcement_data.status", status).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find announcements by status {status}: {e}")
            return []
    
    def search_announcements(
        self, 
        search_term: str,
        search_fields: List[str] = None
    ) -> List[Announcement]:
        """Search announcements by term in multiple fields"""
        try:
            if search_fields is None:
                search_fields = [
                    "announcement_data.business_name",
                    "announcement_data.business_overview",
                    "announcement_data.support_target"
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
            logger.error(f"Failed to search announcements with term '{search_term}': {e}")
            return []
    
    async def create_many(self, creates: List[AnnouncementCreate]) -> List[Announcement]:
        """대량 공고 생성 (벌크 삽입)"""
        if not creates:
            return []
            
        try:
            # 벌크 삽입을 위한 문서 준비
            documents = []
            now = datetime.utcnow()
            
            for create in creates:
                doc = {
                    **create.announcement_data,
                    "source_url": create.source_url,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now
                }
                documents.append(doc)
            
            # 벌크 삽입 실행
            result = self.collection.insert_many(documents, ordered=False)
            logger.info(f"벌크 삽입 완료: {len(result.inserted_ids)}개 문서")
            
            # 생성된 문서들 조회하여 반환
            created_announcements = []
            for doc_id in result.inserted_ids:
                doc = self.collection.find_one({"_id": doc_id})
                if doc:
                    created_announcements.append(self._to_domain_model(doc))
            
            return created_announcements
            
        except Exception as e:
            logger.error(f"벌크 삽입 실패: {e}")
            # 실패 시 개별 삽입 시도
            return await self._fallback_individual_create(creates)
    
    async def _fallback_individual_create(self, creates: List[AnnouncementCreate]) -> List[Announcement]:
        """벌크 삽입 실패 시 개별 삽입 폴백"""
        created_announcements = []
        
        for create in creates:
            try:
                announcement = self.create(create)
                created_announcements.append(announcement)
            except Exception as e:
                logger.warning(f"개별 삽입 실패: {e}")
                continue
        
        return created_announcements
    
    async def count_all(self) -> int:
        """전체 공고 수 조회"""
        try:
            return self.collection.count_documents({"is_active": True})
        except Exception as e:
            logger.error(f"전체 개수 조회 실패: {e}")
            return 0
    
    async def count_recent(self, days: int = 7) -> int:
        """최근 N일간 공고 수 조회"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = {
                "is_active": True,
                "created_at": {"$gte": cutoff_date}
            }
            
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"최근 개수 조회 실패: {e}")
            return 0

    def get_recent_announcements(self, limit: int = 10) -> List[Announcement]:
        """Get most recent announcements"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent announcements: {e}")
            return []
    
    def check_duplicate(self, business_id: str = None, business_name: str = None) -> bool:
        """Check if announcement already exists"""
        try:
            if business_id:
                filters = QueryFilter().eq("announcement_data.business_id", business_id).eq("is_active", True)
                return self.exists(filters)
            
            if business_name:
                filters = QueryFilter().eq("announcement_data.business_name", business_name).eq("is_active", True)
                return self.exists(filters)
            
            return False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False
    
    def bulk_create_announcements(self, announcements: List[AnnouncementCreate]) -> List[Announcement]:
        """Bulk create announcements"""
        try:
            return self.create_many(announcements)
        except Exception as e:
            logger.error(f"Failed to bulk create announcements: {e}")
            return []
    
    def update_status_by_business_id(self, business_id: str, status: str) -> bool:
        """Update announcement status by business ID"""
        try:
            result = self.collection.update_one(
                {
                    "announcement_data.business_id": business_id,
                    "is_active": True
                },
                {
                    "$set": {
                        "announcement_data.status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update status for business_id {business_id}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, int]:
        """Get announcement statistics"""
        try:
            total_count = self.count()
            active_count = self.count(QueryFilter().eq("is_active", True))
            
            # Count by status
            pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$announcement_data.status",
                    "count": {"$sum": 1}
                }}
            ]
            
            status_counts = {}
            for result in self.collection.aggregate(pipeline):
                status_counts[result["_id"] or "unknown"] = result["count"]
            
            return {
                "total_announcements": total_count,
                "active_announcements": active_count,
                "inactive_announcements": total_count - active_count,
                "status_breakdown": status_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get announcement statistics: {e}")
            return {
                "total_announcements": 0,
                "active_announcements": 0,
                "inactive_announcements": 0,
                "status_breakdown": {}
            }