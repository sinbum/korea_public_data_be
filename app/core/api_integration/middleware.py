"""
Middleware System for Request/Response Processing - handles cross-cutting concerns.

Provides a flexible middleware pipeline for processing requests and responses
with support for authentication, logging, metrics, caching, and other concerns.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Type, Union
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
import logging

from .gateway import APIRequest, APIResponse

logger = logging.getLogger(__name__)


class MiddlewarePhase(str, Enum):
    """Middleware execution phases"""
    PRE_REQUEST = "pre_request"        # Before request processing
    POST_REQUEST = "post_request"      # After request transformation
    PRE_ROUTING = "pre_routing"        # Before routing
    POST_ROUTING = "post_routing"      # After routing
    PRE_RESPONSE = "pre_response"      # Before response transformation
    POST_RESPONSE = "post_response"    # After response ready
    ERROR_HANDLING = "error_handling"  # Error processing


class MiddlewareOrder(int, Enum):
    """Standard middleware execution orders"""
    FIRST = 0
    AUTHENTICATION = 100
    AUTHORIZATION = 200
    RATE_LIMITING = 300
    LOGGING = 400
    METRICS = 500
    CACHING = 600
    TRANSFORMATION = 700
    ROUTING = 800
    BUSINESS_LOGIC = 900
    LAST = 1000


class MiddlewareConfig(BaseModel):
    """Middleware configuration"""
    enabled: bool = Field(True, description="Whether middleware is enabled")
    order: int = Field(MiddlewareOrder.BUSINESS_LOGIC, description="Execution order")
    phases: List[MiddlewarePhase] = Field(default_factory=list, description="Phases to execute in")
    config: Dict[str, Any] = Field(default_factory=dict, description="Middleware-specific configuration")


class MiddlewareContext(BaseModel):
    """Context passed through middleware pipeline"""
    request_id: str = Field(..., description="Request identifier")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Processing start time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    user_data: Dict[str, Any] = Field(default_factory=dict, description="User-specific data")
    
    # Performance tracking
    phase_times: Dict[str, float] = Field(default_factory=dict, description="Time spent in each phase")
    middleware_times: Dict[str, float] = Field(default_factory=dict, description="Time spent in each middleware")
    
    # Error tracking
    errors: List[str] = Field(default_factory=list, description="Accumulated errors")
    warnings: List[str] = Field(default_factory=list, description="Accumulated warnings")
    
    class Config:
        arbitrary_types_allowed = True


class Middleware(ABC):
    """Base class for middleware components"""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        self.config = config or MiddlewareConfig()
        self.name = self.__class__.__name__
        self._stats = {
            "executions": 0,
            "errors": 0,
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0
        }
    
    @abstractmethod
    def get_name(self) -> str:
        """Get middleware name"""
        pass
    
    @abstractmethod
    def get_phases(self) -> List[MiddlewarePhase]:
        """Get phases this middleware should execute in"""
        pass
    
    @abstractmethod
    async def process_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Process request in specified phase"""
        pass
    
    @abstractmethod
    async def process_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Process response in specified phase"""
        pass
    
    async def handle_error(
        self, 
        error: Exception, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> Optional[APIResponse]:
        """Handle error during processing"""
        logger.error(f"Error in middleware {self.name} during {phase}: {error}")
        context.errors.append(f"{self.name}: {error}")
        return None
    
    def get_order(self) -> int:
        """Get execution order"""
        return self.config.order
    
    def is_enabled(self) -> bool:
        """Check if middleware is enabled"""
        return self.config.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics"""
        return self._stats.copy()
    
    def _update_stats(self, execution_time_ms: float, error: bool = False):
        """Update middleware statistics"""
        self._stats["executions"] += 1
        if error:
            self._stats["errors"] += 1
        
        self._stats["total_time_ms"] += execution_time_ms
        self._stats["avg_time_ms"] = self._stats["total_time_ms"] / self._stats["executions"]


