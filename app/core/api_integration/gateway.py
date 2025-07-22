"""
API Gateway - unified interface for all data sources.

Provides a single entry point for accessing multiple public data APIs
with consistent request/response handling, routing, and error management.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from ..data_sources.manager import DataSourceManager, get_data_source_manager
from ..data_sources.registry import DataSourceRegistry, get_data_source_registry
from .transformers import RequestTransformer, ResponseTransformer
from .versioning import APIVersionManager
from .rate_limiting import RateLimiter
from .middleware import MiddlewareManager

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """HTTP methods supported by the gateway"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class APIRequest(BaseModel):
    """Standardized API request model"""
    # Request identification
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    # HTTP details
    method: HTTPMethod = Field(HTTPMethod.GET, description="HTTP method")
    path: str = Field(..., description="Request path")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    body: Optional[Any] = Field(None, description="Request body")
    
    # Gateway routing
    data_source: Optional[str] = Field(None, description="Target data source name")
    operation: Optional[str] = Field(None, description="Operation name")
    version: str = Field("v1", description="API version")
    
    # Client information
    client_id: Optional[str] = Field(None, description="Client identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    api_key: Optional[str] = Field(None, description="API key")
    
    # Request options
    timeout: Optional[float] = Field(None, description="Request timeout in seconds")
    retry_count: int = Field(0, description="Number of retries attempted")
    cache_enabled: bool = Field(True, description="Whether caching is enabled")
    
    class Config:
        use_enum_values = True


class APIResponse(BaseModel):
    """Standardized API response model"""
    # Response identification
    request_id: str = Field(..., description="Original request identifier")
    response_id: str = Field(..., description="Unique response identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    # HTTP response details
    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    
    # Response data
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if any")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    
    # Metadata
    data_source: Optional[str] = Field(None, description="Source data source name")
    operation: Optional[str] = Field(None, description="Operation that was executed")
    version: str = Field("v1", description="API version used")
    
    # Performance metrics
    processing_time_ms: float = Field(0.0, description="Processing time in milliseconds")
    data_source_time_ms: float = Field(0.0, description="Data source response time")
    cache_hit: bool = Field(False, description="Whether response came from cache")
    
    # Pagination and metadata
    pagination: Optional[Dict[str, Any]] = Field(None, description="Pagination information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @property
    def is_success(self) -> bool:
        """Check if response indicates success"""
        return 200 <= self.status_code < 300 and not self.error
    
    @property
    def is_error(self) -> bool:
        """Check if response indicates error"""
        return self.status_code >= 400 or bool(self.error)


class RouteHandler:
    """Handler for API route processing"""
    
    def __init__(
        self,
        data_source: str,
        operation: str,
        handler_func: Callable,
        middleware: Optional[List[str]] = None
    ):
        self.data_source = data_source
        self.operation = operation
        self.handler_func = handler_func
        self.middleware = middleware or []
    
    async def handle(self, request: APIRequest) -> APIResponse:
        """Handle the request"""
        return await self.handler_func(request)


class APIGateway:
    """
    Unified API Gateway for all data sources.
    
    Provides a single entry point for accessing multiple public data APIs
    with consistent interfaces, routing, and processing.
    """
    
    def __init__(
        self,
        data_source_manager: Optional[DataSourceManager] = None,
        registry: Optional[DataSourceRegistry] = None,
        request_transformer: Optional[RequestTransformer] = None,
        response_transformer: Optional[ResponseTransformer] = None,
        version_manager: Optional[APIVersionManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        middleware_manager: Optional[MiddlewareManager] = None
    ):
        self.data_source_manager = data_source_manager or get_data_source_manager()
        self.registry = registry or get_data_source_registry()
        self.request_transformer = request_transformer
        self.response_transformer = response_transformer
        self.version_manager = version_manager
        self.rate_limiter = rate_limiter
        self.middleware_manager = middleware_manager
        
        # Route registry
        self._routes: Dict[str, RouteHandler] = {}
        self._default_routes: Dict[str, RouteHandler] = {}
        
        # Gateway statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_responses": 0,
            "rate_limited_requests": 0,
            "average_response_time": 0.0,
            "start_time": datetime.utcnow()
        }
        
        # Request/response cache
        self._response_cache: Dict[str, APIResponse] = {}
        self._cache_ttl = 300  # 5 minutes default
        
        # Setup default routes
        self._setup_default_routes()
    
    def _setup_default_routes(self):
        """Setup default routes for common operations"""
        # Health check route
        self.register_route(
            path="/health",
            handler=self._health_check_handler,
            methods=[HTTPMethod.GET]
        )
        
        # Gateway stats route
        self.register_route(
            path="/stats",
            handler=self._stats_handler,
            methods=[HTTPMethod.GET]
        )
        
        # Data sources list route
        self.register_route(
            path="/data-sources",
            handler=self._data_sources_handler,
            methods=[HTTPMethod.GET]
        )
    
    def register_route(
        self,
        path: str,
        handler: Callable,
        methods: List[HTTPMethod] = None,
        data_source: Optional[str] = None,
        operation: Optional[str] = None,
        middleware: Optional[List[str]] = None
    ):
        """
        Register a route handler.
        
        Args:
            path: Route path
            handler: Handler function
            methods: Supported HTTP methods
            data_source: Target data source
            operation: Operation name
            middleware: Middleware to apply
        """
        methods = methods or [HTTPMethod.GET]
        
        for method in methods:
            route_key = f"{method.value}:{path}"
            route_handler = RouteHandler(
                data_source=data_source,
                operation=operation,
                handler_func=handler,
                middleware=middleware
            )
            self._routes[route_key] = route_handler
        
        logger.info(f"Registered route: {methods} {path}")
    
    def register_data_source_routes(self, data_source_name: str):
        """
        Register routes for a data source automatically.
        
        Args:
            data_source_name: Name of the data source
        """
        try:
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                logger.error(f"Data source not found: {data_source_name}")
                return
            
            # Register common CRUD routes
            base_path = f"/api/v1/{data_source_name}"
            
            # List/search route
            self.register_route(
                path=f"{base_path}/",
                handler=self._create_list_handler(data_source_name),
                methods=[HTTPMethod.GET],
                data_source=data_source_name,
                operation="list"
            )
            
            # Create route
            self.register_route(
                path=f"{base_path}/",
                handler=self._create_create_handler(data_source_name),
                methods=[HTTPMethod.POST],
                data_source=data_source_name,
                operation="create"
            )
            
            # Get by ID route
            self.register_route(
                path=f"{base_path}/{{id}}",
                handler=self._create_get_handler(data_source_name),
                methods=[HTTPMethod.GET],
                data_source=data_source_name,
                operation="get"
            )
            
            # Update route
            self.register_route(
                path=f"{base_path}/{{id}}",
                handler=self._create_update_handler(data_source_name),
                methods=[HTTPMethod.PUT, HTTPMethod.PATCH],
                data_source=data_source_name,
                operation="update"
            )
            
            # Delete route
            self.register_route(
                path=f"{base_path}/{{id}}",
                handler=self._create_delete_handler(data_source_name),
                methods=[HTTPMethod.DELETE],
                data_source=data_source_name,
                operation="delete"
            )
            
            logger.info(f"Registered routes for data source: {data_source_name}")
            
        except Exception as e:
            logger.error(f"Failed to register routes for {data_source_name}: {e}")
    
    async def process_request(self, request: APIRequest) -> APIResponse:
        """
        Process an API request through the gateway.
        
        Args:
            request: API request
            
        Returns:
            API response
        """
        start_time = datetime.utcnow()
        
        try:
            # Update statistics
            self._stats["total_requests"] += 1
            
            # Check rate limiting
            if self.rate_limiter and not await self._check_rate_limit(request):
                self._stats["rate_limited_requests"] += 1
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=429,
                    error="Rate limit exceeded",
                    processing_time_ms=self._calculate_processing_time(start_time)
                )
            
            # Check cache
            cached_response = await self._check_cache(request)
            if cached_response:
                self._stats["cached_responses"] += 1
                return cached_response
            
            # Transform request if transformer available
            if self.request_transformer:
                request = await self.request_transformer.transform(request)
            
            # Process through middleware
            if self.middleware_manager:
                request = await self.middleware_manager.process_request(request)
            
            # Route request
            response = await self._route_request(request)
            
            # Transform response if transformer available
            if self.response_transformer:
                response = await self.response_transformer.transform(response)
            
            # Process response through middleware
            if self.middleware_manager:
                response = await self.middleware_manager.process_response(response)
            
            # Cache response if appropriate
            if request.cache_enabled and response.is_success:
                await self._cache_response(request, response)
            
            # Update statistics
            if response.is_success:
                self._stats["successful_requests"] += 1
            else:
                self._stats["failed_requests"] += 1
            
            # Update processing time
            processing_time = self._calculate_processing_time(start_time)
            response.processing_time_ms = processing_time
            self._update_average_response_time(processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            self._stats["failed_requests"] += 1
            
            return APIResponse(
                request_id=request.request_id,
                response_id=self._generate_response_id(),
                status_code=500,
                error=f"Internal gateway error: {e}",
                processing_time_ms=self._calculate_processing_time(start_time)
            )
    
    async def _route_request(self, request: APIRequest) -> APIResponse:
        """
        Route request to appropriate handler.
        
        Args:
            request: API request
            
        Returns:
            API response
        """
        # Find route handler
        route_key = f"{request.method.value}:{request.path}"
        handler = self._routes.get(route_key)
        
        if not handler:
            # Try to find a pattern match or default handler
            handler = self._find_pattern_handler(request)
        
        if not handler:
            return APIResponse(
                request_id=request.request_id,
                response_id=self._generate_response_id(),
                status_code=404,
                error=f"Route not found: {request.method.value} {request.path}"
            )
        
        # Execute handler
        try:
            return await handler.handle(request)
        except Exception as e:
            logger.error(f"Handler error for {route_key}: {e}")
            return APIResponse(
                request_id=request.request_id,
                response_id=self._generate_response_id(),
                status_code=500,
                error=f"Handler error: {e}"
            )
    
    def _find_pattern_handler(self, request: APIRequest) -> Optional[RouteHandler]:
        """Find handler using pattern matching"""
        # Simple pattern matching for parameterized routes
        for route_key, handler in self._routes.items():
            method, path = route_key.split(":", 1)
            if method == request.method.value:
                if self._path_matches(path, request.path):
                    return handler
        return None
    
    def _path_matches(self, pattern: str, path: str) -> bool:
        """Check if path matches pattern with parameters"""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                # Parameter placeholder
                continue
            elif pattern_part != path_part:
                return False
        
        return True
    
    async def _check_rate_limit(self, request: APIRequest) -> bool:
        """Check if request is within rate limits"""
        if not self.rate_limiter:
            return True
        
        client_id = request.client_id or request.api_key or "anonymous"
        return await self.rate_limiter.check_limit(client_id, request.path)
    
    async def _check_cache(self, request: APIRequest) -> Optional[APIResponse]:
        """Check if response is cached"""
        if not request.cache_enabled or request.method != HTTPMethod.GET:
            return None
        
        cache_key = self._generate_cache_key(request)
        cached_response = self._response_cache.get(cache_key)
        
        if cached_response:
            # Check if cache is still valid
            cache_age = (datetime.utcnow() - cached_response.timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                cached_response.cache_hit = True
                return cached_response
            else:
                # Remove expired cache entry
                del self._response_cache[cache_key]
        
        return None
    
    async def _cache_response(self, request: APIRequest, response: APIResponse):
        """Cache response if appropriate"""
        if request.method == HTTPMethod.GET and response.is_success:
            cache_key = self._generate_cache_key(request)
            self._response_cache[cache_key] = response
    
    def _generate_cache_key(self, request: APIRequest) -> str:
        """Generate cache key for request"""
        return f"{request.method.value}:{request.path}:{hash(str(request.query_params))}"
    
    def _generate_response_id(self) -> str:
        """Generate unique response ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _calculate_processing_time(self, start_time: datetime) -> float:
        """Calculate processing time in milliseconds"""
        return (datetime.utcnow() - start_time).total_seconds() * 1000
    
    def _update_average_response_time(self, processing_time: float):
        """Update average response time"""
        total_requests = self._stats["total_requests"]
        if total_requests > 1:
            current_avg = self._stats["average_response_time"]
            self._stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
        else:
            self._stats["average_response_time"] = processing_time
    
    # Default route handlers
    async def _health_check_handler(self, request: APIRequest) -> APIResponse:
        """Health check handler"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "uptime_seconds": (datetime.utcnow() - self._stats["start_time"]).total_seconds()
        }
        
        return APIResponse(
            request_id=request.request_id,
            response_id=self._generate_response_id(),
            status_code=200,
            data=health_data
        )
    
    async def _stats_handler(self, request: APIRequest) -> APIResponse:
        """Gateway statistics handler"""
        return APIResponse(
            request_id=request.request_id,
            response_id=self._generate_response_id(),
            status_code=200,
            data=self._stats
        )
    
    async def _data_sources_handler(self, request: APIRequest) -> APIResponse:
        """Data sources list handler"""
        try:
            if self.data_source_manager:
                data_sources = self.data_source_manager.list_data_sources()
            else:
                data_sources = []
            
            return APIResponse(
                request_id=request.request_id,
                response_id=self._generate_response_id(),
                status_code=200,
                data={"data_sources": data_sources}
            )
        except Exception as e:
            return APIResponse(
                request_id=request.request_id,
                response_id=self._generate_response_id(),
                status_code=500,
                error=str(e)
            )
    
    def _create_list_handler(self, data_source_name: str) -> Callable:
        """Create list handler for data source"""
        async def handler(request: APIRequest) -> APIResponse:
            try:
                # This would integrate with the data source service
                # For now, return placeholder
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=200,
                    data={"message": f"List operation for {data_source_name}"},
                    data_source=data_source_name,
                    operation="list"
                )
            except Exception as e:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=500,
                    error=str(e),
                    data_source=data_source_name,
                    operation="list"
                )
        
        return handler
    
    def _create_get_handler(self, data_source_name: str) -> Callable:
        """Create get handler for data source"""
        async def handler(request: APIRequest) -> APIResponse:
            try:
                # Extract ID from path
                path_parts = request.path.split("/")
                item_id = path_parts[-1] if path_parts else None
                
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=200,
                    data={"message": f"Get operation for {data_source_name}, ID: {item_id}"},
                    data_source=data_source_name,
                    operation="get"
                )
            except Exception as e:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=500,
                    error=str(e),
                    data_source=data_source_name,
                    operation="get"
                )
        
        return handler
    
    def _create_create_handler(self, data_source_name: str) -> Callable:
        """Create create handler for data source"""
        async def handler(request: APIRequest) -> APIResponse:
            try:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=201,
                    data={"message": f"Create operation for {data_source_name}"},
                    data_source=data_source_name,
                    operation="create"
                )
            except Exception as e:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=500,
                    error=str(e),
                    data_source=data_source_name,
                    operation="create"
                )
        
        return handler
    
    def _create_update_handler(self, data_source_name: str) -> Callable:
        """Create update handler for data source"""
        async def handler(request: APIRequest) -> APIResponse:
            try:
                path_parts = request.path.split("/")
                item_id = path_parts[-1] if path_parts else None
                
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=200,
                    data={"message": f"Update operation for {data_source_name}, ID: {item_id}"},
                    data_source=data_source_name,
                    operation="update"
                )
            except Exception as e:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=500,
                    error=str(e),
                    data_source=data_source_name,
                    operation="update"
                )
        
        return handler
    
    def _create_delete_handler(self, data_source_name: str) -> Callable:
        """Create delete handler for data source"""
        async def handler(request: APIRequest) -> APIResponse:
            try:
                path_parts = request.path.split("/")
                item_id = path_parts[-1] if path_parts else None
                
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=204,
                    data={"message": f"Delete operation for {data_source_name}, ID: {item_id}"},
                    data_source=data_source_name,
                    operation="delete"
                )
            except Exception as e:
                return APIResponse(
                    request_id=request.request_id,
                    response_id=self._generate_response_id(),
                    status_code=500,
                    error=str(e),
                    data_source=data_source_name,
                    operation="delete"
                )
        
        return handler
    
    def get_gateway_stats(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            **self._stats,
            "cached_responses_count": len(self._response_cache),
            "registered_routes": len(self._routes),
            "uptime_seconds": (datetime.utcnow() - self._stats["start_time"]).total_seconds()
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self._response_cache.clear()
        logger.info("Gateway response cache cleared")


# Global API gateway instance
_api_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get the global API gateway instance"""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway


def setup_api_gateway(
    data_source_manager: Optional[DataSourceManager] = None,
    registry: Optional[DataSourceRegistry] = None,
    **kwargs
) -> APIGateway:
    """Setup and return the global API gateway"""
    global _api_gateway
    _api_gateway = APIGateway(data_source_manager, registry, **kwargs)
    return _api_gateway