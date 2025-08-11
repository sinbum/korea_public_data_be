"""
Statistics Repository implementation.

Implements Repository pattern for statistics data access with MongoDB.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo.database import Database

from ...core.interfaces.base_repository import BaseRepository, QueryFilter, SortOption, PaginationResult
from .models import Statistics, StatisticsCreate, StatisticsUpdate
from ...core.database import get_database
import logging

logger = logging.getLogger(__name__)


class StatisticsRepository(BaseRepository[Statistics, StatisticsCreate, StatisticsUpdate]):
    """Repository for statistics data access operations"""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize statistics repository"""
        super().__init__(db if db is not None else get_database(), "statistics")
    
    def _to_domain_model(self, doc: Dict[str, Any]) -> Statistics:
        """Convert MongoDB document to Statistics domain model"""
        # Convert ObjectId to string id
        doc = self._convert_objectid_to_string(doc)
        return Statistics(**doc)
    
    def _to_create_dict(self, create_model: StatisticsCreate) -> Dict[str, Any]:
        """Convert StatisticsCreate to MongoDB document"""
        doc = create_model.dict(by_alias=True, exclude={"id"})
        
        # Ensure is_active is set to True for new statistics
        doc["is_active"] = True
        
        return doc
    
    def _to_update_dict(self, update_model: StatisticsUpdate) -> Dict[str, Any]:
        """Convert StatisticsUpdate to MongoDB update document"""
        # Only include non-None fields
        update_dict = {}
        for field, value in update_model.dict(exclude_unset=True).items():
            if value is not None:
                update_dict[field] = value
        
        return update_dict
    
    # Specialized query methods
    def find_by_stat_id(self, stat_id: str) -> Optional[Statistics]:
        """Find statistics by stat ID"""
        try:
            filters = QueryFilter().eq("statistical_data.stat_id", stat_id).eq("is_active", True)
            results = self.get_all(filters=filters, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to find statistics by stat_id {stat_id}: {e}")
            return None
    
    def find_by_stat_name(self, stat_name: str) -> List[Statistics]:
        """Find statistics by stat name (partial match)"""
        try:
            filters = QueryFilter().regex("statistical_data.stat_name", stat_name).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by stat_name {stat_name}: {e}")
            return []
    
    def find_by_stat_type(self, stat_type: str) -> List[Statistics]:
        """Find statistics by stat type"""
        try:
            filters = QueryFilter().eq("statistical_data.stat_type", stat_type).eq("is_active", True)
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by stat_type {stat_type}: {e}")
            return []
    
    def find_by_year(self, year: int) -> List[Statistics]:
        """Find statistics by year"""
        try:
            filters = QueryFilter().eq("statistical_data.year", year).eq("is_active", True)
            sort = SortOption().desc("statistical_data.month")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by year {year}: {e}")
            return []
    
    def find_by_year_month(self, year: int, month: int) -> List[Statistics]:
        """Find statistics by year and month"""
        try:
            filters = QueryFilter().eq("statistical_data.year", year).eq("statistical_data.month", month).eq("is_active", True)
            sort = SortOption().desc("created_at")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by year {year} month {month}: {e}")
            return []
    
    def find_by_period(self, period: str) -> List[Statistics]:
        """Find statistics by period"""
        try:
            filters = QueryFilter().eq("statistical_data.period", period).eq("is_active", True)
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by period {period}: {e}")
            return []
    
    def find_active_statistics(self, page: int = 1, page_size: int = 20) -> PaginationResult[Statistics]:
        """Get paginated active statistics"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to get active statistics: {e}")
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
        start_year: int,
        start_month: int = 1,
        end_year: Optional[int] = None,
        end_month: Optional[int] = None
    ) -> List[Statistics]:
        """Find statistics within date range"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            # Start date filter
            start_date_value = start_year * 100 + start_month  # YYYYMM format
            filters.gte("statistical_data.year", start_year)
            
            # End date filter if provided
            if end_year is not None:
                if end_month is not None:
                    end_date_value = end_year * 100 + end_month
                    filters.lte("statistical_data.year", end_year)
                else:
                    filters.lte("statistical_data.year", end_year)
            
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_all(filters=filters, sort=sort)
        except Exception as e:
            logger.error(f"Failed to find statistics by date range: {e}")
            return []
    
    def search_statistics(
        self, 
        search_term: str,
        search_fields: List[str] = None
    ) -> List[Statistics]:
        """Search statistics by term in multiple fields"""
        try:
            if search_fields is None:
                search_fields = [
                    "statistical_data.stat_name",
                    "statistical_data.stat_type",
                    "statistical_data.period"
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
            
            cursor = self.collection.find(query).sort([("statistical_data.year", -1), ("statistical_data.month", -1)])
            return [self._to_domain_model(doc) for doc in cursor]
            
        except Exception as e:
            logger.error(f"Failed to search statistics with term '{search_term}': {e}")
            return []
    
    def get_recent_statistics(self, limit: int = 10) -> List[Statistics]:
        """Get most recent statistics"""
        try:
            filters = QueryFilter().eq("is_active", True)
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_all(filters=filters, sort=sort, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent statistics: {e}")
            return []
    
    def check_duplicate(self, stat_id: str = None, stat_name: str = None, year: int = None, month: int = None) -> bool:
        """Check if statistics already exists"""
        try:
            if stat_id:
                filters = QueryFilter().eq("statistical_data.stat_id", stat_id).eq("is_active", True)
                return self.exists(filters)
            
            if stat_name and year and month:
                filters = QueryFilter().eq("statistical_data.stat_name", stat_name)\
                                     .eq("statistical_data.year", year)\
                                     .eq("statistical_data.month", month)\
                                     .eq("is_active", True)
                return self.exists(filters)
            
            return False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False
    
    def bulk_create_statistics(self, statistics_list: List[StatisticsCreate]) -> List[Statistics]:
        """Bulk create statistics"""
        try:
            return self.create_many(statistics_list)
        except Exception as e:
            logger.error(f"Failed to bulk create statistics: {e}")
            return []
    
    def get_statistics_by_filter(
        self,
        stat_type: Optional[str] = None,
        period: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        min_total_count: Optional[int] = None,
        min_success_rate: Optional[float] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginationResult[Statistics]:
        """Get statistics by multiple filter criteria"""
        try:
            filters = QueryFilter().eq("is_active", True)
            
            if stat_type:
                filters.eq("statistical_data.stat_type", stat_type)
            
            if period:
                filters.eq("statistical_data.period", period)
            
            if year is not None:
                filters.eq("statistical_data.year", year)
            
            if month is not None:
                filters.eq("statistical_data.month", month)
            
            if min_total_count is not None:
                filters.gte("statistical_data.total_count", min_total_count)
            
            if min_success_rate is not None:
                filters.gte("statistical_data.success_rate", min_success_rate)
            
            sort = SortOption().desc("statistical_data.year").desc("statistical_data.month")
            return self.get_paginated(page=page, page_size=page_size, filters=filters, sort=sort)
            
        except Exception as e:
            logger.error(f"Failed to get statistics by filter: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_aggregated_metrics(
        self,
        stat_type: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics for statistics"""
        try:
            match_criteria = {"is_active": True}
            
            if stat_type:
                match_criteria["statistical_data.stat_type"] = stat_type
            
            if year:
                match_criteria["statistical_data.year"] = year
            
            pipeline = [
                {"$match": match_criteria},
                {"$group": {
                    "_id": None,
                    "total_records": {"$sum": 1},
                    "total_count_sum": {"$sum": "$statistical_data.total_count"},
                    "success_count_sum": {"$sum": "$statistical_data.success_count"},
                    "avg_success_rate": {"$avg": "$statistical_data.success_rate"},
                    "max_total_count": {"$max": "$statistical_data.total_count"},
                    "min_total_count": {"$min": "$statistical_data.total_count"}
                }}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                aggregated = result[0]
                return {
                    "total_records": aggregated.get("total_records", 0),
                    "total_count_sum": aggregated.get("total_count_sum", 0),
                    "success_count_sum": aggregated.get("success_count_sum", 0),
                    "avg_success_rate": round(aggregated.get("avg_success_rate", 0), 2),
                    "max_total_count": aggregated.get("max_total_count", 0),
                    "min_total_count": aggregated.get("min_total_count", 0)
                }
            else:
                return {
                    "total_records": 0,
                    "total_count_sum": 0,
                    "success_count_sum": 0,
                    "avg_success_rate": 0,
                    "max_total_count": 0,
                    "min_total_count": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get aggregated metrics: {e}")
            return {}
    
    def get_statistics_overview(self) -> Dict[str, Any]:
        """Get statistics overview and breakdown"""
        try:
            total_count = self.count()
            active_count = self.count(QueryFilter().eq("is_active", True))
            
            # Count by stat type
            stat_type_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$statistical_data.stat_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            stat_type_counts = {}
            for result in self.collection.aggregate(stat_type_pipeline):
                stat_type_counts[result["_id"] or "unknown"] = result["count"]
            
            # Count by period
            period_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$statistical_data.period",
                    "count": {"$sum": 1}
                }}
            ]
            
            period_counts = {}
            for result in self.collection.aggregate(period_pipeline):
                period_counts[result["_id"] or "unknown"] = result["count"]
            
            # Count by year
            year_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {
                    "_id": "$statistical_data.year",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": -1}},
                {"$limit": 5}  # Last 5 years
            ]
            
            year_counts = {}
            for result in self.collection.aggregate(year_pipeline):
                year_counts[str(result["_id"]) if result["_id"] else "unknown"] = result["count"]
            
            return {
                "total_statistics": total_count,
                "active_statistics": active_count,
                "inactive_statistics": total_count - active_count,
                "stat_type_breakdown": stat_type_counts,
                "period_breakdown": period_counts,
                "year_breakdown": year_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics overview: {e}")
            return {
                "total_statistics": 0,
                "active_statistics": 0,
                "inactive_statistics": 0,
                "stat_type_breakdown": {},
                "period_breakdown": {},
                "year_breakdown": {}
            }