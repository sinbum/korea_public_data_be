from typing import Optional, List, Dict, Any
from datetime import datetime
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

from ...shared.pagination import PaginationParams, PaginatedResult, paginate_query_result
from ...core.database import get_database
from .models import DataRequest, DataRequestData, CategoryDocument, VoteDocument, DataRequestStatus, VoteType
from .schemas import DataRequestFilters


class DataRequestRepository:
    """데이터 요청 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_database()
        self.collection: Collection = self.db["data_requests"]
    
    def create(self, data_request: DataRequest) -> DataRequest:
        """데이터 요청 생성"""
        doc = data_request.model_dump(by_alias=True)
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        doc["is_active"] = True
        
        result = self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return DataRequest(**doc)
    
    def find_by_id(self, request_id: str) -> Optional[DataRequest]:
        """ID로 데이터 요청 조회"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(request_id), "is_active": True})
            return DataRequest(**doc) if doc else None
        except Exception:
            return None
    
    def update(self, request_id: str, data_request: DataRequest) -> DataRequest:
        """데이터 요청 수정"""
        doc = data_request.model_dump(by_alias=True, exclude={"_id"})
        doc["updated_at"] = datetime.utcnow()
        
        self.collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": doc}
        )
        
        return self.find_by_id(request_id)
    
    def delete(self, request_id: str) -> bool:
        """데이터 요청 삭제 (소프트 삭제)"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def find_by_filters(
        self,
        filters: DataRequestFilters,
        pagination: PaginationParams,
        user_id: Optional[str] = None
    ) -> PaginatedResult[DataRequest]:
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
        
        # 총 개수 조회
        try:
            total = self.collection.count_documents(query)
        except Exception as e:
            print(f"Error counting documents: {e}")
            total = 0
        
        # 페이지네이션 적용
        try:
            skip = (pagination.page - 1) * pagination.size
            cursor = self.collection.find(query).sort(sort_order).skip(skip).limit(pagination.size)
            documents = list(cursor)
        except Exception as e:
            print(f"Error fetching documents: {e}")
            documents = []
        
        items = []
        for doc in documents:
            try:
                items.append(DataRequest(**doc))
            except Exception as e:
                print(f"Error creating DataRequest from document: {e}")
                continue
        
        return paginate_query_result(items, total, pagination)
    
    def find_popular(self, limit: int = 10) -> List[DataRequest]:
        """인기 데이터 요청 조회"""
        query = {"is_active": True}
        sort_order = [("data.vote_count", -1), ("created_at", -1)]
        
        cursor = self.collection.find(query).sort(sort_order).limit(limit)
        documents = list(cursor)
        
        return [DataRequest(**doc) for doc in documents]
    
    def find_by_user(
        self,
        user_id: str,
        pagination: PaginationParams
    ) -> PaginatedResult[DataRequest]:
        """사용자의 데이터 요청 조회"""
        query = {"is_active": True, "data.user_id": user_id}
        sort_order = [("created_at", -1)]
        
        # 총 개수 조회
        total = self.collection.count_documents(query)
        
        # 페이지네이션 적용
        skip = (pagination.page - 1) * pagination.size
        cursor = self.collection.find(query).sort(sort_order).skip(skip).limit(pagination.size)
        documents = list(cursor)
        
        items = [DataRequest(**doc) for doc in documents]
        
        return paginate_query_result(items, total, pagination)
    
    def update_status(
        self, 
        request_id: str, 
        status: str, 
        admin_notes: Optional[str] = None,
        estimated_completion: Optional[datetime] = None
    ) -> bool:
        """데이터 요청 상태 업데이트"""
        try:
            update_doc = {
                "data.status": status,
                "updated_at": datetime.utcnow()
            }
            
            if admin_notes:
                update_doc["data.admin_notes"] = admin_notes
            
            if estimated_completion:
                update_doc["data.estimated_completion"] = estimated_completion
            
            result = self.collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": update_doc}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def update_vote_count(self, request_id: str, vote_count: int, likes_count: int, dislikes_count: int) -> bool:
        """투표 수 업데이트"""
        try:
            result = self.collection.update_one(
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
    
    def get_stats(self) -> Dict[str, Any]:
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
        
        status_counts = {}
        for doc in self.collection.aggregate(pipeline):
            status_counts[doc["_id"]] = doc
        
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
        
        category_counts = []
        for doc in self.collection.aggregate(category_pipeline):
            category_counts.append(doc)
        
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


class CategoryRepository:
    """카테고리 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_database()
        self.collection: Collection = self.db["categories"]
    
    def create(self, category: CategoryDocument) -> CategoryDocument:
        """카테고리 생성"""
        doc = category.model_dump(by_alias=True)
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        doc["is_active"] = True
        
        result = self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return CategoryDocument(**doc)
    
    def find_by_id(self, category_id: str) -> Optional[CategoryDocument]:
        """ID로 카테고리 조회"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(category_id), "is_active": True})
            return CategoryDocument(**doc) if doc else None
        except Exception:
            return None
    
    def find_by_name(self, name: str) -> Optional[CategoryDocument]:
        """이름으로 카테고리 조회"""
        doc = self.collection.find_one({"data.name": name, "is_active": True})
        return CategoryDocument(**doc) if doc else None
    
    def find_all_active(self) -> List[CategoryDocument]:
        """활성화된 모든 카테고리 조회"""
        query = {"is_active": True}
        cursor = self.collection.find(query).sort("data.name", 1)
        documents = list(cursor)
        return [CategoryDocument(**doc) for doc in documents]


class VoteRepository:
    """투표 저장소"""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_database()
        self.collection: Collection = self.db["votes"]
    
    def create(self, vote: VoteDocument) -> VoteDocument:
        """투표 생성"""
        doc = vote.model_dump(by_alias=True)
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        doc["is_active"] = True
        
        result = self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return VoteDocument(**doc)
    
    def update(self, vote_id: str, vote: VoteDocument) -> VoteDocument:
        """투표 수정"""
        doc = vote.model_dump(by_alias=True, exclude={"_id"})
        doc["updated_at"] = datetime.utcnow()
        
        self.collection.update_one(
            {"_id": ObjectId(vote_id)},
            {"$set": doc}
        )
        
        return vote
    
    def find_by_request_and_user(
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
        doc = self.collection.find_one(query)
        return VoteDocument(**doc) if doc else None
    
    def get_vote_counts(self, request_id: str) -> Dict[str, int]:
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
        
        results = []
        for doc in self.collection.aggregate(pipeline):
            results.append(doc)
        
        counts = {"like": 0, "dislike": 0}
        for result in results:
            counts[result["_id"]] = result["count"]
        
        return {
            "likes_count": counts["like"],
            "dislikes_count": counts["dislike"],
            "total_count": counts["like"] + counts["dislike"]
        }
    
    def delete_by_request_and_user(
        self,
        request_id: str,
        user_id: str
    ) -> bool:
        """사용자의 투표 삭제 (투표 취소)"""
        try:
            result = self.collection.update_one(
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