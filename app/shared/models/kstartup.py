"""
K-Startup API specific data models with validation.

Provides pydantic models for K-Startup API responses with comprehensive validation.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Union, Any, Dict
from datetime import datetime
from enum import Enum

from .base import PublicDataResponse
from ..exceptions import DataValidationError


class BusinessCategoryCode(str, Enum):
    """K-Startup 사업 구분 코드 (실제 API 응답 기반)"""
    # 실제 supt_biz_clsfc 필드에서 사용되는 한글 값들
    SAUPAHWA = "사업화"                              # 사업화 지원
    MENTORING_CONSULTING_EDU = "멘토링ㆍ컨설팅ㆍ교육"    # 멘토링, 컨설팅, 교육
    EVENT_NETWORK = "행사ㆍ네트워크"                   # 행사 및 네트워킹  
    FACILITY_SPACE_INCUBATION = "시설ㆍ공간ㆍ보육"     # 시설, 공간, 보육
    LOAN = "융자"                                    # 융자 지원
    MARKET_GLOBAL = "판로ㆍ해외진출"                  # 판로 개척 및 해외진출
    # 추가로 발견될 수 있는 분류들 (확장 가능)
    RND = "기술개발ㆍR&D"                             # R&D (예상)
    MANPOWER = "인력"                                # 인력 지원 (예상)
    GLOBAL = "글로벌"                                # 글로벌 전용 (예상)


class ContentTypeCode(str, Enum):
    """K-Startup 콘텐츠 구분 코드 (실제 API clss_cd 기반)"""
    # docs/content-category-codes.md 및 실제 API 응답 기준
    NOTICE_MATR = "notice_matr"           # 정책 및 규제정보(공지사항)
    FND_SCS_CASE = "fnd_scs_case"         # 창업우수사례
    KSTARTUP_ISSE_TRD = "kstartup_isse_trd"  # 생태계 이슈, 동향


class BaseKStartupItem(BaseModel):
    """K-Startup API 응답 아이템 기본 클래스"""
    
    class Config:
        """Pydantic 설정"""
        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True
        extra = "allow"  # Allow additional fields from API
    
    @validator('*', pre=True)
    def empty_str_to_none(cls, v):
        """빈 문자열을 None으로 변환"""
        if v == '' or v == 'null' or v == 'NULL':
            return None
        return v


class AnnouncementItem(BaseKStartupItem):
    """사업공고 정보 모델 (실제 API 응답 기반)"""
    
    # 기본 정보 (실제 XML 필드명으로 수정)
    announcement_id: Optional[str] = Field(None, alias="pbanc_sn", description="공고번호")
    title: Optional[str] = Field(None, alias="biz_pbanc_nm", description="사업공고명")
    content: Optional[str] = Field(None, alias="pbanc_ctnt", description="공고내용")
    
    # 일정 정보 (실제 필드명으로 수정)
    start_date: Optional[str] = Field(None, alias="pbanc_rcpt_bgng_dt", description="공고접수시작일")
    end_date: Optional[str] = Field(None, alias="pbanc_rcpt_end_dt", description="공고접수종료일")
    
    # 사업 정보 (실제 필드명으로 수정)
    business_category: Optional[str] = Field(None, alias="supt_biz_clsfc", description="지원사업구분")
    integrated_business_name: Optional[str] = Field(None, alias="intg_pbanc_biz_nm", description="통합공고사업명")
    
    # 대상 정보 (새로 추가된 실제 필드들)
    application_target: Optional[str] = Field(None, alias="aply_trgt", description="신청대상")
    application_target_content: Optional[str] = Field(None, alias="aply_trgt_ctnt", description="신청대상내용")
    application_exclusion_content: Optional[str] = Field(None, alias="aply_excl_trgt_ctnt", description="신청제외대상내용")
    business_entry: Optional[str] = Field(None, alias="biz_enyy", description="사업참여년수")
    business_target_age: Optional[str] = Field(None, alias="biz_trgt_age", description="사업대상연령")
    support_region: Optional[str] = Field(None, alias="supt_regin", description="지원지역")
    
    # 기관 정보 (실제 필드명으로 수정)
    organization: Optional[str] = Field(None, alias="pbanc_ntrp_nm", description="공고기업명")
    supervising_institution: Optional[str] = Field(None, alias="sprv_inst", description="감독기관")
    contact_department: Optional[str] = Field(None, alias="biz_prch_dprt_nm", description="사업추진부서명")
    contact_number: Optional[str] = Field(None, alias="prch_cnpl_no", description="추진연락처번호")
    
    # URL 정보 (새로 추가된 실제 필드들)
    detail_page_url: Optional[str] = Field(None, alias="detl_pg_url", description="상세페이지URL")
    business_guidance_url: Optional[str] = Field(None, alias="biz_gdnc_url", description="사업안내URL") 
    business_application_url: Optional[str] = Field(None, alias="biz_aply_url", description="사업신청URL")
    
    # 신청방법 정보 (새로 추가)
    online_reception: Optional[str] = Field(None, alias="aply_mthd_onli_rcpt_istc", description="온라인접수처")
    visit_reception: Optional[str] = Field(None, alias="aply_mthd_vst_rcpt_istc", description="방문접수처")
    email_reception: Optional[str] = Field(None, alias="aply_mthd_eml_rcpt_istc", description="이메일접수처")
    fax_reception: Optional[str] = Field(None, alias="aply_mthd_fax_rcpt_istc", description="팩스접수처")
    postal_reception: Optional[str] = Field(None, alias="aply_mthd_pssr_rcpt_istc", description="우편접수처")
    other_reception: Optional[str] = Field(None, alias="aply_mthd_etc_istc", description="기타접수처")
    
    # 상태 정보 (새로 추가)
    integrated_announcement: Optional[str] = Field(None, alias="intg_pbanc_yn", description="통합공고여부")
    recruitment_progress: Optional[str] = Field(None, alias="rcrt_prgs_yn", description="모집진행여부")
    performance_material: Optional[str] = Field(None, alias="prfn_matr", description="수행자료")
    
    # ID 정보 (API 응답에 포함)
    id: Optional[str] = Field(None, alias="id", description="ID")
    
    @validator('start_date', 'end_date', pre=True)
    def validate_date_format(cls, v):
        """날짜 형식 검증 (YYYYMMDD → YYYY-MM-DD)"""
        if v and isinstance(v, str):
            # Remove common invalid characters
            v = v.replace('/', '-').replace('.', '-')
            # Basic format validation
            if len(v) == 8 and v.isdigit():
                # Convert YYYYMMDD to YYYY-MM-DD
                return f"{v[:4]}-{v[4:6]}-{v[6:8]}"
        return v
    
    @validator('detail_page_url', 'business_guidance_url', 'business_application_url', 
               'online_reception', pre=True)
    def validate_url_fields(cls, v):
        """URL 필드 형식 기본 검증"""
        if v and isinstance(v, str):
            # Skip if already has protocol
            if v.startswith(('http://', 'https://')):
                return v
            # Skip if it's just a domain without protocol
            if v.startswith('www.') or '.' in v:
                return f"https://{v}" if v else None
        return v


class BusinessItem(BaseKStartupItem):
    """사업정보 모델 (실제 API 응답 기반 - 완전한 필드 매핑)"""
    
    # 기본 정보 (API 명세서 기반)
    business_category: Optional[str] = Field(None, alias="biz_category_cd", description="사업구분코드")
    business_name: Optional[str] = Field(None, alias="supt_biz_titl_nm", description="지원사업제목명")
    support_target: Optional[str] = Field(None, alias="biz_supt_trgt_info", description="사업지원대상정보")
    support_budget: Optional[str] = Field(None, alias="biz_supt_bdgt_info", description="사업지원예산정보")
    support_content: Optional[str] = Field(None, alias="biz_supt_ctnt", description="사업지원내용")
    business_feature: Optional[str] = Field(None, alias="supt_biz_chrct", description="지원사업특징")
    business_intro: Optional[str] = Field(None, alias="supt_biz_intrd_info", description="지원사업소개정보")
    business_year: Optional[str] = Field(None, alias="biz_yr", description="사업연도")
    detail_page_url: Optional[str] = Field(None, alias="Detl_pg_url", description="상세페이지URL")
    
    # 추가 필드들 (API 명세서에서 누락된 필드들)
    host_organization: Optional[str] = Field(None, alias="host_org", description="주최기관")
    supervising_institution: Optional[str] = Field(None, alias="sprv_inst", description="감독기관")
    contact_department: Optional[str] = Field(None, alias="contact_dept", description="담당부서")
    contact_phone: Optional[str] = Field(None, alias="contact_tel", description="연락처")
    contact_email: Optional[str] = Field(None, alias="contact_email", description="이메일")
    
    # 지원 관련 추가 정보
    application_period: Optional[str] = Field(None, alias="aply_period", description="신청기간")
    selection_criteria: Optional[str] = Field(None, alias="slctn_criteria", description="선정기준")
    selection_method: Optional[str] = Field(None, alias="slctn_method", description="선정방법")
    
    # 메타데이터
    created_date: Optional[str] = Field(None, alias="create_dt", description="생성일시")
    updated_date: Optional[str] = Field(None, alias="update_dt", description="수정일시")
    
    # ID 정보
    id: Optional[str] = Field(None, alias="id", description="ID")
    
    @validator('business_year', pre=True)
    def validate_year(cls, v):
        """사업연도 검증"""
        if v and isinstance(v, str) and v.isdigit():
            year = int(v)
            if 2000 <= year <= 2050:
                return v
        return v
    
    @validator('detail_page_url', pre=True)
    def validate_url(cls, v):
        """URL 형식 기본 검증"""
        if v and isinstance(v, str):
            if v.startswith(('http://', 'https://')):
                return v
            if v.startswith('www.') or '.' in v:
                return f"https://{v}" if v else None
        return v


class ContentItem(BaseKStartupItem):
    """콘텐츠 정보 모델 (실제 API 응답 기반 - 완전한 필드 매핑)"""
    
    # 기본 정보 (API 명세서 기반)
    content_type: Optional[str] = Field(None, alias="clss_cd", description="콘텐츠구분코드")
    title: Optional[str] = Field(None, alias="titl_nm", description="제목명")
    register_date: Optional[str] = Field(None, alias="fstm_reg_dt", description="최초등록일시")
    view_count: Optional[int] = Field(None, alias="view_cnt", description="조회수")
    detail_page_url: Optional[str] = Field(None, alias="detl_pg_url", description="상세페이지URL")
    file_name: Optional[str] = Field(None, alias="file_nm", description="파일명")
    
    # 추가 필드들 (API 명세서에서 확인 가능한 필드들)
    content_summary: Optional[str] = Field(None, alias="summary", description="콘텐츠 요약")
    content_body: Optional[str] = Field(None, alias="ctnt", description="콘텐츠 본문")
    category: Optional[str] = Field(None, alias="category_nm", description="카테고리명")
    tags: Optional[str] = Field(None, alias="tag_list", description="태그목록")
    author: Optional[str] = Field(None, alias="author_nm", description="작성자명")
    
    # 메타데이터
    update_date: Optional[str] = Field(None, alias="last_mdfcn_dt", description="최종수정일시")
    publish_status: Optional[str] = Field(None, alias="pblctn_sttus", description="공개상태")
    
    # ID 정보
    id: Optional[str] = Field(None, alias="id", description="ID")
    
    @validator('register_date', pre=True)
    def validate_date_format(cls, v):
        """날짜시간 형식 검증 (YYYY-MM-DD HH:MM:SS)"""
        if v and isinstance(v, str):
            # 이미 올바른 형식인 경우 그대로 반환
            if ' ' in v and ':' in v:
                return v
            # YYYYMMDD 형식인 경우 변환
            if len(v) == 8 and v.isdigit():
                return f"{v[:4]}-{v[4:6]}-{v[6:8]} 00:00:00"
        return v
    
    @validator('view_count', pre=True)
    def validate_view_count(cls, v):
        """조회수 검증"""
        if v and isinstance(v, str) and v.isdigit():
            return int(v)
        return v if isinstance(v, int) else None
    
    @validator('detail_page_url', pre=True)
    def validate_url(cls, v):
        """URL 형식 기본 검증"""
        if v and isinstance(v, str):
            if v.startswith(('http://', 'https://')):
                return v
            if v.startswith('www.') or '.' in v:
                return f"https://{v}" if v else None
        return v


class StatisticalItem(BaseKStartupItem):
    """통계 정보 모델 (실제 API 응답 기반 - 완전한 필드 매핑)"""
    
    # 기본 정보 (API 명세서 기반)
    title: Optional[str] = Field(None, alias="titl_nm", description="통계자료명")
    content: Optional[str] = Field(None, alias="ctnt", description="통계자료내용")
    register_date: Optional[str] = Field(None, alias="fstm_reg_dt", description="최초등록일시")
    modify_date: Optional[str] = Field(None, alias="last_mdfcn_dt", description="최종수정일시")
    detail_page_url: Optional[str] = Field(None, alias="detl_pg_url", description="상세페이지URL")
    file_name: Optional[str] = Field(None, alias="file_nm", description="다운로드파일명")
    
    # 추가 필드들 (API 명세서 기반)
    category: Optional[str] = Field(None, alias="category_nm", description="통계분류")
    data_type: Optional[str] = Field(None, alias="data_type", description="데이터타입")
    statistics_year: Optional[str] = Field(None, alias="stats_yr", description="통계기준년도")
    organization: Optional[str] = Field(None, alias="org_nm", description="작성기관")
    contact_info: Optional[str] = Field(None, alias="contact_info", description="문의처")
    
    # 메타데이터
    download_count: Optional[int] = Field(None, alias="dwnld_cnt", description="다운로드수")
    view_count: Optional[int] = Field(None, alias="view_cnt", description="조회수")
    file_size: Optional[str] = Field(None, alias="file_size", description="파일크기")
    
    # ID 정보
    id: Optional[str] = Field(None, alias="id", description="ID")
    
    @validator('register_date', 'modify_date', pre=True)
    def validate_date_format(cls, v):
        """날짜시간 형식 검증 (YYYY-MM-DD HH:MM:SS)"""
        if v and isinstance(v, str):
            # 이미 올바른 형식인 경우 그대로 반환
            if ' ' in v and ':' in v:
                return v
            # YYYYMMDD 형식인 경우 변환
            if len(v) == 8 and v.isdigit():
                return f"{v[:4]}-{v[4:6]}-{v[6:8]} 00:00:00"
        return v
    
    @validator('detail_page_url', pre=True)
    def validate_url(cls, v):
        """URL 형식 기본 검증"""
        if v and isinstance(v, str):
            if v.startswith(('http://', 'https://')):
                return v
            if v.startswith('www.') or '.' in v:
                return f"https://{v}" if v else None
        return v


# API 응답 래퍼 클래스들
class KStartupAnnouncementResponse(PublicDataResponse):
    """사업공고 API 응답"""
    data: List[AnnouncementItem]
    
    @validator('data', pre=True)
    def validate_data_items(cls, v):
        """데이터 아이템 검증"""
        if not isinstance(v, list):
            raise DataValidationError("Response data must be a list")
        
        validated_items = []
        for item in v:
            try:
                if isinstance(item, dict):
                    validated_items.append(AnnouncementItem(**item))
                else:
                    validated_items.append(item)
            except Exception as e:
                # Log validation error but continue processing
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to validate announcement item: {e}")
                
        return validated_items


class KStartupBusinessResponse(PublicDataResponse):
    """사업정보 API 응답"""
    data: List[BusinessItem]
    
    @validator('data', pre=True)
    def validate_data_items(cls, v):
        """데이터 아이템 검증"""
        if not isinstance(v, list):
            raise DataValidationError("Response data must be a list")
        
        validated_items = []
        for item in v:
            try:
                if isinstance(item, dict):
                    validated_items.append(BusinessItem(**item))
                else:
                    validated_items.append(item)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to validate business item: {e}")
                
        return validated_items


class KStartupContentResponse(PublicDataResponse):
    """콘텐츠 API 응답"""
    data: List[ContentItem]
    
    @validator('data', pre=True)
    def validate_data_items(cls, v):
        """데이터 아이템 검증"""
        if not isinstance(v, list):
            raise DataValidationError("Response data must be a list")
        
        validated_items = []
        for item in v:
            try:
                if isinstance(item, dict):
                    validated_items.append(ContentItem(**item))
                else:
                    validated_items.append(item)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to validate content item: {e}")
                
        return validated_items


class KStartupStatisticsResponse(PublicDataResponse):
    """통계정보 API 응답"""
    data: List[StatisticalItem]
    
    @validator('data', pre=True)
    def validate_data_items(cls, v):
        """데이터 아이템 검증"""
        if not isinstance(v, list):
            raise DataValidationError("Response data must be a list")
        
        validated_items = []
        for item in v:
            try:
                if isinstance(item, dict):
                    validated_items.append(StatisticalItem(**item))
                else:
                    validated_items.append(item)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to validate statistical item: {e}")
                
        return validated_items


# Union type for all K-Startup responses
KStartupAPIResponse = Union[
    KStartupAnnouncementResponse,
    KStartupBusinessResponse, 
    KStartupContentResponse,
    KStartupStatisticsResponse
]


# Utility functions for data validation
def validate_kstartup_response_data(
    data: Dict[str, Any], 
    response_type: str
) -> KStartupAPIResponse:
    """
    K-Startup API 응답 데이터 검증 및 변환
    
    Args:
        data: Raw response data
        response_type: Type of response (announcements, business, content, statistics)
        
    Returns:
        Validated response model
        
    Raises:
        DataValidationError: If validation fails
    """
    try:
        if response_type == "announcements":
            return KStartupAnnouncementResponse(**data)
        elif response_type == "business":
            return KStartupBusinessResponse(**data)
        elif response_type == "content":
            return KStartupContentResponse(**data)
        elif response_type == "statistics":
            return KStartupStatisticsResponse(**data)
        else:
            raise DataValidationError(f"Unknown response type: {response_type}")
            
    except Exception as e:
        raise DataValidationError(
            f"Failed to validate {response_type} response: {str(e)}",
            field_name=response_type
        )