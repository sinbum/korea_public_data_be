"""
Base API Client interface and abstract implementation.

Implements Strategy and Template Method patterns for flexible API integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Generic, List
from enum import Enum
import httpx
import asyncio
import logging
from contextlib import asynccontextmanager
from pydantic import BaseModel

from ...shared.exceptions import (
    APIClientError,
    create_api_exception_from_response,
    create_network_exception_from_httpx_error
)
from ...shared.exceptions.data_exceptions import (
    DataParsingError,
    DataTransformationError,
    DataValidationError,
)
from ...core.request_context import get_request_id
from .retry_strategies import (
    RetryStrategy,
    ExponentialBackoffStrategy,
    RetryExecutor
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# APIClientError is now imported from shared.exceptions


class AuthenticationStrategy(ABC):
    """Abstract authentication strategy"""
    
    @abstractmethod
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply authentication to request parameters"""
        pass


class APIKeyAuthStrategy(AuthenticationStrategy):
    """API Key authentication strategy"""
    
    def __init__(self, api_key: str, key_param: str = "serviceKey"):
        self.api_key = api_key
        self.key_param = key_param
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        request_params[self.key_param] = self.api_key
        return request_params


class BearerTokenAuthStrategy(AuthenticationStrategy):
    """Bearer token authentication strategy"""
    
    def __init__(self, token: str):
        self.token = token
    
    def apply_auth(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        headers = request_params.get("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        request_params["headers"] = headers
        return request_params


class RequestMethod(Enum):
    """HTTP request methods"""
    GET = "GET"
    POST = "POST" 
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    status_code: int
    total_count: Optional[int] = None
    current_count: Optional[int] = None


class BaseAPIClient(ABC, Generic[T]):
    """
    Abstract base class for API clients implementing Template Method pattern.
    
    Provides common HTTP operations with customizable hooks for different APIs.
    """
    
    def __init__(
        self, 
        base_url: str,
        auth_strategy: AuthenticationStrategy,
        timeout: int = 30,
        max_retries: int = 3,
        retry_strategy: Optional[RetryStrategy] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.auth_strategy = auth_strategy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_strategy = retry_strategy or ExponentialBackoffStrategy(
            max_attempts=max_retries + 1,
            base_delay=1.0,
            max_delay=30.0
        )
        self.retry_executor = RetryExecutor(self.retry_strategy)
        self.client: Optional[httpx.Client] = None
    
    def __enter__(self):
        """Context manager entry"""
        self.client = httpx.Client(timeout=self.timeout)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            self.client.close()
    
    @asynccontextmanager
    async def async_client(self):
        """Async context manager for httpx.AsyncClient"""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        ) as async_client:
            old_client = self.client
            self.client = async_client
            try:
                yield self
            finally:
                # Ensure we restore the previous client reference
                self.client = old_client
    
    # Template method pattern implementation
    def request(
        self,
        endpoint: str,
        method: RequestMethod = RequestMethod.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> APIResponse[T]:
        """
        Template method for making API requests.
        
        Follows the pattern:
        1. Pre-process request
        2. Apply authentication  
        3. Make HTTP request
        4. Post-process response
        5. Transform to domain model
        """
        try:
            # Step 1: Pre-process request (hook method)
            request_params = self._preprocess_request(
                endpoint, method, params, data, headers
            )
            
            # Step 2: Apply authentication strategy
            request_params = self.auth_strategy.apply_auth(request_params)
            
            # Step 3: Make HTTP request with retry logic via RetryExecutor,
            # wrapping the overridable _make_request_with_retry so tests can patch it
            def _op() -> httpx.Response:
                return self._make_request_with_retry(request_params)
            operation_name = f"{request_params.get('method', 'REQUEST')} {request_params.get('url', 'unknown')}"
            response = self.retry_executor.execute_sync(_op, operation_name)
            
            # Step 4: Post-process response (hook method)
            processed_response = self._postprocess_response(response)
            
            # Step 5: Transform to domain model (hook method)
            return self._transform_response(processed_response)
            
        except (DataParsingError, DataTransformationError, DataValidationError):
            raise
        except Exception as e:
            logger.error(f"API request failed: {e}")
            status_code = getattr(e, 'status_code', None)
            if status_code is None:
                status_code = 500
            return APIResponse[T](
                success=False,
                error=str(e),
                status_code=status_code
            )
    
    def _preprocess_request(
        self,
        endpoint: str,
        method: RequestMethod,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]], 
        headers: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Hook method for request preprocessing"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        request_params = {
            "method": method.value,
            "url": url,
            "params": params or {},
            "data": data,
            "headers": headers or {}
        }
        
        # Add default headers
        request_params["headers"].update({
            "User-Agent": "Korea-Public-API-Client/1.0",
            "Accept": "application/json,application/xml"
        })

        # Propagate request id for tracing if available
        req_id = get_request_id()
        if req_id:
            request_params["headers"]["X-Request-ID"] = req_id
        
        return request_params
    
    def _make_request_with_retry(self, request_params: Dict[str, Any]) -> httpx.Response:
        """Make HTTP request with advanced retry logic"""
        
        def make_single_request() -> httpx.Response:
            try:
                if not self.client:
                    raise APIClientError("Client not initialized. Use context manager.")
                
                response = self.client.request(**request_params)
                
                # Convert HTTP errors to appropriate exceptions
                if response.status_code >= 400:
                    raise create_api_exception_from_response(response)
                
                return response
                
            except httpx.HTTPError as e:
                # Convert httpx errors to our custom exceptions
                raise create_network_exception_from_httpx_error(e)
        
        operation_name = f"{request_params.get('method', 'REQUEST')} {request_params.get('url', 'unknown')}"
        return self.retry_executor.execute_sync(make_single_request, operation_name)
    
    def _postprocess_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Hook method for response post-processing"""
        raw_headers = getattr(response, 'headers', {})
        try:
            headers = dict(raw_headers)
        except Exception:
            headers = {}
        return {
            "status_code": getattr(response, 'status_code', 500),
            "content": getattr(response, 'text', ""),
            "headers": headers
        }
    
    @abstractmethod
    def _transform_response(self, response_data: Dict[str, Any]) -> APIResponse[T]:
        """Transform raw response to domain model (must be implemented by subclasses)"""
        pass
    
    @abstractmethod 
    def _parse_response_data(self, content: str) -> List[Dict[str, Any]]:
        """Parse response content to structured data (must be implemented by subclasses)"""
        pass
    
    # Convenience methods for common operations
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """GET request convenience method"""
        return self.request(endpoint, RequestMethod.GET, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """POST request convenience method"""
        return self.request(endpoint, RequestMethod.POST, data=data)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """PUT request convenience method"""
        return self.request(endpoint, RequestMethod.PUT, data=data)
    
    def delete(self, endpoint: str) -> APIResponse[T]:
        """DELETE request convenience method"""
        return self.request(endpoint, RequestMethod.DELETE)
    
    # Async versions of convenience methods
    async def async_request(
        self,
        endpoint: str,
        method: RequestMethod = RequestMethod.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> APIResponse[T]:
        """
        Async template method for making API requests.
        
        Similar to request() but uses async HTTP client.
        """
        try:
            # Step 1: Pre-process request (hook method)
            request_params = self._preprocess_request(
                endpoint, method, params, data, headers
            )
            
            # Step 2: Apply authentication strategy
            request_params = self.auth_strategy.apply_auth(request_params)
            
            # Step 3: Make async HTTP request with retry logic
            response = await self._make_async_request_with_retry(request_params)
            
            # Step 4: Post-process response (hook method)
            processed_response = self._postprocess_response(response)
            
            # Step 5: Transform to domain model (hook method)
            return self._transform_response(processed_response)
            
        except (DataParsingError, DataTransformationError, DataValidationError):
            raise
        except Exception as e:
            logger.error(f"Async API request failed: {e}")
            status_code = getattr(e, 'status_code', None)
            if status_code is None:
                status_code = 500
            return APIResponse[T](
                success=False,
                error=str(e),
                status_code=status_code
            )
    
    async def _make_async_request_with_retry(self, request_params: Dict[str, Any]) -> httpx.Response:
        """Make async HTTP request with advanced retry logic"""
        
        async def make_single_async_request() -> httpx.Response:
            try:
                if not self.client:
                    raise APIClientError("Client not initialized. Use async context manager.")
                
                # Use the async client for async requests
                if hasattr(self.client, 'arequest') or isinstance(self.client, httpx.AsyncClient):
                    response = await self.client.request(**request_params)
                else:
                    # Fallback to sync if not async client
                    response = self.client.request(**request_params)
                
                # Convert HTTP errors to appropriate exceptions
                if response.status_code >= 400:
                    raise create_api_exception_from_response(response)
                
                return response
                
            except httpx.HTTPError as e:
                # Convert httpx errors to our custom exceptions
                raise create_network_exception_from_httpx_error(e)
        
        operation_name = f"ASYNC {request_params.get('method', 'REQUEST')} {request_params.get('url', 'unknown')}"
        return await self.retry_executor.execute_async(make_single_async_request, operation_name)
    
    async def async_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """Async GET request convenience method"""
        return await self.async_request(endpoint, RequestMethod.GET, params=params)
    
    async def async_post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """Async POST request convenience method"""
        return await self.async_request(endpoint, RequestMethod.POST, data=data)
    
    async def async_put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> APIResponse[T]:
        """Async PUT request convenience method"""
        return await self.async_request(endpoint, RequestMethod.PUT, data=data)
    
    async def async_delete(self, endpoint: str) -> APIResponse[T]:
        """Async DELETE request convenience method"""
        return await self.async_request(endpoint, RequestMethod.DELETE)