import httpx
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
from datetime import datetime
from ...core.config import settings
from ..models import PublicDataResponse, APIRequestLog

logger = logging.getLogger(__name__)


class PublicDataAPIClient:
    """창업진흥원 K-Startup 공공데이터 API 클라이언트"""
    
    def __init__(self):
        self.base_url = settings.api_base_url
        self.api_key = settings.public_data_api_key
        self.client = httpx.Client(timeout=30.0)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _build_params(self, **kwargs) -> Dict[str, Any]:
        """공통 파라미터 구성"""
        params = {
            "serviceKey": self.api_key,
            "numOfRows": kwargs.get("num_of_rows", 10),
            "pageNo": kwargs.get("page_no", 1),
            "type": "json"
        }
        
        # 추가 파라미터 병합
        additional_params = {k: v for k, v in kwargs.items() 
                           if k not in ["num_of_rows", "page_no"] and v is not None}
        params.update(additional_params)
        
        return params
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """API 요청 실행"""
        url = f"{self.base_url}/{endpoint}"
        start_time = datetime.utcnow()
        
        try:
            response = self.client.get(url, params=params)
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 요청 로그 기록 (실제 구현시 MongoDB에 저장)
            log_data = APIRequestLog(
                endpoint=endpoint,
                params=params,
                response_status=response.status_code,
                response_time=response_time
            )
            
            if response.status_code == 200:
                logger.info(f"API 요청 성공: {endpoint} (응답시간: {response_time:.2f}s)")
                # 응답 내용 로깅 (디버깅용)
                logger.info(f"응답 내용: {response.text[:500]}")
                try:
                    return response.json()
                except Exception as e:
                    logger.info(f"JSON 파싱 실패, XML 파싱 시도: {e}")
                    # XML 응답 파싱
                    try:
                        return self._parse_xml_response(response.text)
                    except Exception as xml_e:
                        logger.error(f"XML 파싱도 실패: {xml_e}, 응답: {response.text[:200]}")
                        # 빈 응답 구조 반환
                        return {
                            "currentCount": 0,
                            "matchCount": 0,
                            "page": params.get("pageNo", 1),
                            "perPage": params.get("numOfRows", 10),
                            "totalCount": 0,
                            "data": []
                        }
            else:
                error_msg = f"API 요청 실패: {response.status_code}"
                log_data.error_message = error_msg
                logger.error(f"{error_msg} - {endpoint}")
                raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)
                
        except httpx.TimeoutException:
            error_msg = "API 요청 타임아웃"
            logger.error(f"{error_msg} - {endpoint}")
            raise
        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {e} - {endpoint}")
            raise
    
    def _parse_xml_response(self, xml_text: str) -> Dict[str, Any]:
        """XML 응답을 JSON 형태로 변환"""
        try:
            root = ET.fromstring(xml_text)
            
            # currentCount, matchCount, totalCount 등 추출
            current_count = int(root.find('currentCount').text) if root.find('currentCount') is not None else 0
            match_count = int(root.find('matchCount').text) if root.find('matchCount') is not None else 0
            total_count = int(root.find('totalCount').text) if root.find('totalCount') is not None else 0
            
            # data 항목들 파싱
            data_items = []
            data_element = root.find('data')
            
            if data_element is not None:
                for item in data_element.findall('item'):
                    item_data = {}
                    for col in item.findall('col'):
                        name = col.get('name')
                        value = col.text if col.text else ""
                        item_data[name] = value
                    data_items.append(item_data)
            
            return {
                "currentCount": current_count,
                "matchCount": match_count,
                "page": 1,  # XML에서 page 정보가 없으므로 기본값
                "perPage": current_count,
                "totalCount": total_count,
                "data": data_items
            }
            
        except Exception as e:
            logger.error(f"XML 파싱 오류: {e}")
            raise
    
    def get_announcement_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> PublicDataResponse:
        """사업공고 정보 조회"""
        params = self._build_params(
            page_no=page_no,
            num_of_rows=num_of_rows,
            businessName=business_name,
            businessType=business_type
        )
        
        response_data = self._make_request("getAnnouncementInformation01", params)
        return PublicDataResponse(**response_data)
    
    def get_content_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        content_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> PublicDataResponse:
        """콘텐츠 정보 조회"""
        params = self._build_params(
            page_no=page_no,
            num_of_rows=num_of_rows,
            contentType=content_type,
            category=category
        )
        
        response_data = self._make_request("getContentInformation01", params)
        return PublicDataResponse(**response_data)
    
    def get_statistical_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> PublicDataResponse:
        """통계 정보 조회"""
        params = self._build_params(
            page_no=page_no,
            num_of_rows=num_of_rows,
            year=year,
            month=month
        )
        
        response_data = self._make_request("getStatisticalInformation01", params)
        return PublicDataResponse(**response_data)
    
    def get_business_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_field: Optional[str] = None,
        organization: Optional[str] = None
    ) -> PublicDataResponse:
        """사업 정보 조회"""
        params = self._build_params(
            page_no=page_no,
            num_of_rows=num_of_rows,
            businessField=business_field,
            organization=organization
        )
        
        response_data = self._make_request("getBusinessInformation01", params)
        return PublicDataResponse(**response_data)