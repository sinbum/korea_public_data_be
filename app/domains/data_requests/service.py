from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# Removed BaseService import - not needed for this service
from ...shared.pagination import PaginationParams, PaginatedResult
from ...shared.exceptions.custom_exceptions import BaseAPIException
from .models import (
    DataRequest, DataRequestData, CategoryDocument, VoteDocument,
    DataRequestStatus, DataRequestPriority, VoteType, Category, Vote
)
from .schemas import (
    DataRequestCreateRequest, DataRequestUpdateRequest, DataRequestStatusUpdateRequest,
    VoteRequest, CategoryCreateRequest, DataRequestFilters,
    DataRequestResponse, DataRequestListResponse, VoteResponse, CategoryResponse,
    DataRequestStatsResponse
)
from .repository import DataRequestRepository, CategoryRepository, VoteRepository


class DataRequestService:
    """데이터 요청 서비스"""
    
    def __init__(
        self,
        data_request_repository: DataRequestRepository,
        category_repository: CategoryRepository,
        vote_repository: VoteRepository
    ):
        self.data_request_repo = data_request_repository
        self.category_repo = category_repository
        self.vote_repo = vote_repository
    
    async def create_data_request(
        self,
        request_data: DataRequestCreateRequest,
        user_id: str,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> DataRequestResponse:
        """데이터 요청 생성"""
        # 카테고리 존재 확인
        category = await self.category_repo.find_by_id(request_data.category_id)
        if not category:
            raise BaseAPIException(f"카테고리를 찾을 수 없습니다: {request_data.category_id}")
        
        # 데이터 요청 생성
        data_request_data = DataRequestData(
            title=request_data.title,
            description=request_data.description,
            category_id=request_data.category_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            priority=request_data.priority or DataRequestPriority.MEDIUM,
            tags=request_data.tags or []
        )
        
        data_request = DataRequest(
            data=data_request_data,
            source="web"
        )
        
        # 저장
        saved_request = await self.data_request_repo.create(data_request)
        
        # 응답 생성
        return await self._build_response(saved_request, category=category)
    
    async def get_data_request(
        self,
        request_id: str,
        user_id: Optional[str] = None
    ) -> DataRequestResponse:
        """데이터 요청 상세 조회"""
        data_request = await self.data_request_repo.find_by_id(request_id)
        if not data_request:
            raise BaseAPIException(f"데이터 요청을 찾을 수 없습니다: {request_id}")
        
        return await self._build_response(data_request, user_id=user_id)
    
    async def get_data_requests(
        self,
        filters: DataRequestFilters,
        user_id: Optional[str] = None
    ) -> DataRequestListResponse:
        """데이터 요청 목록 조회"""
        pagination = PaginationParams(page=filters.page, size=filters.limit)
        
        paginated_result = await self.data_request_repo.find_by_filters(
            filters, pagination, user_id
        )
        
        # 응답 변환
        response_items = []
        for request in paginated_result.items:
            response_item = await self._build_response(request, user_id=user_id)
            response_items.append(response_item)
        
        return DataRequestListResponse(
            data=response_items,
            total=paginated_result.total,
            page=paginated_result.page,
            limit=paginated_result.limit,
            total_pages=paginated_result.total_pages,
            has_next=paginated_result.has_next,
            has_previous=paginated_result.has_previous
        )
    
    async def update_data_request(
        self,
        request_id: str,
        update_data: DataRequestUpdateRequest,
        user_id: str
    ) -> DataRequestResponse:
        """데이터 요청 수정"""
        data_request = await self.data_request_repo.find_by_id(request_id)
        if not data_request:
            raise BaseAPIException(f"데이터 요청을 찾을 수 없습니다: {request_id}")
        
        # 권한 확인 (요청자만 수정 가능)
        if data_request.data.user_id != user_id:
            raise BaseAPIException("수정 권한이 없습니다.")
        
        # 업데이트 데이터 적용
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if update_dict:
            # 카테고리 변경 시 유효성 확인
            if "category_id" in update_dict:
                category = await self.category_repo.find_by_id(update_dict["category_id"])
                if not category:
                    raise BaseAPIException(f"카테고리를 찾을 수 없습니다: {update_dict['category_id']}")
            
            # 업데이트 실행
            for key, value in update_dict.items():
                if hasattr(data_request.data, key):
                    setattr(data_request.data, key, value)
            
            updated_request = await self.data_request_repo.update(request_id, data_request)
            return await self._build_response(updated_request, user_id=user_id)
        
        return await self._build_response(data_request, user_id=user_id)
    
    async def delete_data_request(self, request_id: str, user_id: str) -> bool:
        """데이터 요청 삭제"""
        data_request = await self.data_request_repo.find_by_id(request_id)
        if not data_request:
            raise BaseAPIException(f"데이터 요청을 찾을 수 없습니다: {request_id}")
        
        # 권한 확인 (요청자만 삭제 가능)
        if data_request.data.user_id != user_id:
            raise BaseAPIException("삭제 권한이 없습니다.")
        
        return await self.data_request_repo.delete(request_id)
    
    async def vote_data_request(
        self,
        request_id: str,
        vote_data: VoteRequest,
        user_id: str
    ) -> VoteResponse:
        """데이터 요청에 투표"""
        # 요청 존재 확인
        data_request = await self.data_request_repo.find_by_id(request_id)
        if not data_request:
            raise BaseAPIException(f"데이터 요청을 찾을 수 없습니다: {request_id}")
        
        # 기존 투표 확인
        existing_vote = await self.vote_repo.find_by_request_and_user(request_id, user_id)
        
        if existing_vote:
            # 같은 타입의 투표라면 투표 취소
            if existing_vote.data.vote_type == vote_data.vote_type:
                await self.vote_repo.delete_by_request_and_user(request_id, user_id)
                user_voted = False
                user_vote_type = None
            else:
                # 다른 타입의 투표라면 변경
                existing_vote.data.vote_type = vote_data.vote_type
                await self.vote_repo.update(str(existing_vote._id), existing_vote)
                user_voted = True
                user_vote_type = vote_data.vote_type
        else:
            # 새 투표 생성
            vote = Vote(
                id=str(uuid.uuid4()),
                request_id=request_id,
                user_id=user_id,
                vote_type=vote_data.vote_type
            )
            
            vote_document = VoteDocument(data=vote)
            await self.vote_repo.create(vote_document)
            user_voted = True
            user_vote_type = vote_data.vote_type
        
        # 투표 수 업데이트
        vote_counts = await self.vote_repo.get_vote_counts(request_id)
        await self.data_request_repo.update_vote_count(
            request_id,
            vote_counts["total_count"],
            vote_counts["likes_count"],
            vote_counts["dislikes_count"]
        )
        
        return VoteResponse(
            success=True,
            vote_count=vote_counts["total_count"],
            likes_count=vote_counts["likes_count"],
            dislikes_count=vote_counts["dislikes_count"],
            user_voted=user_voted,
            user_vote_type=user_vote_type
        )
    
    async def update_request_status(
        self,
        request_id: str,
        status_data: DataRequestStatusUpdateRequest
    ) -> DataRequestResponse:
        """데이터 요청 상태 변경 (관리자용)"""
        data_request = await self.data_request_repo.find_by_id(request_id)
        if not data_request:
            raise BaseAPIException(f"데이터 요청을 찾을 수 없습니다: {request_id}")
        
        success = await self.data_request_repo.update_status(
            request_id,
            status_data.status,
            status_data.admin_notes,
            status_data.estimated_completion
        )
        
        if not success:
            raise BaseAPIException("상태 업데이트에 실패했습니다.")
        
        # 업데이트된 요청 조회
        updated_request = await self.data_request_repo.find_by_id(request_id)
        return await self._build_response(updated_request)
    
    async def get_popular_requests(self, limit: int = 10) -> List[DataRequestResponse]:
        """인기 데이터 요청 조회"""
        popular_requests = await self.data_request_repo.find_popular(limit)
        
        response_items = []
        for request in popular_requests:
            response_item = await self._build_response(request)
            response_items.append(response_item)
        
        return response_items
    
    async def get_user_requests(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> DataRequestListResponse:
        """사용자의 데이터 요청 목록 조회"""
        pagination = PaginationParams(page=page, size=limit)
        paginated_result = await self.data_request_repo.find_by_user(user_id, pagination)
        
        response_items = []
        for request in paginated_result.items:
            response_item = await self._build_response(request, user_id=user_id)
            response_items.append(response_item)
        
        return DataRequestListResponse(
            data=response_items,
            total=paginated_result.total,
            page=paginated_result.page,
            limit=paginated_result.limit,
            total_pages=paginated_result.total_pages,
            has_next=paginated_result.has_next,
            has_previous=paginated_result.has_previous
        )
    
    async def get_stats(self) -> DataRequestStatsResponse:
        """데이터 요청 통계 조회"""
        stats = await self.data_request_repo.get_stats()
        popular_requests = await self.get_popular_requests(5)
        
        return DataRequestStatsResponse(
            total_requests=stats["total_requests"],
            pending_requests=stats["pending_requests"],
            in_progress_requests=stats["in_progress_requests"],
            completed_requests=stats["completed_requests"],
            rejected_requests=stats["rejected_requests"],
            total_votes=stats["total_votes"],
            requests_by_category=stats["requests_by_category"],
            popular_requests=popular_requests
        )
    
    async def _build_response(
        self,
        data_request: DataRequest,
        user_id: Optional[str] = None,
        category: Optional[CategoryDocument] = None
    ) -> DataRequestResponse:
        """데이터 요청 응답 객체 생성"""
        # 카테고리 정보 조회
        if not category:
            category = await self.category_repo.find_by_id(data_request.data.category_id)
        
        category_response = None
        if category:
            category_response = CategoryResponse(
                id=category.id,
                name=category.data.name,
                description=category.data.description,
                color=category.data.color,
                created_at=category.data.created_at
            )
        
        # 사용자 투표 정보 조회
        user_voted = None
        user_vote_type = None
        if user_id:
            user_vote = await self.vote_repo.find_by_request_and_user(
                str(data_request._id), user_id
            )
            if user_vote:
                user_voted = True
                user_vote_type = user_vote.data.vote_type
            else:
                user_voted = False
        
        return DataRequestResponse(
            id=data_request.id,
            title=data_request.data.title,
            description=data_request.data.description,
            category_id=data_request.data.category_id,
            category=category_response,
            user_id=data_request.data.user_id,
            user_name=data_request.data.user_name,
            user_email=data_request.data.user_email,
            status=data_request.data.status,
            priority=data_request.data.priority,
            vote_count=data_request.data.vote_count,
            likes_count=data_request.data.likes_count,
            dislikes_count=data_request.data.dislikes_count,
            user_voted=user_voted,
            user_vote_type=user_vote_type,
            tags=data_request.data.tags,
            admin_notes=data_request.data.admin_notes,
            estimated_completion=data_request.data.estimated_completion,
            actual_completion=data_request.data.actual_completion,
            created_at=data_request.created_at,
            updated_at=data_request.updated_at
        )


class CategoryService:
    """카테고리 서비스"""
    
    def __init__(self, category_repository: CategoryRepository):
        self.category_repo = category_repository
    
    async def create_category(self, request_data: CategoryCreateRequest) -> CategoryResponse:
        """카테고리 생성"""
        # 중복 이름 확인
        existing = await self.category_repo.find_by_name(request_data.name)
        if existing:
            raise BaseAPIException(f"이미 존재하는 카테고리입니다: {request_data.name}")
        
        # 카테고리 생성
        category = Category(
            id=str(uuid.uuid4()),
            name=request_data.name,
            description=request_data.description,
            color=request_data.color
        )
        
        category_document = CategoryDocument(data=category)
        saved_category = await self.category_repo.create(category_document)
        
        return CategoryResponse(
            id=saved_category.id,
            name=saved_category.data.name,
            description=saved_category.data.description,
            color=saved_category.data.color,
            created_at=saved_category.data.created_at
        )
    
    async def get_categories(self) -> List[CategoryResponse]:
        """모든 활성 카테고리 조회"""
        categories = await self.category_repo.find_all_active()
        
        return [
            CategoryResponse(
                id=category.id,
                name=category.data.name,
                description=category.data.description,
                color=category.data.color,
                created_at=category.data.created_at
            )
            for category in categories
        ]
    
    async def get_category(self, category_id: str) -> CategoryResponse:
        """카테고리 상세 조회"""
        category = await self.category_repo.find_by_id(category_id)
        if not category:
            raise BaseAPIException(f"카테고리를 찾을 수 없습니다: {category_id}")
        
        return CategoryResponse(
            id=category.id,
            name=category.data.name,
            description=category.data.description,
            color=category.data.color,
            created_at=category.data.created_at
        )