class LoggingMiddleware(Middleware):
    """Middleware for request/response logging"""
    
    def get_name(self) -> str:
        return "logging"
    
    def get_phases(self) -> List[MiddlewarePhase]:
        return [
            MiddlewarePhase.PRE_REQUEST,
            MiddlewarePhase.POST_RESPONSE,
            MiddlewarePhase.ERROR_HANDLING
        ]
    
    async def process_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Log request details"""
        if phase == MiddlewarePhase.PRE_REQUEST:
            log_data = {
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "client_id": request.client_id,
                "data_source": request.data_source,
                "timestamp": context.start_time.isoformat()
            }
            
            # Include query params if configured
            if self.config.config.get("log_query_params", True):
                log_data["query_params"] = request.query_params
            
            logger.info(f"API Request: {log_data}")
            context.metadata["logged_request"] = True
        
        return request
    
    async def process_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Log response details"""
        if phase == MiddlewarePhase.POST_RESPONSE:
            processing_time = (datetime.utcnow() - context.start_time).total_seconds() * 1000
            
            log_data = {
                "request_id": response.request_id,
                "response_id": response.response_id,
                "status_code": response.status_code,
                "processing_time_ms": processing_time,
                "cache_hit": response.cache_hit,
                "data_source": response.data_source,
                "success": response.is_success
            }
            
            if response.error:
                log_data["error"] = response.error
            
            logger.info(f"API Response: {log_data}")
            context.metadata["logged_response"] = True
        
        return response
    
    async def handle_error(
        self, 
        error: Exception, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> Optional[APIResponse]:
        """Log error details"""
        logger.error(f"API Error: {error}", extra={
            "request_id": context.request_id,
            "phase": phase,
            "middleware": self.name
        })
        return None


class MetricsMiddleware(Middleware):
    """Middleware for collecting performance metrics"""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        super().__init__(config)
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0,
            "total_response_time_ms": 0.0,
            "requests_by_status": {},
            "requests_by_path": {},
            "requests_by_data_source": {}
        }
    
    def get_name(self) -> str:
        return "metrics"
    
    def get_phases(self) -> List[MiddlewarePhase]:
        return [
            MiddlewarePhase.PRE_REQUEST,
            MiddlewarePhase.POST_RESPONSE
        ]
    
    async def process_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Start metrics collection"""
        if phase == MiddlewarePhase.PRE_REQUEST:
            self._metrics["total_requests"] += 1
            context.metadata["metrics_start_time"] = time.time()
            
            # Track by path
            path = request.path
            if path not in self._metrics["requests_by_path"]:
                self._metrics["requests_by_path"][path] = 0
            self._metrics["requests_by_path"][path] += 1
            
            # Track by data source
            if request.data_source:
                if request.data_source not in self._metrics["requests_by_data_source"]:
                    self._metrics["requests_by_data_source"][request.data_source] = 0
                self._metrics["requests_by_data_source"][request.data_source] += 1
        
        return request
    
    async def process_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Collect response metrics"""
        if phase == MiddlewarePhase.POST_RESPONSE:
            # Calculate response time
            start_time = context.metadata.get("metrics_start_time")
            if start_time:
                response_time_ms = (time.time() - start_time) * 1000
                self._metrics["total_response_time_ms"] += response_time_ms
                self._metrics["avg_response_time_ms"] = (
                    self._metrics["total_response_time_ms"] / self._metrics["total_requests"]
                )
            
            # Track by status
            status = response.status_code
            if status not in self._metrics["requests_by_status"]:
                self._metrics["requests_by_status"][status] = 0
            self._metrics["requests_by_status"][status] += 1
            
            # Track success/failure
            if response.is_success:
                self._metrics["successful_requests"] += 1
            else:
                self._metrics["failed_requests"] += 1
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self._metrics.copy()


class AuthenticationMiddleware(Middleware):
    """Middleware for API key authentication"""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        super().__init__(config)
        self._valid_api_keys = set(self.config.config.get("valid_api_keys", []))
        self._require_auth = self.config.config.get("require_auth", True)
        self._auth_header = self.config.config.get("auth_header", "X-API-Key")
    
    def get_name(self) -> str:
        return "authentication"
    
    def get_phases(self) -> List[MiddlewarePhase]:
        return [MiddlewarePhase.PRE_REQUEST]
    
    async def process_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Authenticate request"""
        if phase == MiddlewarePhase.PRE_REQUEST:
            # Skip auth for health check and public endpoints
            public_paths = self.config.config.get("public_paths", ["/health", "/docs"])
            if request.path in public_paths:
                context.metadata["auth_required"] = False
                context.metadata["authenticated"] = True
                return request
            
            # Check API key
            api_key = request.api_key or request.headers.get(self._auth_header)
            
            if self._require_auth and not api_key:
                raise ValueError("API key required")
            
            if api_key and self._valid_api_keys and api_key not in self._valid_api_keys:
                raise ValueError("Invalid API key")
            
            # Set authentication context
            context.metadata["auth_required"] = self._require_auth
            context.metadata["authenticated"] = bool(api_key)
            context.metadata["api_key"] = api_key
            
            # Update request with validated API key
            if api_key:
                request.api_key = api_key
        
        return request
    
    async def process_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Process authentication response"""
        return response


