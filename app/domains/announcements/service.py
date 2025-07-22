from typing import List, Optional
from .models import Announcement, AnnouncementCreate, AnnouncementUpdate
from .repository import AnnouncementRepository
from ...shared.clients.public_data_client import PublicDataAPIClient
from ...core.interfaces.base_repository import QueryFilter, PaginationResult
import logging

logger = logging.getLogger(__name__)


class AnnouncementService:
    """사업공고 서비스"""
    
    def __init__(self, repository: AnnouncementRepository):
        self.repository = repository
    
    def fetch_and_save_announcements(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> List[Announcement]:
        """공공데이터에서 사업공고 정보를 가져와 저장"""
        announcements = []
        
        try:
            # 공공데이터 API 호출
            with PublicDataAPIClient() as client:
                response = client.get_announcement_information(
                    page_no=page_no,
                    num_of_rows=num_of_rows,
                    business_name=business_name,
                    business_type=business_type
                )
                
                logger.info(f"API 응답: {response.total_count}건 중 {response.current_count}건 조회")
                
                # 응답 데이터 처리
                for item in response.data:
                    try:
                        # 공공데이터 응답을 우리 모델에 맞게 변환
                        announcement_data = self._transform_api_data(item)
                        
                        # 중복 체크
                        business_id = announcement_data.get("business_id")
                        business_name = announcement_data.get("business_name")
                        
                        # 중복 체크 수행
                        is_duplicate = self.repository.check_duplicate(
                            business_id=business_id,
                            business_name=business_name
                        )
                        
                        if is_duplicate:
                            logger.info(f"중복 데이터 스킵: {business_name}")
                            continue
                        
                        # 새 공고 생성
                        announcement_create = AnnouncementCreate(
                            announcement_data=announcement_data,
                            source_url=f"공공데이터포털-사업공고-{business_id or 'unknown'}"
                        )
                        
                        # Repository를 통해 저장
                        announcement = self.repository.create(announcement_create)
                        announcements.append(announcement)
                        
                        logger.info(f"새로운 사업공고 저장: {business_name}")
                        
                    except Exception as e:
                        logger.error(f"데이터 변환/저장 오류: {e}, 데이터: {item}")
                        continue
                        
        except Exception as e:
            logger.error(f"공공데이터 API 호출 실패: {e}")
            # API 호출 실패시 빈 리스트 반환
            
        return announcements
    
    def _transform_api_data(self, api_item: dict) -> dict:
        """공공데이터 API 응답을 내부 모델로 변환"""
        # XML에서 파싱된 실제 필드명에 맞게 매핑
        # 로그에서 확인한 실제 응답 필드를 기반으로 매핑
        
        business_name = (api_item.get("intg_pbanc_biz_nm") or 
                        api_item.get("biz_pbanc_nm") or 
                        api_item.get("biz_nm"))
        
        # 지원대상 정보 통합
        support_target = (api_item.get("aply_trgt") or 
                         api_item.get("aply_trgt_ctnt") or 
                         api_item.get("sprt_trgt"))
        
        # 신청 방법 통합
        application_method = (api_item.get("aply_mthd_onli_rcpt_istc") or 
                             api_item.get("biz_gdnc_url") or 
                             api_item.get("biz_aply_url") or "온라인 접수")
        
        # 모집기간 설정
        start_date = api_item.get("pbanc_rcpt_bgng_dt", "")
        end_date = api_item.get("pbanc_rcpt_end_dt", "")
        recruitment_period = ""
        if start_date or end_date:
            recruitment_period = f"{start_date} ~ {end_date}".strip(' ~')
        
        return {
            "business_id": api_item.get("pbanc_sn") or api_item.get("id"),  # 사업공고 일련번호 사용
            "business_name": business_name,
            "business_type": api_item.get("supt_biz_clsfc") or "창업지원",  # 지원사업분류
            "business_overview": api_item.get("pbanc_ctnt") or business_name,  # 공고내용
            "support_target": support_target,
            "recruitment_period": recruitment_period,
            "application_method": application_method,
            "contact_info": api_item.get("pbanc_ntrp_nm") or api_item.get("biz_prch_dprt_nm"),
            "announcement_date": self._parse_date(api_item.get("pbanc_rcpt_bgng_dt")),
            "deadline": self._parse_date(api_item.get("pbanc_rcpt_end_dt")),
            "status": "모집중" if api_item.get("rcrt_prgs_yn") == "Y" else "모집종료"
        }
    
    def _parse_date(self, date_str):
        """날짜 문자열을 datetime 객체로 변환"""
        if not date_str:
            return None
        try:
            # 다양한 날짜 형식 처리 (실제 API 응답에 맞게 조정)
            from datetime import datetime
            if isinstance(date_str, str):
                # YYYYMMDD 형식 처리
                if len(date_str) == 8 and date_str.isdigit():
                    return datetime.strptime(date_str, "%Y%m%d")
                # YYYY-MM-DD 형식 처리
                elif "-" in date_str:
                    return datetime.strptime(date_str[:10], "%Y-%m-%d")
            return None
        except Exception:
            return None
    
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