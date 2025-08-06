from typing import Optional, List, Dict, Any
from datetime import datetime
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

from ...shared.pagination import PaginationParams, PaginatedResponse, create_paginated_response
from ...core.database import get_database
from .models import DataRequest, DataRequestData, CategoryDocument, VoteDocument, DataRequestStatus, VoteType
from .schemas import DataRequestFilters


class DataRequestRepository:
    """데이터 요청 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
        self.collection: Collection = self.db["data_requests"]
    
    async def find_by_filters(
        self,
        filters: DataRequestFilters,
        pagination: PaginationParams,
        user_id: Optional[str] = None
    ) -> PaginatedResponse[DataRequest]:
        """필터와 페이지네이션을 적용한 데이터 요청 조회"""
        query = {"is_active": True}
        
        # 필터 적용
        if filters.category:
            query["data.category_id"] = filters.category
        
        if filters.status:
            query["data.status"] = filters.status.value
        
        if filters.priority:
            query["data.priority"] = filters.priority.value
        
        if filters.search:
            search_query = {
                "$or": [
                    {"data.title": {"$regex": filters.search, "$options": "i"}},
                    {"data.description": {"$regex": filters.search, "$options": "i"}},
                    {"data.tags": {"$in": [filters.search]}},
                ]
            }
            query.update(search_query)
        
        if filters.tags:
            query["data.tags"] = {"$in": filters.tags}
        
        if filters.user_id:
            query["data.user_id"] = filters.user_id
        
        # 정렬 설정
        sort_mapping = {
            "likes": [("data.vote_count", -1), ("created_at", -1)],
            "newest": [("created_at", -1)],
            "oldest": [("created_at", 1)],
            "priority": [("data.priority", -1), ("created_at", -1)]
        }
        sort_order = sort_mapping.get(filters.sort, sort_mapping["likes"])
        
        return await self._find_paginated(query, pagination, sort_order)
    
    async def find_popular(self, limit: int = 10) -> List[DataRequest]:
        """인기 데이터 요청 조회"""
        query = {"is_active": True}
        sort_order = [("data.vote_count", -1), ("created_at", -1)]
        
        cursor = self.collection.find(query).sort(sort_order).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        return [self.model_class(**doc) for doc in documents]
    
    async def find_by_user(
        self,
        user_id: str,
        pagination: PaginationParams
    ) -> PaginatedResponse[DataRequest]:
        """사용자의 데이터 요청 조회"""
        query = {"is_active": True, "data.user_id": user_id}
        sort_order = [("created_at", -1)]
        
        return await self.find_paginated(query, pagination, sort_order)
    
    async def find_by_status(
        self,
        status: DataRequestStatus,
        pagination: PaginationParams
    ) -> PaginatedResponse[DataRequest]:
        """상태별 데이터 요청 조회"""
        query = {"is_active": True, "data.status": status.value}
        sort_order = [("created_at", -1)]
        
        return await self.find_paginated(query, pagination, sort_order)
    
    async def update_vote_count(self, request_id: str, vote_count: int, likes_count: int, dislikes_count: int) -> bool:
        """투표 수 업데이트"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(request_id)},
                {
                    "$set": {
                        "data.vote_count": vote_count,
                        "data.likes_count": likes_count,
                        "data.dislikes_count": dislikes_count,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def update_status(
        self,
        request_id: str,
        status: DataRequestStatus,
        admin_notes: Optional[str] = None,
        estimated_completion: Optional[datetime] = None
    ) -> bool:
        """상태 업데이트 (관리자용)"""
        try:
            update_data = {
                "data.status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if admin_notes is not None:
                update_data["data.admin_notes"] = admin_notes
            
            if estimated_completion is not None:
                update_data["data.estimated_completion"] = estimated_completion
            
            if status == DataRequestStatus.COMPLETED:
                update_data["data.actual_completion"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """데이터 요청 통계 조회"""
        pipeline = [
            {"$match": {"is_active": True}},
            {
                "$group": {
                    "_id": "$data.status",
                    "count": {"$sum": 1},
                    "total_votes": {"$sum": "$data.vote_count"}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        status_counts = {doc["_id"]: doc for doc in await cursor.to_list(length=None)}
        
        # 카테고리별 통계
        category_pipeline = [
            {"$match": {"is_active": True}},
            {
                "$group": {
                    "_id": "$data.category_id",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = self.collection.aggregate(category_pipeline)
        category_counts = await cursor.to_list(length=None)
        
        total_requests = sum(doc["count"] for doc in status_counts.values())
        total_votes = sum(doc["total_votes"] for doc in status_counts.values())
        
        return {
            "total_requests": total_requests,
            "pending_requests": status_counts.get("pending", {}).get("count", 0),
            "under_review_requests": status_counts.get("under_review", {}).get("count", 0),
            "in_progress_requests": status_counts.get("in_progress", {}).get("count", 0),
            "completed_requests": status_counts.get("completed", {}).get("count", 0),
            "rejected_requests": status_counts.get("rejected", {}).get("count", 0),
            "total_votes": total_votes,
            "requests_by_category": {doc["_id"]: doc["count"] for doc in category_counts}
        }
    
    async def search_by_text(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        pagination: PaginationParams = None
    ) -> PaginatedResponse[DataRequest]:
        """텍스트 검색"""
        search_query = {
            "$text": {"$search": query},
            "is_active": True
        }
        
        if filters:
            search_query.update(filters)
        
        # 검색 점수 기준 정렬
        sort_order = [("score", {"$meta": "textScore"})]
        
        if pagination:
            return await self.find_paginated(search_query, pagination, sort_order)
        else:
            cursor = self.collection.find(search_query).sort(sort_order)
            documents = await cursor.to_list(length=None)
            items = [self.model_class(**doc) for doc in documents]
            return create_paginated_response(items, len(items), 1, len(items))


class CategoryRepository:
    """카테고리 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
        self.collection: Collection = self.db["categories"]
    
    async def find_by_name(self, name: str) -> Optional[CategoryDocument]:
        """이름으로 카테고리 조회"""
        query = {"data.name": name, "is_active": True}
        document = await self.collection.find_one(query)
        return self.model_class(**document) if document else None
    
    async def find_all_active(self) -> List[CategoryDocument]:
        """활성화된 모든 카테고리 조회"""
        query = {"is_active": True}
        cursor = self.collection.find(query).sort("data.name", 1)
        documents = await cursor.to_list(length=None)
        return [self.model_class(**doc) for doc in documents]


class VoteRepository:
    """투표 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
        self.collection: Collection = self.db["votes"]
    
    async def find_by_request_and_user(
        self,
        request_id: str,
        user_id: str
    ) -> Optional[VoteDocument]:
        """요청과 사용자로 투표 조회"""
        query = {
            "data.request_id": request_id,
            "data.user_id": user_id,
            "is_active": True
        }
        document = await self.collection.find_one(query)
        return self.model_class(**document) if document else None
    
    async def find_by_request(self, request_id: str) -> List[VoteDocument]:
        """요청의 모든 투표 조회"""
        query = {"data.request_id": request_id, "is_active": True}
        cursor = self.collection.find(query)
        documents = await cursor.to_list(length=None)
        return [self.model_class(**doc) for doc in documents]
    
    async def count_by_request_and_type(
        self,
        request_id: str,
        vote_type: VoteType
    ) -> int:
        """요청의 특정 타입 투표 수 조회"""
        query = {
            "data.request_id": request_id,
            "data.vote_type": vote_type.value,
            "is_active": True
        }
        return await self.collection.count_documents(query)
    
    async def get_vote_counts(self, request_id: str) -> Dict[str, int]:
        """요청의 투표 수 통계"""
        pipeline = [
            {
                "$match": {
                    "data.request_id": request_id,
                    "is_active": True
                }
            },
            {
                "$group": {
                    "_id": "$data.vote_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        counts = {"like": 0, "dislike": 0}
        for result in results:
            counts[result["_id"]] = result["count"]
        
        return {
            "likes_count": counts["like"],
            "dislikes_count": counts["dislike"],
            "total_count": counts["like"] + counts["dislike"]
        }
    
    async def delete_by_request_and_user(
        self,
        request_id: str,
        user_id: str
    ) -> bool:
        """사용자의 투표 삭제 (투표 취소)"""
        try:
            result = await self.collection.update_one(
                {
                    "data.request_id": request_id,
                    "data.user_id": user_id
                },
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False