class CachingMiddleware(Middleware):
    """Middleware for response caching"""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        super().__init__(config)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = self.config.config.get("cache_ttl", 300)  # 5 minutes
        self._cacheable_methods = set(self.config.config.get("cacheable_methods", ["GET"]))
        self._cacheable_status_codes = set(self.config.config.get("cacheable_status_codes", [200]))
    
    def get_name(self) -> str:
        return "caching"
    
    def get_phases(self) -> List[MiddlewarePhase]:
        return [
            MiddlewarePhase.PRE_ROUTING,
            MiddlewarePhase.POST_RESPONSE
        ]
    
    async def process_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Check cache for existing response"""
        if phase == MiddlewarePhase.PRE_ROUTING:
            if not request.cache_enabled or request.method.value not in self._cacheable_methods:
                return request
            
            cache_key = self._generate_cache_key(request)
            cached_entry = self._cache.get(cache_key)
            
            if cached_entry:
                # Check if cache is still valid
                cache_time = cached_entry["timestamp"]
                if (time.time() - cache_time) < self._cache_ttl:
                    # Cache hit - store response in context for later return
                    context.metadata["cache_hit"] = True
                    context.metadata["cached_response"] = cached_entry["response"]
                    logger.debug(f"Cache hit for key: {cache_key}")
                else:
                    # Cache expired
                    del self._cache[cache_key]
                    logger.debug(f"Cache expired for key: {cache_key}")
        
        return request
    
    async def process_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Cache successful responses"""
        if phase == MiddlewarePhase.POST_RESPONSE:
            # Don't cache if already a cache hit
            if context.metadata.get("cache_hit"):
                return response
            
            # Check if response should be cached
            if (response.status_code in self._cacheable_status_codes and 
                response.is_success):
                
                # Generate cache key from original request
                # We need to reconstruct this from response metadata
                cache_key = f"{response.request_id}:{hash(str(response.data))}"
                
                self._cache[cache_key] = {
                    "response": response,
                    "timestamp": time.time()
                }
                
                logger.debug(f"Cached response for key: {cache_key}")
        
        return response
    
    def _generate_cache_key(self, request: APIRequest) -> str:
        """Generate cache key for request"""
        key_parts = [
            request.method.value,
            request.path,
            str(hash(str(sorted(request.query_params.items()))))
        ]
        return ":".join(key_parts)
    
    def clear_cache(self):
        """Clear all cached responses"""
        self._cache.clear()
        logger.info("Response cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self._cache.values()
            if (current_time - entry["timestamp"]) < self._cache_ttl
        )
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_ttl": self._cache_ttl
        }


