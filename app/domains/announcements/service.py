from typing import List, Optional
from .models import Announcement, AnnouncementCreate, AnnouncementUpdate
from ...shared.clients.public_data_client import PublicDataAPIClient
from ...core.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class AnnouncementService:
    """사업공고 서비스"""
    
    def __init__(self, db=None):
        self.db = db or get_database()
        self.collection = self.db.announcements
    
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
                        
                        # 중복 체크 - business_id 또는 business_name으로 중복 확인
                        business_id = announcement_data.get("business_id")
                        business_name = announcement_data.get("business_name")
                        
                        # 중복 체크 임시 비활성화 - 강제 저장
                        logger.info(f"강제 저장 시도: {announcement_data.get('business_name')}")
                        
                        # 새 공고 저장
                        announcement = Announcement(
                            announcement_data=announcement_data,
                            source_url=f"공공데이터포털-사업공고-{business_id or 'unknown'}"
                        )
                        
                        # dict()로 변환 시 _id 필드 제거 (MongoDB가 자동 생성하도록)
                        announcement_dict = announcement.dict(by_alias=True, exclude={"id"})
                        result = self.collection.insert_one(announcement_dict)
                        announcement.id = str(result.inserted_id)
                        announcements.append(announcement)
                        
                        logger.info(f"새로운 사업공고 저장: {announcement_data.get('business_name')}")
                        
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
        skip: int = 0, 
        limit: int = 20,
        is_active: bool = True
    ) -> List[Announcement]:
        """저장된 사업공고 목록 조회"""
        cursor = self.collection.find({"is_active": is_active}).skip(skip).limit(limit)
        announcements = []
        for doc in cursor:
            # ObjectId를 문자열로 변환하고 id 필드로 설정
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                # _id 필드는 제거하여 중복 방지
                del doc["_id"]
            announcements.append(Announcement(**doc))
        return announcements
    
    def get_announcement_by_id(self, announcement_id: str) -> Optional[Announcement]:
        """ID로 사업공고 조회"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(announcement_id)})
            if doc:
                # ObjectId를 문자열로 변환하고 id 필드로 설정
                doc["id"] = str(doc["_id"])
                # _id 필드는 제거하여 중복 방지
                del doc["_id"]
                return Announcement(**doc)
            return None
        except Exception:
            return None
    
    def create_announcement(self, announcement_data: AnnouncementCreate) -> Announcement:
        """새 사업공고 생성"""
        announcement = Announcement(**announcement_data.dict())
        # dict()로 변환 시 _id 필드 제거 (MongoDB가 자동 생성하도록)
        announcement_dict = announcement.dict(by_alias=True, exclude={"id"})
        result = self.collection.insert_one(announcement_dict)
        announcement.id = str(result.inserted_id)
        return announcement
    
    def update_announcement(
        self, 
        announcement_id: str, 
        update_data: AnnouncementUpdate
    ) -> Optional[Announcement]:
        """사업공고 수정"""
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        if not update_dict:
            return None
            
        try:
            self.collection.update_one(
                {"_id": ObjectId(announcement_id)},
                {"$set": update_dict}
            )
            return self.get_announcement_by_id(announcement_id)
        except Exception:
            return None
    
    def delete_announcement(self, announcement_id: str) -> bool:
        """사업공고 삭제 (비활성화)"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(announcement_id)},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except Exception:
            return False