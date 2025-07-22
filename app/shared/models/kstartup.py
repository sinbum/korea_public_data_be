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
    """K-Startup 사업 구분 코드"""
    CMRCZN_TAB1 = "cmrczn_Tab1"  # R&D
    CMRCZN_TAB2 = "cmrczn_Tab2"  # 창업교육
    CMRCZN_TAB3 = "cmrczn_Tab3"  # 창업사업화
    CMRCZN_TAB4 = "cmrczn_Tab4"  # 판로개척
    CMRCZN_TAB5 = "cmrczn_Tab5"  # 창업인프라
    CMRCZN_TAB6 = "cmrczn_Tab6"  # 창업정책자금
    CMRCZN_TAB7 = "cmrczn_Tab7"  # 기타


class ContentTypeCode(str, Enum):
    """K-Startup 콘텐츠 구분 코드"""
    CONTENT_TAB1 = "content_Tab1"  # 뉴스
    CONTENT_TAB2 = "content_Tab2"  # 정책정보
    CONTENT_TAB3 = "content_Tab3"  # 교육정보
    CONTENT_TAB4 = "content_Tab4"  # 행사정보
    CONTENT_TAB5 = "content_Tab5"  # 기타정보


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
    """사업공고 정보 모델"""
    
    # 기본 정보
    announcement_id: Optional[str] = Field(None, alias="pbanc_no", description="공고번호")
    title: Optional[str] = Field(None, alias="pbanc_titl_nm", description="공고제목")
    content: Optional[str] = Field(None, alias="pbanc_cn", description="공고내용")
    
    # 일정 정보
    announcement_date: Optional[str] = Field(None, alias="pbanc_de", description="공고일자")
    start_date: Optional[str] = Field(None, alias="reqst_bgng_ymd", description="신청시작일")
    end_date: Optional[str] = Field(None, alias="reqst_end_ymd", description="신청종료일")
    
    # 사업 정보
    business_category: Optional[str] = Field(None, alias="biz_category_cd", description="사업구분코드")
    business_name: Optional[str] = Field(None, alias="supt_biz_titl_nm", description="지원사업명")
    support_target: Optional[str] = Field(None, alias="biz_supt_trgt_info", description="지원대상")
    
    # 기관 정보
    organization: Optional[str] = Field(None, alias="excutr_instt_nm", description="수행기관명")
    contact_info: Optional[str] = Field(None, alias="qustnr_info", description="문의처정보")
    
    # 기타
    url: Optional[str] = Field(None, alias="relm_url", description="관련URL")
    attachment: Optional[str] = Field(None, alias="atch_file_nm", description="첨부파일명")
    
    @validator('announcement_date', 'start_date', 'end_date', pre=True)
    def validate_date_format(cls, v):
        """날짜 형식 검증"""
        if v and isinstance(v, str):
            # Remove common invalid characters
            v = v.replace('/', '-').replace('.', '-')
            # Basic format validation
            if len(v) == 8 and v.isdigit():
                # Convert YYYYMMDD to YYYY-MM-DD
                return f"{v[:4]}-{v[4:6]}-{v[6:8]}"
        return v
    
    @validator('url', pre=True)
    def validate_url(cls, v):
        """URL 형식 기본 검증"""
        if v and isinstance(v, str):
            if not (v.startswith('http://') or v.startswith('https://')):
                return f"http://{v}" if v else None
        return v


