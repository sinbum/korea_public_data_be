"""
K-Startup API Client implementation using new architecture.

Implements BaseAPIClient with K-Startup specific data transformation.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import logging

from ...core.interfaces.base_api_client import (
    BaseAPIClient, 
    APIResponse, 
    AuthenticationStrategy,
    APIKeyAuthStrategy
)
from ...core.config import settings
from ..models.base import PublicDataResponse

logger = logging.getLogger(__name__)


class KStartupAPIResponse(PublicDataResponse):
    """K-Startup specific API response model"""
    pass


class KStartupAPIClient(BaseAPIClient[KStartupAPIResponse]):
    """
    K-Startup API client implementing BaseAPIClient.
    
    Handles XML/JSON responses and K-Startup specific data formats.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        auth_strategy = APIKeyAuthStrategy(
            api_key or settings.public_data_api_key,
            "serviceKey"
        )
        
        super().__init__(
            base_url=settings.api_base_url,
            auth_strategy=auth_strategy,
            timeout=30,
            max_retries=3
        )
    
    def _preprocess_request(
        self,
        endpoint: str,
        method,
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
            return APIResponse[KStartupAPIResponse](
                success=False,
                error=f"Response transformation failed: {str(e)}",
                status_code=response_data.get("status_code", 500)
            )
    
    def _parse_response_data(self, content: str) -> Dict[str, Any]:
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
            
            return {
                "currentCount": current_count,
                "matchCount": match_count,
                "page": page,
                "perPage": per_page,
                "totalCount": total_count,
                "data": data_items
            }
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            # Return empty structure for malformed XML
            return {
                "currentCount": 0,
                "matchCount": 0,
                "page": 1,
                "perPage": 0,
                "totalCount": 0,
                "data": []
            }
    
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
    
    # Domain-specific methods
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