"""
Statistics Service implementation.

Provides business logic for statistics-related operations using Repository pattern.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Statistics, StatisticsCreate, StatisticsUpdate
from .repository import StatisticsRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import StatisticalItem
from ...shared.interfaces.base_service import BaseService
from ...shared.interfaces.domain_services import IStatisticsService
from ...shared.schemas import PaginatedResponse, DataCollectionResult
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class StatisticsService(BaseService[Statistics, StatisticsCreate, StatisticsUpdate, StatisticalItem]):
    """통계 서비스"""
    
    def __init__(self, repository: StatisticsRepository, api_client: Optional[KStartupAPIClient] = None):
        super().__init__(repository=repository, logger=logger)
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    # BaseService 추상 메소드 구현
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """ID로 통계 데이터 조회"""
        return await self.repository.get_by_id(item_id)
    
    async def _fetch_list(
        self, 
        page: int, 
        limit: int, 
        query_params: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int]:
        """페이지네이션된 통계 목록 조회"""
        filters = query_params.get("filters", {})
        sort_by = query_params.get("sort_by")
        sort_order = query_params.get("sort_order", "desc")
        
        offset = (page - 1) * limit
        return await self.repository.get_list(
            offset=offset,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def _save_new_item(self, domain_data: Statistics) -> Dict[str, Any]:
        """새 통계 저장"""
        return await self.repository.create(domain_data)
    
    async def _save_updated_item(self, item_id: str, domain_data: Statistics) -> Dict[str, Any]:
        """통계 업데이트"""
        return await self.repository.update(item_id, domain_data)
    
    async def _delete_item(self, item_id: str) -> bool:
        """통계 삭제"""
        return await self.repository.delete(item_id)
    
    async def _transform_to_response(self, raw_data: Dict[str, Any]) -> StatisticalItem:
        """원본 데이터를 응답 모델로 변환"""
        return StatisticalItem(**raw_data)
    
    async def _transform_to_domain(self, input_data) -> Statistics:
        """입력 데이터를 도메인 모델로 변환"""
        if isinstance(input_data, StatisticsCreate):
            return Statistics(**input_data.model_dump())
        elif isinstance(input_data, StatisticsUpdate):
            return Statistics(**input_data.model_dump(exclude_unset=True))
        else:
            return Statistics(**input_data)
    
    # 도메인별 특화 메소드들
    async def fetch_statistics_from_api(
        self,
        page_no: int = 1,
        num_of_rows: int = 10
    ) -> DataCollectionResult:
        """K-Startup API에서 통계 데이터 수집"""
        start_time = datetime.utcnow()
        result = DataCollectionResult(
            total_fetched=0,
            new_items=0,
            updated_items=0,
            skipped_items=0,
            errors=[],
            collection_time=0.0
        )
        
        try:
            statistics = self.fetch_and_save_statistics(page_no, num_of_rows)
            result.total_fetched = len(statistics)
            result.new_items = len(statistics)
            
        except Exception as e:
            result.errors.append(str(e))
            self._log_error(f"통계 데이터 수집 실패: {e}")
        
        end_time = datetime.utcnow()
        result.collection_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def get_statistics_by_category(
        self,
        category: str,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[StatisticalItem]:
        """카테고리별 통계 목록 조회"""
        filters = {"category": category}
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_statistics_by_period(
        self,
        year: int,
        month: Optional[int] = None,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedResponse[StatisticalItem]:
        """기간별 통계 목록 조회"""
        filters = {"year": year}
        if month:
            filters["month"] = month
        return await self.get_list(page=page, limit=limit, filters=filters)
    
    async def get_trend_analysis(
        self,
        category: str,
        start_year: int,
        end_year: int
    ) -> Dict[str, Any]:
        """통계 트렌드 분석"""
        filters = {
            "category": category,
            "year": {"$gte": start_year, "$lte": end_year}
        }
        stats_data, _ = await self._fetch_list(1, 1000, {"filters": filters})
        
        # 트렌드 분석 로직
        trend_data = {}
        for stat in stats_data:
            year = stat.get("year")
            value = stat.get("value", 0)
            if year not in trend_data:
                trend_data[year] = []
            trend_data[year].append(value)
        
        # 연도별 평균 계산
        yearly_averages = {}
        for year, values in trend_data.items():
            yearly_averages[year] = sum(values) / len(values) if values else 0
        
        return {
            "category": category,
            "period": f"{start_year}-{end_year}",
            "yearly_averages": yearly_averages,
            "total_data_points": len(stats_data)
        }
    
    async def get_summary_statistics(self) -> Dict[str, Any]:
        """요약 통계 조회"""
        total_count = await self.repository.count()
        
        # 카테고리별 통계
        categories = await self._get_categories_summary()
        
        return {
            "total_statistics": total_count,
            "categories": categories,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def calculate_growth_rate(
        self,
        category: str,
        year: int,
        comparison_year: int
    ) -> Dict[str, Any]:
        """성장률 계산"""
        # 두 연도의 데이터 조회
        current_year_data = await self._get_year_average(category, year)
        comparison_year_data = await self._get_year_average(category, comparison_year)
        
        if comparison_year_data == 0:
            growth_rate = 0
        else:
            growth_rate = ((current_year_data - comparison_year_data) / comparison_year_data) * 100
        
        return {
            "category": category,
            "current_year": year,
            "current_value": current_year_data,
            "comparison_year": comparison_year,
            "comparison_value": comparison_year_data,
            "growth_rate": round(growth_rate, 2)
        }
    
    async def _get_categories_summary(self) -> Dict[str, int]:
        """카테고리별 요약 통계"""
        # 간단한 구현 - 실제로는 aggregation 사용
        categories = {}
        all_stats, _ = await self._fetch_list(1, 1000, {})
        
        for stat in all_stats:
            category = stat.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        
        return categories
    
    async def _get_year_average(self, category: str, year: int) -> float:
        """년도별 평균값 계산"""
        filters = {"category": category, "year": year}
        stats_data, _ = await self._fetch_list(1, 1000, {"filters": filters})
        
        if not stats_data:
            return 0.0
        
        total_value = sum(stat.get("value", 0) for stat in stats_data)
        return total_value / len(stats_data)
    
    def fetch_and_save_statistics(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Statistics]:
        """공공데이터에서 통계 정보를 가져와 저장"""
        statistics_list = []
        
        try:
            # K-Startup API 호출
            with KStartupAPIClient() as client:
                response = client.get_statistical_information(
                    page_no=page_no,
                    num_of_rows=num_of_rows,
                    year=year,
                    month=month
                )
                
                if not response.success:
                    logger.error(f"API 호출 실패: {response.error}")
                    return statistics_list
                
                logger.info(f"API 응답: {len(response.data.data)}건 조회")
                
                # 응답 데이터 처리
                for item in response.data.data:
                    try:
                        # 공공데이터 응답을 우리 모델에 맞게 변환
                        statistical_data = self._transform_api_data(item.dict())
                        
                        # 중복 체크
                        stat_id = statistical_data.get("stat_id")
                        stat_name = statistical_data.get("stat_name")
                        stat_year = statistical_data.get("year")
                        stat_month = statistical_data.get("month")
                        
                        is_duplicate = self.repository.check_duplicate(
                            stat_id=stat_id,
                            stat_name=stat_name,
                            year=stat_year,
                            month=stat_month
                        )
                        
                        if is_duplicate:
                            logger.info(f"중복 데이터 스킵: {stat_name} ({stat_year}-{stat_month})")
                            continue
                        
                        # 새 통계 생성
                        statistics_create = StatisticsCreate(
                            statistical_data=statistical_data,
                            source_url=f"K-Startup-통계-{stat_id or 'unknown'}"
                        )
                        
                        # Repository를 통해 저장
                        statistics = self.repository.create(statistics_create)
                        statistics_list.append(statistics)
                        
                        logger.info(f"새로운 통계 저장: {stat_name}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"K-Startup API 호출 실패: {e}")
            
        return statistics_list
    
    def _transform_api_data(self, api_item: dict) -> dict:
        """K-Startup API 응답을 내부 모델로 변환"""
        return {
            "stat_id": api_item.get("stat_id"),
            "stat_name": api_item.get("stat_name"),
            "stat_type": api_item.get("stat_type"),
            "period": api_item.get("period"),
            "year": api_item.get("year"),
            "month": api_item.get("month"),
            "metrics": api_item.get("metrics", {}),
            "total_count": api_item.get("total_count"),
            "success_count": api_item.get("success_count"),
            "success_rate": api_item.get("success_rate")
        }
    
    def get_statistics(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True
    ) -> PaginationResult[Statistics]:
        """저장된 통계 목록 조회 (페이지네이션)"""
        try:
            if is_active:
                return self.repository.find_active_statistics(page=page, page_size=page_size)
            else:
                filters = QueryFilter().eq("is_active", False)
                return self.repository.get_paginated(page=page, page_size=page_size, filters=filters)
        except Exception as e:
            logger.error(f"통계 목록 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_statistics_by_id(self, statistics_id: str) -> Optional[Statistics]:
        """ID로 통계 조회"""
        try:
            return self.repository.get_by_id(statistics_id)
        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return None
    
    def create_statistics(self, statistics_data: StatisticsCreate) -> Statistics:
        """새 통계 생성"""
        try:
            return self.repository.create(statistics_data)
        except Exception as e:
            logger.error(f"통계 생성 오류: {e}")
            raise
    
    def update_statistics(
        self, 
        statistics_id: str, 
        update_data: StatisticsUpdate
    ) -> Optional[Statistics]:
        """통계 수정"""
        try:
            return self.repository.update_by_id(statistics_id, update_data)
        except Exception as e:
            logger.error(f"통계 수정 오류: {e}")
            return None
    
    def delete_statistics(self, statistics_id: str) -> bool:
        """통계 삭제 (비활성화)"""
        try:
            return self.repository.delete_by_id(statistics_id, soft_delete=True)
        except Exception as e:
            logger.error(f"통계 삭제 오류: {e}")
            return False
    
    # 추가 비즈니스 로직 메서드들
    def search_statistics(self, search_term: str) -> List[Statistics]:
        """통계 검색"""
        try:
            return self.repository.search_statistics(search_term)
        except Exception as e:
            logger.error(f"통계 검색 오류: {e}")
            return []
    
    def get_statistics_by_type(self, stat_type: str) -> List[Statistics]:
        """통계 유형별 조회"""
        try:
            return self.repository.find_by_stat_type(stat_type)
        except Exception as e:
            logger.error(f"유형별 통계 조회 오류: {e}")
            return []
    
    def get_statistics_by_year(self, year: int) -> List[Statistics]:
        """연도별 통계 조회"""
        try:
            return self.repository.find_by_year(year)
        except Exception as e:
            logger.error(f"연도별 통계 조회 오류: {e}")
            return []
    
    def get_statistics_by_year_month(self, year: int, month: int) -> List[Statistics]:
        """연월별 통계 조회"""
        try:
            return self.repository.find_by_year_month(year, month)
        except Exception as e:
            logger.error(f"연월별 통계 조회 오류: {e}")
            return []
    
    def get_statistics_by_period(self, period: str) -> List[Statistics]:
        """기간별 통계 조회"""
        try:
            return self.repository.find_by_period(period)
        except Exception as e:
            logger.error(f"기간별 통계 조회 오류: {e}")
            return []
    
    def get_recent_statistics(self, limit: int = 10) -> List[Statistics]:
        """최근 통계 조회"""
        try:
            return self.repository.get_recent_statistics(limit)
        except Exception as e:
            logger.error(f"최근 통계 조회 오류: {e}")
            return []
    
    def get_statistics_by_date_range(
        self, 
        start_year: int,
        start_month: int = 1,
        end_year: Optional[int] = None,
        end_month: Optional[int] = None
    ) -> List[Statistics]:
        """날짜 범위별 통계 조회"""
        try:
            return self.repository.find_by_date_range(start_year, start_month, end_year, end_month)
        except Exception as e:
            logger.error(f"날짜 범위별 통계 조회 오류: {e}")
            return []
    
    def get_statistics_with_filter(
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
        """필터 조건에 따른 통계 조회"""
        try:
            return self.repository.get_statistics_by_filter(
                stat_type=stat_type,
                period=period,
                year=year,
                month=month,
                min_total_count=min_total_count,
                min_success_rate=min_success_rate,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            logger.error(f"필터 조건별 통계 조회 오류: {e}")
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
        """집계 지표 조회"""
        try:
            return self.repository.get_aggregated_metrics(stat_type, year)
        except Exception as e:
            logger.error(f"집계 지표 조회 오류: {e}")
            return {}
    
    def get_statistics_overview(self) -> Dict[str, Any]:
        """통계 개요 조회"""
        try:
            return self.repository.get_statistics_overview()
        except Exception as e:
            logger.error(f"통계 개요 조회 오류: {e}")
            return {}
    
    def bulk_create_statistics(self, statistics_list: List[StatisticsCreate]) -> List[Statistics]:
        """대량 통계 생성"""
        try:
            return self.repository.bulk_create_statistics(statistics_list)
        except Exception as e:
            logger.error(f"대량 통계 생성 오류: {e}")
            return []
    
    def generate_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        """월별 리포트 생성"""
        try:
            monthly_stats = self.get_statistics_by_year_month(year, month)
            
            # 기본 통계
            total_stats = len(monthly_stats)
            
            # 타입별 분류
            type_breakdown = {}
            total_count_sum = 0
            success_count_sum = 0
            
            for stat in monthly_stats:
                stat_type = stat.statistical_data.stat_type or "unknown"
                if stat_type not in type_breakdown:
                    type_breakdown[stat_type] = 0
                type_breakdown[stat_type] += 1
                
                if stat.statistical_data.total_count:
                    total_count_sum += stat.statistical_data.total_count
                if stat.statistical_data.success_count:
                    success_count_sum += stat.statistical_data.success_count
            
            success_rate = (success_count_sum / total_count_sum * 100) if total_count_sum > 0 else 0
            
            return {
                "year": year,
                "month": month,
                "total_statistics": total_stats,
                "type_breakdown": type_breakdown,
                "total_count_sum": total_count_sum,
                "success_count_sum": success_count_sum,
                "overall_success_rate": round(success_rate, 2),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"월별 리포트 생성 오류: {e}")
            return {}
    
    def generate_yearly_report(self, year: int) -> Dict[str, Any]:
        """연별 리포트 생성"""
        try:
            yearly_stats = self.get_statistics_by_year(year)
            
            # 월별 분류
            monthly_breakdown = {}
            type_breakdown = {}
            total_count_sum = 0
            success_count_sum = 0
            
            for stat in yearly_stats:
                month = stat.statistical_data.month or 0
                if month not in monthly_breakdown:
                    monthly_breakdown[month] = 0
                monthly_breakdown[month] += 1
                
                stat_type = stat.statistical_data.stat_type or "unknown"
                if stat_type not in type_breakdown:
                    type_breakdown[stat_type] = 0
                type_breakdown[stat_type] += 1
                
                if stat.statistical_data.total_count:
                    total_count_sum += stat.statistical_data.total_count
                if stat.statistical_data.success_count:
                    success_count_sum += stat.statistical_data.success_count
            
            success_rate = (success_count_sum / total_count_sum * 100) if total_count_sum > 0 else 0
            
            return {
                "year": year,
                "total_statistics": len(yearly_stats),
                "monthly_breakdown": monthly_breakdown,
                "type_breakdown": type_breakdown,
                "total_count_sum": total_count_sum,
                "success_count_sum": success_count_sum,
                "overall_success_rate": round(success_rate, 2),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"연별 리포트 생성 오류: {e}")
            return {}