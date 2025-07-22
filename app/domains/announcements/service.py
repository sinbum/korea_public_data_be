from typing import List, Optional
from .models import Announcement, AnnouncementCreate, AnnouncementUpdate
from .repository import AnnouncementRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient
from ...shared.models.kstartup import KStartupAnnouncementResponse
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class AnnouncementService:
    """사업공고 서비스"""
    
    def __init__(self, repository: AnnouncementRepository, api_client: Optional[KStartupAPIClient] = None):
        self.repository = repository
        self.api_client = api_client or KStartupAPIClient()
    
    async def fetch_and_save_announcements(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> List[Announcement]:
        """K-Startup API에서 사업공고 정보를 가져와 저장"""
        announcements = []
        
        try:
            # K-Startup API 호출 (새로운 클라이언트 사용)
            response = await self.api_client.async_get_announcement_information(
                page_no=page_no,
                num_of_rows=num_of_rows,
                business_name=business_name,
                business_type=business_type
            )
            
            logger.info(f"K-Startup API 응답: {response.total_count}건 중 {response.current_count}건 조회")
            
            # 응답 데이터 처리
            if response.data:
                for item in response.data:
                    try:
                        # K-Startup 응답을 우리 모델에 맞게 변환
                        announcement_data = self._transform_kstartup_data(item)
                        
                        # 중복 체크
                        business_id = announcement_data.get("business_id")
                        business_name_val = announcement_data.get("business_name")
                        
                        # 중복 체크 수행
                        is_duplicate = self.repository.check_duplicate(
                            business_id=business_id,
                            business_name=business_name_val
                        )
                        
                        if is_duplicate:
                            logger.info(f"중복 데이터 스킵: {business_name_val}")
                            continue
                        
                        # 새 공고 생성
                        announcement_create = AnnouncementCreate(
                            announcement_data=announcement_data,
                            source_url=f"K-Startup-사업공고-{business_id or 'unknown'}"
                        )
                        
                        # Repository를 통해 저장
                        announcement = self.repository.create(announcement_create)
                        announcements.append(announcement)
                        
                        logger.info(f"새로운 사업공고 저장: {business_name_val}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"K-Startup API 호출 실패: {e}")
            # API 호출 실패시 빈 리스트 반환
            
        return announcements
    
    def _transform_kstartup_data(self, kstartup_item: KStartupAnnouncementResponse) -> dict:
        """K-Startup API 응답을 내부 모델로 변환"""
        # KStartupAnnouncementResponse 모델의 필드를 사용
        
        # 모집기간 설정
        recruitment_period = ""
        if kstartup_item.announcement_start_date and kstartup_item.announcement_end_date:
            recruitment_period = f"{kstartup_item.announcement_start_date} ~ {kstartup_item.announcement_end_date}"
        elif kstartup_item.announcement_start_date:
            recruitment_period = f"{kstartup_item.announcement_start_date} ~"
        elif kstartup_item.announcement_end_date:
            recruitment_period = f"~ {kstartup_item.announcement_end_date}"
        
        # 지원 대상 정보 구성
        support_target = ""
        if kstartup_item.support_target:
            support_target = kstartup_item.support_target
        elif kstartup_item.support_target_content:
            support_target = kstartup_item.support_target_content
        
        # 신청 방법 정보 구성
        application_method = ""
        if kstartup_item.application_method_online:
            application_method = kstartup_item.application_method_online
        elif kstartup_item.business_guide_url:
            application_method = f"온라인 접수 - {kstartup_item.business_guide_url}"
        else:
            application_method = "온라인 접수"
        
        return {
            "business_id": kstartup_item.announcement_serial_number or str(kstartup_item.id) if kstartup_item.id else None,
            "business_name": kstartup_item.integrated_announcement_business_name or kstartup_item.business_announcement_name,
            "business_type": kstartup_item.support_business_classification or "창업지원",
            "business_overview": kstartup_item.announcement_content or kstartup_item.integrated_announcement_business_name,
            "support_target": support_target,
            "recruitment_period": recruitment_period,
            "application_method": application_method,
            "contact_info": kstartup_item.announcement_enterprise_name or kstartup_item.business_department_name,
            "announcement_date": kstartup_item.announcement_start_date,
            "deadline": kstartup_item.announcement_end_date,
            "status": "모집중" if kstartup_item.recruitment_progress_yn == "Y" else "모집종료"
        }
    
    # 이전 레거시 메서드들은 향후 제거 예정 (K-Startup 클라이언트로 완전 마이그레이션 후)
    
    def get_announcements(
        self, 
        page: int = 1, 
        page_size: int = 20,
        is_active: bool = True
    ) -> PaginationResult[Announcement]:
        """저장된 사업공고 목록 조회 (페이지네이션)"""
        try:
            if is_active:
                return self.repository.find_active_announcements(page=page, page_size=page_size)
            else:
                filters = QueryFilter().eq("is_active", False)
                return self.repository.get_paginated(page=page, page_size=page_size, filters=filters)
        except Exception as e:
            logger.error(f"공고 목록 조회 오류: {e}")
            return PaginationResult(
                items=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    def get_announcement_by_id(self, announcement_id: str) -> Optional[Announcement]:
        """ID로 사업공고 조회"""
        try:
            return self.repository.get_by_id(announcement_id)
        except Exception as e:
            logger.error(f"공고 조회 오류: {e}")
            return None
    
    def create_announcement(self, announcement_data: AnnouncementCreate) -> Announcement:
        """새 사업공고 생성"""
        try:
            return self.repository.create(announcement_data)
        except Exception as e:
            logger.error(f"공고 생성 오류: {e}")
            raise
    
    def update_announcement(
        self, 
        announcement_id: str, 
        update_data: AnnouncementUpdate
    ) -> Optional[Announcement]:
        """사업공고 수정"""
        try:
            return self.repository.update_by_id(announcement_id, update_data)
        except Exception as e:
            logger.error(f"공고 수정 오류: {e}")
            return None
    
    def delete_announcement(self, announcement_id: str) -> bool:
        """사업공고 삭제 (비활성화)"""
        try:
            return self.repository.delete_by_id(announcement_id, soft_delete=True)
        except Exception as e:
            logger.error(f"공고 삭제 오류: {e}")
            return False
    
    # 추가 비즈니스 로직 메서드들
    def search_announcements(self, search_term: str) -> List[Announcement]:
        """공고 검색"""
        try:
            return self.repository.search_announcements(search_term)
        except Exception as e:
            logger.error(f"공고 검색 오류: {e}")
            return []
    
    def get_announcements_by_type(self, business_type: str) -> List[Announcement]:
        """사업 유형별 공고 조회"""
        try:
            return self.repository.find_by_business_type(business_type)
        except Exception as e:
            logger.error(f"유형별 공고 조회 오류: {e}")
            return []
    
    def get_recent_announcements(self, limit: int = 10) -> List[Announcement]:
        """최근 공고 조회"""
        try:
            return self.repository.get_recent_announcements(limit)
        except Exception as e:
            logger.error(f"최근 공고 조회 오류: {e}")
            return []
    
    def get_announcement_statistics(self) -> dict:
        """공고 통계 조회"""
        try:
            return self.repository.get_statistics()
        except Exception as e:
            logger.error(f"공고 통계 조회 오류: {e}")
            return {}