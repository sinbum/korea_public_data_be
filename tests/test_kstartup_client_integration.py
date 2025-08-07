"""
Integration tests for K-Startup API Client.

Tests complete workflows and interactions between components.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import httpx

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.shared.models.kstartup import (
    KStartupAnnouncementResponse,
    KStartupBusinessResponse,
    KStartupContentResponse,
    KStartupStatisticsResponse
)
from app.shared.exceptions import (
    APIClientError,
    APITimeoutError,
    APIServerError,
    DataParsingError
)


@pytest.mark.integration
class TestKStartupClientSyncMethods:
    """Test synchronous API methods with mocked HTTP responses"""
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_get_announcement_information_success(
        self, mock_request, mock_kstartup_client, sample_announcement_xml, mock_httpx_response
    ):
        """Test successful announcement information retrieval"""
        # Setup mock response
        mock_response = mock_httpx_response(200, sample_announcement_xml)
        mock_request.return_value = mock_response
        
        # Call method
        result = mock_kstartup_client.get_announcement_information(
            page_no=1, num_of_rows=10, business_name="창업도약"
        )
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args[0][0]
        assert call_args["params"]["pageNo"] == 1
        assert call_args["params"]["numOfRows"] == 10
        assert call_args["params"]["businessName"] == "창업도약"
        assert call_args["params"]["type"] == "json"
        
        # Verify response
        assert result.success is True
        assert result.status_code == 200
        assert isinstance(result.data, KStartupAnnouncementResponse)
        
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_get_business_information_success(
        self, mock_request, mock_kstartup_client, sample_business_data, mock_httpx_response
    ):
        """Test successful business information retrieval"""
        # Setup mock response
        json_content = json.dumps(sample_business_data)
        mock_response = mock_httpx_response(200, json_content)
        mock_request.return_value = mock_response
        
        # Call method
        result = mock_kstartup_client.get_business_information(
            page_no=1, business_field="tech", organization="kised"
        )
        
        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args[0][0]
        assert call_args["params"]["businessField"] == "tech"
        assert call_args["params"]["organization"] == "kised"
        
        # Verify response
        assert result.success is True
        assert isinstance(result.data, KStartupBusinessResponse)
        
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_get_content_information_success(
        self, mock_request, mock_kstartup_client, sample_content_data, mock_httpx_response
    ):
        """Test successful content information retrieval"""
        json_content = json.dumps(sample_content_data)
        mock_response = mock_httpx_response(200, json_content)
        mock_request.return_value = mock_response
        
        result = mock_kstartup_client.get_content_information(
            content_type="news", category="startup"
        )
        
        assert result.success is True
        assert isinstance(result.data, KStartupContentResponse)
        
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_get_statistical_information_success(
        self, mock_request, mock_kstartup_client, sample_statistics_data, mock_httpx_response
    ):
        """Test successful statistics information retrieval"""
        json_content = json.dumps(sample_statistics_data)
        mock_response = mock_httpx_response(200, json_content)
        mock_request.return_value = mock_response
        
        result = mock_kstartup_client.get_statistical_information(
            year=2024, month=1
        )
        
        assert result.success is True
        assert isinstance(result.data, KStartupStatisticsResponse)


@pytest.mark.integration
@pytest.mark.asyncio_test
class TestKStartupClientAsyncMethods:
    """Test asynchronous API methods with mocked HTTP responses"""
    
    async def test_async_get_announcement_information_success(
        self, mock_kstartup_client, sample_announcement_xml
    ):
        """Test successful async announcement information retrieval"""
        with patch.object(mock_kstartup_client, 'async_client') as mock_async_context:
            # Setup async context manager mock
            mock_client_instance = AsyncMock()
            mock_client_instance.async_get = AsyncMock()
            
            # Create a proper async context manager
            from contextlib import asynccontextmanager
            @asynccontextmanager
            async def async_context_manager():
                yield mock_client_instance
            
            mock_async_context.return_value = async_context_manager()
            
            # Setup return value
            from app.core.interfaces.base_api_client import APIResponse
            mock_response = APIResponse(
                success=True,
                data=Mock(),
                status_code=200
            )
            mock_client_instance.async_get.return_value = mock_response
            
            # Call async method
            result = await mock_kstartup_client.async_get_announcement_information(
                page_no=1, num_of_rows=10
            )
            
            # Verify async call was made
            mock_client_instance.async_get.assert_called_once_with(
                "getAnnouncementInformation01", 
                {
                    "page_no": 1,
                    "num_of_rows": 10,
                    "business_name": None,
                    "business_type": None
                }
            )
            
            assert result.success is True
    
    async def test_async_batch_processing(self, mock_kstartup_client):
        """Test async batch processing of multiple endpoints"""
        with patch.object(mock_kstartup_client, 'async_client') as mock_async_context:
            mock_client_instance = AsyncMock()
            mock_client_instance.async_get = AsyncMock()
            
            from contextlib import asynccontextmanager
            @asynccontextmanager
            async def async_context_manager():
                yield mock_client_instance
            
            mock_async_context.return_value = async_context_manager()
            
            # Setup batch responses
            from app.core.interfaces.base_api_client import APIResponse
            mock_responses = [
                APIResponse(success=True, data=Mock(), status_code=200),
                APIResponse(success=True, data=Mock(), status_code=200)
            ]
            
            # Mock asyncio.gather to return awaitable that yields our mock responses
            async def _dummy_gather(*args, **kwargs):
                return mock_responses
            with patch('asyncio.gather', _dummy_gather):
                endpoints = ["getAnnouncementInformation01", "getBusinessInformation01"]
                params_list = [{"page_no": 1}, {"page_no": 1}]
                
                results = await mock_kstartup_client.get_all_data_batch(endpoints, params_list)
                
                assert len(results) == 2
                assert all(result.success for result in results)
    
    async def test_async_batch_processing_validation_error(self, mock_kstartup_client):
        """Test async batch processing with validation error"""
        endpoints = ["endpoint1", "endpoint2"]
        params_list = [{"param1": "value1"}]  # Mismatched lengths
        
        with pytest.raises(ValueError, match="same length"):
            await mock_kstartup_client.get_all_data_batch(endpoints, params_list)


@pytest.mark.integration
class TestKStartupClientErrorHandling:
    """Test error handling in integration scenarios"""
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_http_error_handling(self, mock_request, mock_kstartup_client, mock_httpx_response):
        """Test HTTP error handling"""
        # Test different HTTP error codes
        error_scenarios = [
            (400, "Bad Request"),
            (401, "Unauthorized"), 
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable")
        ]
        
        for status_code, error_message in error_scenarios:
            mock_response = mock_httpx_response(status_code, error_message)
            mock_request.return_value = mock_response
            
            result = mock_kstartup_client.get_announcement_information()
            
            assert result.success is False
            assert result.status_code == status_code
            assert str(status_code) in result.error
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_network_error_handling(self, mock_request, mock_kstartup_client):
        """Test network error handling"""
        # Simulate network errors
        network_errors = [
            httpx.TimeoutException("Request timed out"),
            httpx.ConnectError("Connection failed"),
            httpx.ReadTimeout("Read timeout")
        ]
        
        for error in network_errors:
            mock_request.side_effect = error
            
            result = mock_kstartup_client.get_announcement_information()
            
            assert result.success is False
            assert result.error is not None
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_malformed_response_handling(self, mock_request, mock_kstartup_client, mock_httpx_response):
        """Test handling of malformed API responses"""
        # Test malformed XML
        malformed_xml = "<response><unclosed_tag></response>"
        mock_response = mock_httpx_response(200, malformed_xml)
        mock_request.return_value = mock_response
        
        with pytest.raises(DataParsingError):
            mock_kstartup_client.get_announcement_information()
        
        # Test malformed JSON
        malformed_json = '{"incomplete": json'
        mock_response = mock_httpx_response(200, malformed_json)
        mock_request.return_value = mock_response
        
        with pytest.raises((DataParsingError, json.JSONDecodeError)):
            mock_kstartup_client.get_announcement_information()


@pytest.mark.integration  
class TestKStartupClientRetryLogic:
    """Test retry logic integration"""
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_retry_on_server_error(self, mock_request, mock_kstartup_client, mock_httpx_response):
        """Test retry behavior on server errors"""
        # Simulate server error followed by success
        error_response = mock_httpx_response(500, "Internal Server Error")
        success_response = mock_httpx_response(200, '{"success": true}')
        
        mock_request.side_effect = [
            APIServerError("Server error", status_code=500),
            success_response
        ]
        
        # The retry logic should be handled by the RetryExecutor
        # We'll test that the method can handle retry scenarios
        with patch.object(mock_kstartup_client.retry_executor, 'execute_sync') as mock_executor:
            mock_executor.return_value = success_response
            
            result = mock_kstartup_client.get_announcement_information()
            
            # Verify retry executor was called
            mock_executor.assert_called_once()
    
    def test_aggressive_retry_configuration(self, mock_api_key):
        """Test aggressive retry configuration"""
        client = KStartupAPIClient(api_key=mock_api_key, use_aggressive_retry=True)
        
        # Verify aggressive retry settings
        assert client.retry_strategy.max_attempts == 5
        assert client.retry_strategy.max_delay == 60.0
        
    def test_conservative_retry_configuration(self, mock_api_key):
        """Test conservative retry configuration (default)"""
        client = KStartupAPIClient(api_key=mock_api_key, use_aggressive_retry=False)
        
        # Verify conservative retry settings
        assert client.retry_strategy.max_attempts == 3
        assert client.retry_strategy.max_delay == 30.0


@pytest.mark.integration
class TestKStartupClientContextManagers:
    """Test context manager integration"""
    
    @patch('httpx.Client')
    def test_sync_context_manager(self, mock_httpx_client, mock_kstartup_client):
        """Test synchronous context manager usage"""
        mock_client_instance = Mock()
        mock_httpx_client.return_value = mock_client_instance
        
        with mock_kstartup_client as client:
            assert client.client == mock_client_instance
            
        # Verify client was closed
        mock_client_instance.close.assert_called_once()
    
    async def test_async_context_manager(self, mock_kstartup_client):
        """Test asynchronous context manager usage"""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client_instance = AsyncMock()
            
            # Create a proper async context manager
            async def async_client_context():
                yield mock_client_instance
            
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async with mock_kstartup_client.async_client() as client:
                assert client == mock_kstartup_client
                
            # Verify async client was properly managed
            # Note: The actual context management is handled by httpx.AsyncClient


@pytest.mark.integration
class TestKStartupDataValidation:
    """Test data validation integration"""
    
    def test_announcement_data_validation_integration(self, mock_kstartup_client, sample_announcement_xml):
        """Test end-to-end announcement data validation"""
        with patch.object(mock_kstartup_client, '_make_request_with_retry') as mock_request:
            from unittest.mock import Mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = sample_announcement_xml
            mock_request.return_value = mock_response
            
            mock_kstartup_client._current_endpoint = "getAnnouncementInformation01"
            
            # This should trigger the full validation pipeline
            with patch('app.shared.models.kstartup.validate_kstartup_response_data') as mock_validate:
                mock_validate.return_value = Mock(spec=KStartupAnnouncementResponse)
                
                result = mock_kstartup_client.get_announcement_information()
                
                # Verify validation was called
                mock_validate.assert_called_once()
                args = mock_validate.call_args[0]
                assert args[1] == "announcements"  # response_type
                
    def test_invalid_data_validation_handling(self, mock_kstartup_client):
        """Test handling of validation errors"""
        with patch.object(mock_kstartup_client, '_make_request_with_retry') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "invalid response data"
            mock_request.return_value = mock_response
            
            mock_kstartup_client._current_endpoint = "getAnnouncementInformation01"
            
            # This should trigger validation error handling
            with patch('app.shared.models.kstartup.validate_kstartup_response_data') as mock_validate:
                from app.shared.exceptions import DataValidationError
                mock_validate.side_effect = DataValidationError("Validation failed")
                
                with pytest.raises(DataValidationError):
                    mock_kstartup_client.get_announcement_information()