"""
Statistics Service implementation.

Provides business logic for statistics-related operations using Repository pattern.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Statistics, StatisticsCreate, StatisticsUpdate
from .repository import StatisticsRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class StatisticsService:
    """통계 서비스"""
    
    def __init__(self, repository: Optional[StatisticsRepository] = None):
        self.repository = repository or StatisticsRepository()
    
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