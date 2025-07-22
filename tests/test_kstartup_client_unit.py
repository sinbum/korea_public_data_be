"""
Unit tests for K-Startup API Client.

Tests individual components and methods in isolation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import xml.etree.ElementTree as ET
import json

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.shared.models.kstartup import (
    KStartupAnnouncementResponse,
    KStartupBusinessResponse,
    KStartupContentResponse,
    KStartupStatisticsResponse,
    AnnouncementItem,
    BusinessItem,
    ContentItem,
    StatisticalItem
)
from app.shared.exceptions import (
    DataParsingError,
    DataTransformationError,
    APIClientError
)
from app.core.interfaces.base_api_client import APIResponse


@pytest.mark.unit
class TestKStartupClientBasics:
    """Test basic functionality of K-Startup client"""
    
    def test_client_initialization(self, mock_api_key):
        """Test client initialization with different parameters"""
        # Basic initialization
        client = KStartupAPIClient(api_key=mock_api_key)
        assert client.base_url == "https://apis.data.go.kr/B552735/kisedKstartupService01"
        assert client.timeout == 30
        assert client.max_retries == 3
        
    def test_client_initialization_aggressive_retry(self, mock_api_key):
        """Test client initialization with aggressive retry"""
        client = KStartupAPIClient(api_key=mock_api_key, use_aggressive_retry=True)
        assert client.retry_strategy.max_attempts == 5
        
    def test_convert_param_names(self, mock_kstartup_client):
        """Test parameter name conversion"""
        params = {
            "page_no": 1,
            "num_of_rows": 10,
            "business_name": "test",
            "business_type": "startup",
            "content_type": "news",
            "business_field": "tech"
        }
        
        converted = mock_kstartup_client._convert_param_names(params)
        
        assert converted["pageNo"] == 1
        assert converted["numOfRows"] == 10
        assert converted["businessName"] == "test"
        assert converted["businessType"] == "startup"
        assert converted["contentType"] == "news"
        assert converted["businessField"] == "tech"
        
    def test_convert_param_names_with_none_values(self, mock_kstartup_client):
        """Test parameter conversion skips None values"""
        params = {
            "page_no": 1,
            "business_name": None,
            "business_type": "startup"
        }
        
        converted = mock_kstartup_client._convert_param_names(params)
        
        assert "businessName" not in converted
        assert "pageNo" in converted
        assert "businessType" in converted
        
    def test_determine_response_type(self, mock_kstartup_client):
        """Test endpoint-based response type determination"""
        assert mock_kstartup_client._determine_response_type("getAnnouncementInformation01") == "announcements"
        assert mock_kstartup_client._determine_response_type("getBusinessInformation01") == "business"
        assert mock_kstartup_client._determine_response_type("getContentInformation01") == "content"
        assert mock_kstartup_client._determine_response_type("getStatisticalInformation01") == "statistics"
        assert mock_kstartup_client._determine_response_type("unknown_endpoint") == "announcements"


@pytest.mark.unit  
class TestXMLParsing:
    """Test XML response parsing functionality"""
    
    def test_parse_xml_response_success(self, mock_kstartup_client, sample_announcement_xml):
        """Test successful XML parsing"""
        result = mock_kstartup_client._parse_response_data(sample_announcement_xml)
        
        assert len(result) == 2
        assert result[0]["pbanc_no"] == "A2024001"
        assert result[0]["pbanc_titl_nm"] == "창업도약패키지 사업공고"
        assert result[1]["pbanc_no"] == "A2024002"
        
    def test_parse_xml_response_malformed(self, mock_kstartup_client):
        """Test XML parsing with malformed XML"""
        malformed_xml = "<response><unclosed_tag></response>"
        
        with pytest.raises(DataParsingError):
            mock_kstartup_client._parse_response_data(malformed_xml)
            
    def test_parse_xml_response_empty(self, mock_kstartup_client):
        """Test XML parsing with empty response"""
        empty_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <response>
            <currentCount>0</currentCount>
            <matchCount>0</matchCount>
            <totalCount>0</totalCount>
            <data></data>
        </response>"""
        
        result = mock_kstartup_client._parse_response_data(empty_xml)
        assert result == []
        
    def test_get_xml_int_value(self, mock_kstartup_client):
        """Test XML integer value extraction"""
        xml_content = "<root><count>42</count><invalid>abc</invalid></root>"
        root = ET.fromstring(xml_content)
        
        assert mock_kstartup_client._get_xml_int_value(root, "count") == 42
        assert mock_kstartup_client._get_xml_int_value(root, "invalid", default=0) == 0
        assert mock_kstartup_client._get_xml_int_value(root, "missing", default=5) == 5


@pytest.mark.unit
class TestJSONParsing:
    """Test JSON response processing functionality"""
    
    def test_process_json_response_nested(self, mock_kstartup_client, sample_announcement_json):
        """Test nested JSON response processing"""
        result = mock_kstartup_client._process_json_response(sample_announcement_json)
        
        assert result["currentCount"] == 2
        assert result["totalCount"] == 2
        assert result["page"] == 1
        assert len(result["data"]) == 2
        
    def test_process_json_response_direct(self, mock_kstartup_client):
        """Test direct JSON response processing"""
        direct_json = {
            "currentCount": 1,
            "totalCount": 1,
            "data": [{"test": "value"}]
        }
        
        result = mock_kstartup_client._process_json_response(direct_json)
        assert result == direct_json


