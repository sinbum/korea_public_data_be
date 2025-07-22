"""
Simple test to verify async context manager functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.shared.clients.kstartup_api_client import KStartupAPIClient


@pytest.mark.asyncio
async def test_async_context_manager_basic():
    """Test that async context manager works correctly"""
    client = KStartupAPIClient(api_key="test_key")
    
    # Test that we can use the async context manager
    async with client.async_client() as ctx:
        assert ctx is client
        # Verify that client has been set to async client
        assert client.client is not None
        
        # Verify it's an httpx.AsyncClient
        import httpx
        assert isinstance(client.client, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_async_method_call():
    """Test that async methods can be called"""
    client = KStartupAPIClient(api_key="test_key")
    
    # Mock the underlying async request
    with patch.object(client, '_make_async_request_with_retry') as mock_request:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        mock_request.return_value = mock_response
        
        # This should work without the AttributeError: __aenter__
        result = await client.async_get_announcement_information(page_no=1, num_of_rows=5)
        
        # Verify the method completed
        assert result is not None