class BusinessItem(BaseKStartupItem):
    """사업정보 모델"""
    
    # 기본 정보
    business_id: Optional[str] = Field(None, alias="biz_no", description="사업번호")
    business_name: Optional[str] = Field(None, alias="supt_biz_titl_nm", description="지원사업명")
    business_content: Optional[str] = Field(None, alias="biz_cn", description="사업내용")
    
    # 분류 정보
    business_category: Optional[BusinessCategoryCode] = Field(None, alias="biz_category_cd", description="사업구분코드")
    business_field: Optional[str] = Field(None, alias="biz_field_nm", description="사업분야명")
    
    # 지원 정보
    support_target: Optional[str] = Field(None, alias="biz_supt_trgt_info", description="지원대상정보")
    support_content: Optional[str] = Field(None, alias="supt_cn", description="지원내용")
    support_scale: Optional[str] = Field(None, alias="supt_scl_info", description="지원규모정보")
    
    # 기관 정보
    organization: Optional[str] = Field(None, alias="excutr_instt_nm", description="수행기관명")
    organization_type: Optional[str] = Field(None, alias="excutr_instt_se_nm", description="수행기관구분명")
    contact_info: Optional[str] = Field(None, alias="qustnr_info", description="문의처정보")
    
    # 기타
    homepage_url: Optional[str] = Field(None, alias="hmpg_url", description="홈페이지URL")
    related_url: Optional[str] = Field(None, alias="relm_url", description="관련URL")
    
    @validator('homepage_url', 'related_url', pre=True)
    def validate_urls(cls, v):
        """URL 형식 검증"""
        if v and isinstance(v, str):
            if not (v.startswith('http://') or v.startswith('https://')):
                return f"http://{v}" if v else None
        return v


class ContentItem(BaseKStartupItem):
    """콘텐츠 정보 모델"""
    
    # 기본 정보
    content_id: Optional[str] = Field(None, alias="cn_no", description="콘텐츠번호")
    title: Optional[str] = Field(None, alias="cn_titl_nm", description="콘텐츠제목")
    content: Optional[str] = Field(None, alias="cn_cn", description="콘텐츠내용")
    summary: Optional[str] = Field(None, alias="cn_smry", description="콘텐츠요약")
    
    # 분류 정보
    content_type: Optional[ContentTypeCode] = Field(None, alias="cn_se_cd", description="콘텐츠구분코드")
    category: Optional[str] = Field(None, alias="ctgry_nm", description="카테고리명")
    
    # 일정 정보
    publish_date: Optional[str] = Field(None, alias="pblnt_de", description="발행일자")
    update_date: Optional[str] = Field(None, alias="updt_de", description="수정일자")
    
    # 기타
    author: Optional[str] = Field(None, alias="author_nm", description="작성자명")
    source: Optional[str] = Field(None, alias="source_nm", description="출처명")
    url: Optional[str] = Field(None, alias="relm_url", description="관련URL")
    thumbnail_url: Optional[str] = Field(None, alias="thmbnl_url", description="썸네일URL")
    
    @validator('publish_date', 'update_date', pre=True)
    def validate_date_format(cls, v):
        """날짜 형식 검증"""
        if v and isinstance(v, str):
            v = v.replace('/', '-').replace('.', '-')
            if len(v) == 8 and v.isdigit():
                return f"{v[:4]}-{v[4:6]}-{v[6:8]}"
        return v


class StatisticalItem(BaseKStartupItem):
    """통계 정보 모델"""
    
    # 기본 정보
    statistics_id: Optional[str] = Field(None, alias="stats_no", description="통계번호")
    title: Optional[str] = Field(None, alias="stats_titl_nm", description="통계제목")
    description: Optional[str] = Field(None, alias="stats_cn", description="통계내용")
    
    # 통계 데이터
    target_year: Optional[int] = Field(None, alias="trgt_year", description="대상년도")
    target_month: Optional[int] = Field(None, alias="trgt_month", description="대상월")
    statistics_value: Optional[str] = Field(None, alias="stats_vl", description="통계값")
    unit: Optional[str] = Field(None, alias="unt_nm", description="단위명")
    
    # 분류 정보
    category: Optional[str] = Field(None, alias="ctgry_nm", description="카테고리명")
    subcategory: Optional[str] = Field(None, alias="subctgry_nm", description="하위카테고리명")
    
    # 기타
    source: Optional[str] = Field(None, alias="source_nm", description="출처명")
    reference_date: Optional[str] = Field(None, alias="ref_de", description="기준일자")
    
    @validator('target_year', pre=True)
    def validate_year(cls, v):
        """년도 검증"""
        if v and isinstance(v, str) and v.isdigit():
            year = int(v)
            if 2000 <= year <= 2050:
                return year
        return v
    
    @validator('target_month', pre=True)
    def validate_month(cls, v):
        """월 검증"""
        if v and isinstance(v, str) and v.isdigit():
            month = int(v)
            if 1 <= month <= 12:
                return month
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