@pytest.mark.unit
class TestResponseTransformation:
    """Test response transformation functionality"""
    
    def test_transform_response_json_success(self, mock_kstartup_client, sample_announcement_json):
        """Test successful JSON response transformation"""
        mock_kstartup_client._current_endpoint = "getAnnouncementInformation01"
        
        response_data = {
            "status_code": 200,
            "content": json.dumps(sample_announcement_json)
        }
        
        with patch.object(mock_kstartup_client, 'validate_kstartup_response_data') as mock_validate:
            mock_validate.return_value = Mock()
            result = mock_kstartup_client._transform_response(response_data)
            
            assert result.success is True
            assert result.status_code == 200
            
    def test_transform_response_xml_success(self, mock_kstartup_client, sample_announcement_xml):
        """Test successful XML response transformation"""
        mock_kstartup_client._current_endpoint = "getAnnouncementInformation01"
        
        response_data = {
            "status_code": 200,
            "content": sample_announcement_xml
        }
        
        with patch.object(mock_kstartup_client, 'validate_kstartup_response_data') as mock_validate:
            mock_validate.return_value = Mock()
            result = mock_kstartup_client._transform_response(response_data)
            
            assert result.success is True
            assert result.status_code == 200
            
    def test_transform_response_http_error(self, mock_kstartup_client):
        """Test response transformation with HTTP error"""
        response_data = {
            "status_code": 404,
            "content": "Not Found"
        }
        
        result = mock_kstartup_client._transform_response(response_data)
        
        assert result.success is False
        assert result.status_code == 404
        assert "HTTP 404" in result.error
        
    def test_transform_response_json_parse_error(self, mock_kstartup_client):
        """Test response transformation with JSON parse error"""
        mock_kstartup_client._current_endpoint = "getAnnouncementInformation01"
        
        response_data = {
            "status_code": 200,
            "content": "invalid json content"
        }
        
        with pytest.raises((DataParsingError, DataTransformationError)):
            mock_kstartup_client._transform_response(response_data)


@pytest.mark.unit
class TestRequestPreprocessing:
    """Test request preprocessing functionality"""
    
    def test_preprocess_request_basic(self, mock_kstartup_client):
        """Test basic request preprocessing"""
        from app.core.interfaces.base_api_client import RequestMethod
        
        params = {"page_no": 1, "num_of_rows": 10}
        
        result = mock_kstartup_client._preprocess_request(
            "test_endpoint",
            RequestMethod.GET,
            params,
            None,
            None
        )
        
        assert result["method"] == "GET"
        assert result["params"]["pageNo"] == 1
        assert result["params"]["numOfRows"] == 10
        assert result["params"]["type"] == "json"
        assert "KStartup-API-Client/1.0" in result["headers"]["User-Agent"]
        
    def test_preprocess_request_with_custom_headers(self, mock_kstartup_client):
        """Test request preprocessing with custom headers"""
        from app.core.interfaces.base_api_client import RequestMethod
        
        custom_headers = {"Custom-Header": "test-value"}
        
        result = mock_kstartup_client._preprocess_request(
            "test_endpoint",
            RequestMethod.GET,
            {},
            None,
            custom_headers
        )
        
        assert result["headers"]["Custom-Header"] == "test-value"
        assert result["headers"]["Accept"] == "application/json,application/xml"


@pytest.mark.unit
class TestParameterValidation:
    """Test parameter validation and type checking"""
    
    def test_announcement_parameters(self, mock_kstartup_client):
        """Test announcement method parameters"""
        # Should not raise any exceptions
        mock_kstartup_client._convert_param_names({
            "page_no": 1,
            "num_of_rows": 10,
            "business_name": "test",
            "business_type": "startup"
        })
        
    def test_business_parameters(self, mock_kstartup_client):
        """Test business method parameters"""
        mock_kstartup_client._convert_param_names({
            "page_no": 1,
            "num_of_rows": 10,
            "business_field": "tech",
            "organization": "kised"
        })
        
    def test_content_parameters(self, mock_kstartup_client):
        """Test content method parameters"""
        mock_kstartup_client._convert_param_names({
            "page_no": 1,
            "num_of_rows": 10,
            "content_type": "news",
            "category": "startup"
        })
        
    def test_statistics_parameters(self, mock_kstartup_client):
        """Test statistics method parameters"""
        mock_kstartup_client._convert_param_names({
            "page_no": 1,
            "num_of_rows": 10,
            "year": 2024,
            "month": 1
        })


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_endpoint_response_type(self, mock_kstartup_client):
        """Test handling of invalid endpoint for response type determination"""
        # Should default to announcements
        response_type = mock_kstartup_client._determine_response_type("invalid_endpoint_name")
        assert response_type == "announcements"
        
    def test_missing_current_endpoint(self, mock_kstartup_client):
        """Test handling when _current_endpoint is not set"""
        # Should use default behavior
        response_type = mock_kstartup_client._determine_response_type("unknown")
        assert response_type == "announcements"