class MiddlewareManager:
    """
    Manages middleware pipeline execution.
    
    Coordinates the execution of multiple middleware components
    in the correct order and phases.
    """
    
    def __init__(self):
        self._middleware: List[Middleware] = []
        self._middleware_by_phase: Dict[MiddlewarePhase, List[Middleware]] = {
            phase: [] for phase in MiddlewarePhase
        }
        self._enabled = True
        
        # Manager statistics
        self._stats = {
            "total_requests_processed": 0,
            "total_responses_processed": 0,
            "errors_handled": 0,
            "average_pipeline_time_ms": 0.0,
            "start_time": datetime.utcnow()
        }
    
    def register_middleware(self, middleware: Middleware) -> bool:
        """
        Register a middleware component.
        
        Args:
            middleware: Middleware instance
            
        Returns:
            True if registration successful
        """
        try:
            if not middleware.is_enabled():
                logger.info(f"Middleware {middleware.get_name()} is disabled, skipping registration")
                return False
            
            # Insert middleware in correct order
            inserted = False
            for i, existing_middleware in enumerate(self._middleware):
                if middleware.get_order() < existing_middleware.get_order():
                    self._middleware.insert(i, middleware)
                    inserted = True
                    break
            
            if not inserted:
                self._middleware.append(middleware)
            
            # Register for relevant phases
            for phase in middleware.get_phases():
                if middleware not in self._middleware_by_phase[phase]:
                    # Insert in same order as main list
                    phase_middleware = self._middleware_by_phase[phase]
                    inserted_in_phase = False
                    
                    for i, existing_middleware in enumerate(phase_middleware):
                        if middleware.get_order() < existing_middleware.get_order():
                            phase_middleware.insert(i, middleware)
                            inserted_in_phase = True
                            break
                    
                    if not inserted_in_phase:
                        phase_middleware.append(middleware)
            
            logger.info(f"Registered middleware: {middleware.get_name()} (order: {middleware.get_order()})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register middleware {middleware.get_name()}: {e}")
            return False
    
    def unregister_middleware(self, middleware_name: str) -> bool:
        """Unregister middleware by name"""
        try:
            # Remove from main list
            self._middleware = [m for m in self._middleware if m.get_name() != middleware_name]
            
            # Remove from phase lists
            for phase_middleware in self._middleware_by_phase.values():
                phase_middleware[:] = [m for m in phase_middleware if m.get_name() != middleware_name]
            
            logger.info(f"Unregistered middleware: {middleware_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister middleware {middleware_name}: {e}")
            return False
    
    async def process_request(self, request: APIRequest) -> APIRequest:
        """
        Process request through middleware pipeline.
        
        Args:
            request: API request
            
        Returns:
            Processed API request
        """
        if not self._enabled:
            return request
        
        context = MiddlewareContext(request_id=request.request_id)
        pipeline_start = time.time()
        
        try:
            self._stats["total_requests_processed"] += 1
            
            # Execute request phases
            request_phases = [
                MiddlewarePhase.PRE_REQUEST,
                MiddlewarePhase.POST_REQUEST,
                MiddlewarePhase.PRE_ROUTING
            ]
            
            for phase in request_phases:
                request = await self._execute_phase_request(request, context, phase)
                
                # Check for cached response
                if context.metadata.get("cache_hit"):
                    cached_response = context.metadata.get("cached_response")
                    if cached_response:
                        logger.debug(f"Returning cached response for request {request.request_id}")
                        return request  # Request processing stops here for cache hits
            
            return request
            
        except Exception as e:
            self._stats["errors_handled"] += 1
            await self._handle_pipeline_error(e, context, MiddlewarePhase.PRE_REQUEST)
            raise
        
        finally:
            pipeline_time = (time.time() - pipeline_start) * 1000
            self._update_pipeline_stats(pipeline_time)
    
    async def process_response(self, response: APIResponse) -> APIResponse:
        """
        Process response through middleware pipeline.
        
        Args:
            response: API response
            
        Returns:
            Processed API response
        """
        if not self._enabled:
            return response
        
        context = MiddlewareContext(request_id=response.request_id)
        pipeline_start = time.time()
        
        try:
            self._stats["total_responses_processed"] += 1
            
            # Execute response phases
            response_phases = [
                MiddlewarePhase.POST_ROUTING,
                MiddlewarePhase.PRE_RESPONSE,
                MiddlewarePhase.POST_RESPONSE
            ]
            
            for phase in response_phases:
                response = await self._execute_phase_response(response, context, phase)
            
            return response
            
        except Exception as e:
            self._stats["errors_handled"] += 1
            await self._handle_pipeline_error(e, context, MiddlewarePhase.POST_RESPONSE)
            raise
        
        finally:
            pipeline_time = (time.time() - pipeline_start) * 1000
            self._update_pipeline_stats(pipeline_time)
    
    async def _execute_phase_request(
        self, 
        request: APIRequest, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIRequest:
        """Execute middleware for request phase"""
        phase_start = time.time()
        
        try:
            middleware_list = self._middleware_by_phase[phase]
            
            for middleware in middleware_list:
                middleware_start = time.time()
                
                try:
                    request = await middleware.process_request(request, context, phase)
                except Exception as e:
                    middleware._update_stats(0, error=True)
                    error_response = await middleware.handle_error(e, context, phase)
                    if error_response:
                        # Middleware provided error response, use it
                        raise Exception(f"Middleware {middleware.get_name()} returned error response")
                    # Otherwise continue with pipeline
                    logger.warning(f"Middleware {middleware.get_name()} error handled, continuing: {e}")
                
                finally:
                    middleware_time = (time.time() - middleware_start) * 1000
                    middleware._update_stats(middleware_time)
                    context.middleware_times[middleware.get_name()] = middleware_time
            
            return request
            
        finally:
            phase_time = (time.time() - phase_start) * 1000
            context.phase_times[phase.value] = phase_time
    
    async def _execute_phase_response(
        self, 
        response: APIResponse, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ) -> APIResponse:
        """Execute middleware for response phase"""
        phase_start = time.time()
        
        try:
            middleware_list = self._middleware_by_phase[phase]
            
            for middleware in middleware_list:
                middleware_start = time.time()
                
                try:
                    response = await middleware.process_response(response, context, phase)
                except Exception as e:
                    middleware._update_stats(0, error=True)
                    error_response = await middleware.handle_error(e, context, phase)
                    if error_response:
                        return error_response
                    logger.warning(f"Middleware {middleware.get_name()} error handled, continuing: {e}")
                
                finally:
                    middleware_time = (time.time() - middleware_start) * 1000
                    middleware._update_stats(middleware_time)
                    context.middleware_times[middleware.get_name()] = middleware_time
            
            return response
            
        finally:
            phase_time = (time.time() - phase_start) * 1000
            context.phase_times[phase.value] = phase_time
    
    async def _handle_pipeline_error(
        self, 
        error: Exception, 
        context: MiddlewareContext, 
        phase: MiddlewarePhase
    ):
        """Handle pipeline-level errors"""
        logger.error(f"Pipeline error in phase {phase}: {error}")
        
        # Execute error handling middleware
        error_middleware = self._middleware_by_phase[MiddlewarePhase.ERROR_HANDLING]
        
        for middleware in error_middleware:
            try:
                await middleware.handle_error(error, context, phase)
            except Exception as e:
                logger.error(f"Error in error handling middleware {middleware.get_name()}: {e}")
    
    def _update_pipeline_stats(self, pipeline_time_ms: float):
        """Update pipeline statistics"""
        total_processed = (self._stats["total_requests_processed"] + 
                          self._stats["total_responses_processed"])
        
        if total_processed > 0:
            current_avg = self._stats["average_pipeline_time_ms"]
            self._stats["average_pipeline_time_ms"] = (
                (current_avg * (total_processed - 1) + pipeline_time_ms) / total_processed
            )
    
    def list_middleware(self) -> List[str]:
        """List registered middleware names"""
        return [m.get_name() for m in self._middleware]
    
    def get_middleware(self, name: str) -> Optional[Middleware]:
        """Get middleware by name"""
        for middleware in self._middleware:
            if middleware.get_name() == name:
                return middleware
        return None
    
    def enable(self):
        """Enable middleware pipeline"""
        self._enabled = True
        logger.info("Middleware pipeline enabled")
    
    def disable(self):
        """Disable middleware pipeline"""
        self._enabled = False
        logger.info("Middleware pipeline disabled")
    
    def is_enabled(self) -> bool:
        """Check if middleware pipeline is enabled"""
        return self._enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware manager statistics"""
        stats = self._stats.copy()
        stats.update({
            "registered_middleware": len(self._middleware),
            "middleware_names": self.list_middleware(),
            "enabled": self._enabled,
            "uptime_seconds": (datetime.utcnow() - self._stats["start_time"]).total_seconds()
        })
        
        # Add individual middleware stats
        middleware_stats = {}
        for middleware in self._middleware:
            middleware_stats[middleware.get_name()] = middleware.get_stats()
        stats["middleware_stats"] = middleware_stats
        
        return stats


# Pre-configured middleware setups
def create_default_middleware_manager() -> MiddlewareManager:
    """Create middleware manager with default middleware"""
    manager = MiddlewareManager()
    
    # Register default middleware in order
    manager.register_middleware(LoggingMiddleware(MiddlewareConfig(
        order=MiddlewareOrder.LOGGING
    )))
    
    manager.register_middleware(MetricsMiddleware(MiddlewareConfig(
        order=MiddlewareOrder.METRICS
    )))
    
    manager.register_middleware(AuthenticationMiddleware(MiddlewareConfig(
        order=MiddlewareOrder.AUTHENTICATION,
        config={
            "require_auth": False,  # Default to no auth required
            "public_paths": ["/health", "/docs", "/stats"]
        }
    )))
    
    manager.register_middleware(CachingMiddleware(MiddlewareConfig(
        order=MiddlewareOrder.CACHING,
        config={
            "cache_ttl": 300,  # 5 minutes
            "cacheable_methods": ["GET"],
            "cacheable_status_codes": [200]
        }
    )))
    
    return manager


# Global middleware manager instance
_middleware_manager: Optional[MiddlewareManager] = None


def get_middleware_manager() -> MiddlewareManager:
    """Get the global middleware manager instance"""
    global _middleware_manager
    if _middleware_manager is None:
        _middleware_manager = create_default_middleware_manager()
    return _middleware_manager


def setup_middleware_manager(custom_middleware: Optional[List[Middleware]] = None) -> MiddlewareManager:
    """Setup and return the global middleware manager"""
    global _middleware_manager
    _middleware_manager = MiddlewareManager()
    
    # Register default middleware
    default_manager = create_default_middleware_manager()
    for middleware in default_manager._middleware:
        _middleware_manager.register_middleware(middleware)
    
    # Register custom middleware
    if custom_middleware:
        for middleware in custom_middleware:
            _middleware_manager.register_middleware(middleware)
    
    return _middleware_manager