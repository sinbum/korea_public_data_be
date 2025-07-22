"""
K-Startup API Client implementation using new architecture.

Implements BaseAPIClient with K-Startup specific data transformation.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import logging
import asyncio

from ...core.interfaces.base_api_client import (
    BaseAPIClient, 
    APIResponse, 
    RequestMethod
)
from ...core.interfaces.retry_strategies import (
    ExponentialBackoffStrategy,
    RetryCondition
)
from .strategies import GovernmentAPIKeyStrategy
from ...core.config import settings
from ..models.base import PublicDataResponse
from ..exceptions import (
    DataParsingError,
    DataTransformationError,
    APIResponseError
)

logger = logging.getLogger(__name__)


class KStartupAPIResponse(PublicDataResponse):
    """K-Startup specific API response model"""
    pass


class KStartupAPIClient(BaseAPIClient[KStartupAPIResponse]):
    """
    K-Startup API client implementing BaseAPIClient.
    
    Handles XML/JSON responses and K-Startup specific data formats.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        use_aggressive_retry: bool = False
    ):
        auth_strategy = GovernmentAPIKeyStrategy(
            api_key or settings.public_data_api_key
        )
        
        # Configure retry strategy for K-Startup API specifics
        if use_aggressive_retry:
            retry_strategy = ExponentialBackoffStrategy(
                max_attempts=5,
                base_delay=1.0,
                max_delay=60.0,
                multiplier=2.0,
                retry_conditions=[
                    RetryCondition.ON_SERVER_ERROR,
                    RetryCondition.ON_TIMEOUT,
                    RetryCondition.ON_NETWORK_ERROR,
                    RetryCondition.ON_RATE_LIMIT
                ]
            )
        else:
            retry_strategy = ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                retry_conditions=[
                    RetryCondition.ON_SERVER_ERROR,
                    RetryCondition.ON_TIMEOUT,
                    RetryCondition.ON_NETWORK_ERROR
                ]
            )
        
        super().__init__(
            base_url=settings.api_base_url,
            auth_strategy=auth_strategy,
            timeout=30,
            max_retries=3,
            retry_strategy=retry_strategy
        )
    
    def _preprocess_request(
        self,
        endpoint: str,
        method: RequestMethod,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """K-Startup specific request preprocessing"""
        request_params = super()._preprocess_request(
            endpoint, method, params, data, headers
        )
        
        # Add K-Startup specific parameters
        if params:
            # Convert Python parameter names to K-Startup API format
            converted_params = self._convert_param_names(params)
            request_params["params"].update(converted_params)
        
        # Always request JSON format
        request_params["params"]["type"] = "json"
        
        # Add K-Startup specific headers
        request_params["headers"].update({
            "Accept": "application/json,application/xml",
            "User-Agent": "KStartup-API-Client/1.0"
        })
        
        return request_params
    
    def _convert_param_names(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parameter names to K-Startup API format"""
        param_mapping = {
            "page_no": "pageNo",
            "num_of_rows": "numOfRows",
            "business_name": "businessName",
            "business_type": "businessType",
            "content_type": "contentType",
            "business_field": "businessField"
        }
        
        converted = {}
        for key, value in params.items():
            if value is not None:  # Skip None values
                api_key = param_mapping.get(key, key)
                converted[api_key] = value
        
        return converted
    
    def _transform_response(self, response_data: Dict[str, Any]) -> APIResponse[KStartupAPIResponse]:
        """Transform raw response to domain model"""
        try:
            content = response_data.get("content", "")
            status_code = response_data.get("status_code", 200)
            
            if status_code != 200:
                return APIResponse[KStartupAPIResponse](
                    success=False,
                    error=f"HTTP {status_code}",
                    status_code=status_code
                )
            
            # Try JSON first, then XML
            try:
                import json
                json_data = json.loads(content)
                parsed_data = self._process_json_response(json_data)
            except (json.JSONDecodeError, ValueError):
                # Fall back to XML parsing
                parsed_data = self._parse_response_data(content)
            
            # Create KStartupAPIResponse
            api_response_data = KStartupAPIResponse(**parsed_data)
            
            return APIResponse[KStartupAPIResponse](
                success=True,
                data=api_response_data,
                status_code=status_code,
                total_count=parsed_data.get("totalCount"),
                current_count=parsed_data.get("currentCount")
            )
            
        except Exception as e:
            logger.error(f"Response transformation failed: {e}")
            
            # Create specific exception based on error type
            if "json" in str(e).lower() or "xml" in str(e).lower():
                error_msg = f"Data parsing failed: {str(e)}"
                raise DataParsingError(
                    error_msg,
                    data_format="json/xml",
                    parser_type="KStartupAPIClient",
                    raw_content=response_data.get("content", "")
                )
            else:
                error_msg = f"Response transformation failed: {str(e)}"
                raise DataTransformationError(
                    error_msg,
                    source_format="http_response",
                    target_format="KStartupAPIResponse",
                    original_data=response_data
                )
    
    def _parse_response_data(self, content: str) -> List[Dict[str, Any]]:
        """Parse XML response content to structured data"""
        try:
            root = ET.fromstring(content)
            
            # Extract metadata
            current_count = self._get_xml_int_value(root, 'currentCount')
            match_count = self._get_xml_int_value(root, 'matchCount')
            total_count = self._get_xml_int_value(root, 'totalCount')
            page = self._get_xml_int_value(root, 'page', 1)
            per_page = self._get_xml_int_value(root, 'perPage', current_count)
            
            # Extract data items
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
            
            # Return only the data items to match the List[Dict[str, Any]] signature
            return data_items
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise DataParsingError(
                f"XML parsing failed: {str(e)}",
                data_format="xml",
                parser_type="ElementTree",
                raw_content=content
            )
    
    def _process_json_response(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON response data"""
        # Handle nested response structure that might come from K-Startup API
        if "response" in json_data:
            response_data = json_data["response"]
            if "body" in response_data:
                body_data = response_data["body"]
                return {
                    "currentCount": body_data.get("numOfRows", 0),
                    "matchCount": body_data.get("totalCount", 0),
                    "page": body_data.get("pageNo", 1),
                    "perPage": body_data.get("numOfRows", 0),
                    "totalCount": body_data.get("totalCount", 0),
                    "data": body_data.get("items", [])
                }
        
        # Direct data structure
        return json_data
    
    def _get_xml_int_value(self, root, tag_name: str, default: int = 0) -> int:
        """Safely extract integer value from XML element"""
        element = root.find(tag_name)
        if element is not None and element.text:
            try:
                return int(element.text)
            except ValueError:
                return default
        return default
    
    # Async methods for better performance
    async def async_get_announcement_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """사업공고 정보 조회 (비동기)"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "business_name": business_name,
            "business_type": business_type
        }
        
        async with self.async_client() as client:
            return await client.async_get("getAnnouncementInformation01", params)
    
    # Domain-specific methods (sync for backward compatibility)
    def get_announcement_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_name: Optional[str] = None,
        business_type: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """사업공고 정보 조회"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "business_name": business_name,
            "business_type": business_type
        }
        
        return self.get("getAnnouncementInformation01", params)
    
    async def async_get_content_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        content_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """콘텐츠 정보 조회 (비동기)"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "content_type": content_type,
            "category": category
        }
        
        async with self.async_client() as client:
            return await client.async_get("getContentInformation01", params)
    
    async def async_get_statistical_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """통계 정보 조회 (비동기)"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "year": year,
            "month": month
        }
        
        async with self.async_client() as client:
            return await client.async_get("getStatisticalInformation01", params)
    
    async def async_get_business_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_field: Optional[str] = None,
        organization: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """사업 정보 조회 (비동기)"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "business_field": business_field,
            "organization": organization
        }
        
        async with self.async_client() as client:
            return await client.async_get("getBusinessInformation01", params)
    
    def get_content_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        content_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """콘텐츠 정보 조회"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "content_type": content_type,
            "category": category
        }
        
        return self.get("getContentInformation01", params)
    
    def get_statistical_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """통계 정보 조회"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "year": year,
            "month": month
        }
        
        return self.get("getStatisticalInformation01", params)
    
    def get_business_information(
        self, 
        page_no: int = 1, 
        num_of_rows: int = 10,
        business_field: Optional[str] = None,
        organization: Optional[str] = None
    ) -> APIResponse[KStartupAPIResponse]:
        """사업 정보 조회"""
        params = {
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "business_field": business_field,
            "organization": organization
        }
        
        return self.get("getBusinessInformation01", params)
    
    # Batch processing method for improved performance
    async def get_all_data_batch(
        self,
        endpoints: List[str],
        params_list: List[Dict[str, Any]]
    ) -> List[APIResponse[KStartupAPIResponse]]:
        """배치로 여러 API 엔드포인트에서 데이터 조회"""
        if len(endpoints) != len(params_list):
            raise ValueError("Endpoints and params lists must have same length")
        
        async with self.async_client() as client:
            tasks = [
                client.async_get(endpoint, params)
                for endpoint, params in zip(endpoints, params_list)
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)