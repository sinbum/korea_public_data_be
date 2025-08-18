"""
사업정보 대량 데이터 수집을 위한 배치 처리 서비스
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import BusinessItem, KStartupBusinessResponse
from ...shared.exceptions import APIResponseError, DataValidationError
from .repository import BusinessRepository
from .schemas import BusinessCreate
from .models import Business

logger = logging.getLogger(__name__)


@dataclass
class BusinessBatchResult:
    """사업정보 배치 처리 결과"""
    total_requested: int
    total_processed: int
    new_items: int
    duplicate_items: int
    error_items: int
    processing_time: float
    errors: List[str]


@dataclass
class BusinessBatchProgress:
    """사업정보 배치 진행 상황"""
    current_page: int
    total_pages: int
    processed_items: int
    estimated_total: int
    start_time: datetime
    elapsed_time: float
    estimated_remaining_time: float


class BusinessBatchService:
    """사업정보 대량 데이터 수집 배치 서비스"""
    
    def __init__(self, repository: BusinessRepository, api_client: KStartupAPIClient):
        self.repository = repository
        self.api_client = api_client
        self.batch_size = 100  # 페이지당 항목 수
        self.max_concurrent_requests = 5  # 동시 요청 수 제한
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """진행 상황 콜백 함수 설정"""
        self.progress_callback = callback
        
    async def collect_all_businesses(
        self, 
        max_pages: Optional[int] = None,
        business_type: Optional[str] = None,
        organization: Optional[str] = None
    ) -> BusinessBatchResult:
        """모든 사업정보 데이터를 대량으로 수집"""
        start_time = datetime.now()
        total_processed = 0
        new_items = 0
        duplicate_items = 0
        error_items = 0
        errors = []
        
        try:
            # 1. 총 데이터 양 추정
            logger.info("총 데이터 양 확인 중...")
            first_response = await self.api_client.async_get_business_information(
                page_no=1, 
                num_of_rows=1,
                business_type=business_type,
                organization=organization
            )
            
            if not first_response.success:
                raise APIResponseError(f"API 초기 요청 실패: {first_response.error}")
                
            # API가 정확한 total_count를 제공하지 않을 수 있으므로 추정
            estimated_total = 1231  # 이전 분석에서 확인한 총량
            total_pages = (estimated_total // self.batch_size) + 1
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
                
            logger.info(f"예상 총 페이지: {total_pages}, 배치 크기: {self.batch_size}")
            
            # 2. 배치 단위로 병렬 처리
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def process_page_batch(page_start: int, page_end: int) -> Tuple[int, int, int, List[str]]:
                """페이지 범위를 배치로 처리"""
                batch_processed = 0
                batch_new = 0
                batch_duplicates = 0
                batch_errors = []
                
                tasks = []
                for page in range(page_start, min(page_end, total_pages + 1)):
                    tasks.append(self._process_single_page(semaphore, page, business_type, organization))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        batch_errors.append(str(result))
                        continue
                        
                    page_processed, page_new, page_duplicates, page_errors = result
                    batch_processed += page_processed
                    batch_new += page_new
                    batch_duplicates += page_duplicates
                    batch_errors.extend(page_errors)
                
                return batch_processed, batch_new, batch_duplicates, batch_errors
            
            # 3. 중간 규모 처리를 위한 청크 단위 실행
            chunk_size = 15  # 사업정보는 공고보다 적으므로 청크 크기 조정
            current_page = 1
            
            while current_page <= total_pages:
                chunk_end = min(current_page + chunk_size, total_pages + 1)
                
                logger.info(f"페이지 {current_page}-{chunk_end-1} 처리 중...")
                
                batch_processed, batch_new, batch_duplicates, batch_errors = await process_page_batch(
                    current_page, chunk_end
                )
                
                total_processed += batch_processed
                new_items += batch_new
                duplicate_items += batch_duplicates
                errors.extend(batch_errors)
                
                # 진행 상황 보고
                elapsed_time = (datetime.now() - start_time).total_seconds()
                estimated_remaining = 0
                if current_page > 1:
                    avg_time_per_page = elapsed_time / (current_page - 1)
                    remaining_pages = total_pages - current_page + 1
                    estimated_remaining = avg_time_per_page * remaining_pages
                
                progress = BusinessBatchProgress(
                    current_page=current_page,
                    total_pages=total_pages,
                    processed_items=total_processed,
                    estimated_total=estimated_total,
                    start_time=start_time,
                    elapsed_time=elapsed_time,
                    estimated_remaining_time=estimated_remaining
                )
                
                if self.progress_callback:
                    await self.progress_callback(progress)
                    
                logger.info(f"진행상황: {current_page}/{total_pages} 페이지, "
                          f"처리된 항목: {total_processed}, 신규: {new_items}, "
                          f"중복: {duplicate_items}, 오류: {len(errors)}")
                
                current_page = chunk_end
                
                # 메모리 정리를 위한 짧은 대기
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"배치 수집 중 오류: {e}")
            errors.append(str(e))
            error_items += 1
            
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = BusinessBatchResult(
            total_requested=total_pages * self.batch_size,
            total_processed=total_processed,
            new_items=new_items,
            duplicate_items=duplicate_items,
            error_items=error_items,
            processing_time=processing_time,
            errors=errors
        )
        
        logger.info(f"사업정보 배치 수집 완료: {result}")
        return result
    
    async def _process_single_page(
        self, 
        semaphore: asyncio.Semaphore, 
        page_no: int,
        business_type: Optional[str] = None,
        organization: Optional[str] = None
    ) -> Tuple[int, int, int, List[str]]:
        """단일 페이지 처리"""
        async with semaphore:
            try:
                response = await self.api_client.async_get_business_information(
                    page_no=page_no,
                    num_of_rows=self.batch_size,
                    business_type=business_type,
                    organization=organization
                )
                
                if not response.success:
                    return 0, 0, 0, [f"페이지 {page_no} API 요청 실패: {response.error}"]
                
                if not response.data or not response.data.data:
                    return 0, 0, 0, []
                
                processed = 0
                new_items = 0
                duplicates = 0
                errors = []
                
                # 벌크 삽입을 위한 데이터 준비
                items_to_create = []
                
                for item in response.data.data:
                    processed += 1
                    
                    try:
                        if isinstance(item, BusinessItem):
                            business_data = item.dict()
                            business_id = business_data.get('business_id')
                            business_name = business_data.get('business_name', 'Unknown')
                            
                            # 중복 체크 (배치에서는 간단한 체크만)
                            if business_id:
                                is_duplicate = self.repository.check_duplicate(
                                    business_id=business_id,
                                    business_name=business_name
                                )
                                
                                if is_duplicate:
                                    duplicates += 1
                                    continue
                            
                            # 새 항목 준비
                            business_create = BusinessCreate(
                                business_data=business_data,
                                source_url=f"K-Startup-사업정보-{business_id or 'unknown'}"
                            )
                            
                            items_to_create.append(business_create)
                            
                    except Exception as e:
                        errors.append(f"페이지 {page_no} 항목 처리 오류: {str(e)}")
                        continue
                
                # 벌크 삽입 실행
                if items_to_create:
                    try:
                        created_items = await self.repository.create_many(items_to_create)
                        new_items = len(created_items)
                        logger.debug(f"페이지 {page_no}: {new_items}개 신규 항목 생성")
                    except Exception as e:
                        errors.append(f"페이지 {page_no} 벌크 삽입 오류: {str(e)}")
                        new_items = 0
                
                return processed, new_items, duplicates, errors
                
            except Exception as e:
                return 0, 0, 0, [f"페이지 {page_no} 처리 중 예외: {str(e)}"]
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        try:
            total_count = await self.repository.count_all()
            recent_count = await self.repository.count_recent(days=7)
            
            return {
                "total_businesses": total_count,
                "recent_businesses": recent_count,
                "collection_rate": f"{(total_count / 1231 * 100):.1f}%" if total_count else "0%",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {
                "total_businesses": 0,
                "recent_businesses": 0,
                "collection_rate": "0%",
                "last_updated": datetime.now().isoformat(),
                "error": str(e)
            }