"""
Middleware for API versioning support.

Handles version extraction, validation, and response adaptation
at the middleware level for consistent versioning across all endpoints.
"""

from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
import logging
import json

from .versioning import (
    APIVersion,
    VersionRegistry,
    VersionExtractor,
    get_version_registry,
    get_version_extractor
)
from .version_adapters import get_versioned_response_builder
from .responses import error_response

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles API versioning for all requests.
    
    Extracts version information from requests, validates versions,
    and adapts responses to the requested version format.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        version_registry: Optional[VersionRegistry] = None,
        version_extractor: Optional[VersionExtractor] = None,
        skip_paths: Optional[list] = None,
        add_version_headers: bool = True
    ):
        super().__init__(app)
        self.version_registry = version_registry or get_version_registry()
        self.version_extractor = version_extractor or get_version_extractor()
        self.response_builder = get_versioned_response_builder()
        self.skip_paths = skip_paths or [
            "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/health"
        ]
        self.add_version_headers = add_version_headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with version handling."""
        
        # Skip version processing for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Extract and validate API version
        try:
            api_version = self.version_extractor.extract_version(request)
            request.state.api_version = api_version
            
            # Log version usage for analytics
            self._log_version_usage(request, api_version)
            
        except HTTPException as e:
            # Return version error in appropriate format
            return self._create_version_error_response(e, request)
        except Exception as e:
            logger.error(f"Unexpected error in version middleware: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error during version processing"}
            )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
        
        # Add version headers if enabled
        if self.add_version_headers:
            self._add_version_headers(response, api_version)
        
        # Adapt response content if needed
        if response.status_code < 400 and hasattr(response, 'body'):
            try:
                adapted_response = self._adapt_response_content(response, api_version)
                if adapted_response:
                    return adapted_response
            except Exception as e:
                logger.warning(f"Response adaptation failed: {e}")
                # Continue with original response
        
        return response
    
    def _log_version_usage(self, request: Request, version: APIVersion) -> None:
        """Log API version usage for analytics."""
        logger.info(
            f"API request with version {version.short_version}",
            extra={
                "api_version": version.short_version,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent"),
                "is_deprecated": version.is_deprecated,
                "client_ip": request.client.host if request.client else None
            }
        )
        
        # Additional warning for deprecated versions
        if version.is_deprecated:
            logger.warning(
                f"Client using deprecated API version {version.short_version}",
                extra={
                    "api_version": version.short_version,
                    "path": request.url.path,
                    "deprecation_date": version.deprecation_date.isoformat() if version.deprecation_date else None,
                    "sunset_date": version.sunset_date.isoformat() if version.sunset_date else None,
                    "days_until_sunset": version.days_until_sunset
                }
            )
    
    def _create_version_error_response(self, error: HTTPException, request: Request) -> JSONResponse:
        """Create version-specific error response."""
        
        # Try to determine what version format to use for error
        error_version = None
        try:
            # Try to extract version even if validation failed
            path_version = self.version_extractor.extract_from_url(request.url.path)
            if path_version:
                error_version = self.version_registry.get_version(path_version)
        except:
            pass
        
        # Use default version if no version could be determined
        if not error_version:
            error_version = self.version_registry.get_default_version()
        
        # Create error response in appropriate format
        if error_version and error_version.major == 1:
            # V1 error format
            content = {
                "status": "error",
                "msg": error.detail,
                "error_code": "VERSION_ERROR",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # V2+ error format
            content = {
                "success": false,
                "message": error.detail,
                "errors": [
                    {
                        "code": "VERSION_ERROR",
                        "message": error.detail,
                        "context": {
                            "requested_path": request.url.path,
                            "supported_versions": self.version_registry.list_supported_versions()
                        }
                    }
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "error"
            }
        
        return JSONResponse(
            status_code=error.status_code,
            content=content
        )
    
    def _add_version_headers(self, response: Response, version: APIVersion) -> None:
        """Add version information to response headers."""
        response.headers["X-API-Version"] = version.short_version
        response.headers["X-API-Version-Full"] = version.version_string
        
        if version.is_deprecated:
            response.headers["X-API-Deprecated"] = "true"
            if version.deprecation_date:
                response.headers["X-API-Deprecated-Since"] = version.deprecation_date.isoformat()
            if version.sunset_date:
                response.headers["X-API-Sunset-Date"] = version.sunset_date.isoformat()
                if version.days_until_sunset is not None:
                    response.headers["X-API-Days-Until-Sunset"] = str(version.days_until_sunset)
        
        if version.is_experimental:
            response.headers["X-API-Experimental"] = "true"
        
        # Add supported versions
        supported_versions = self.version_registry.list_supported_versions()
        response.headers["X-API-Supported-Versions"] = ",".join(supported_versions)
        
        # Add latest version info
        latest_version = self.version_registry.get_latest_version()
        if latest_version:
            response.headers["X-API-Latest-Version"] = latest_version.short_version
    
    def _adapt_response_content(self, response: Response, version: APIVersion) -> Optional[JSONResponse]:
        """Adapt response content to requested version format."""
        
        # Only process JSON responses
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return None
        
        try:
            # Get response body
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    content = json.loads(body.decode())
                else:
                    content = body
            else:
                return None
            
            # Adapt content to requested version
            adapted_content = self.response_builder.build_response(content, version)
            
            # Create new response with adapted content
            if adapted_content != content:
                return JSONResponse(
                    status_code=response.status_code,
                    content=adapted_content,
                    headers=dict(response.headers)
                )
            
        except Exception as e:
            logger.warning(f"Failed to adapt response content: {e}")
        
        return None


class VersionDeprecationMiddleware(BaseHTTPMiddleware):
    """
    Middleware specifically for handling version deprecation warnings.
    
    Adds deprecation warnings and notices to responses when clients
    use deprecated API versions.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        version_registry: Optional[VersionRegistry] = None,
        add_deprecation_warnings: bool = True,
        log_deprecated_usage: bool = True
    ):
        super().__init__(app)
        self.version_registry = version_registry or get_version_registry()
        self.add_deprecation_warnings = add_deprecation_warnings
        self.log_deprecated_usage = log_deprecated_usage
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with deprecation handling."""
        
        # Get API version from request state (set by APIVersionMiddleware)
        api_version = getattr(request.state, 'api_version', None)
        if not api_version:
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Handle deprecation for deprecated versions
        if api_version.is_deprecated:
            if self.log_deprecated_usage:
                self._log_deprecation_usage(request, api_version)
            
            if self.add_deprecation_warnings:
                self._add_deprecation_headers(response, api_version)
                
                # Add deprecation notice to JSON responses
                if (response.headers.get("content-type", "").startswith("application/json") and
                    response.status_code < 400):
                    self._add_deprecation_notice(response, api_version)
        
        return response
    
    def _log_deprecation_usage(self, request: Request, version: APIVersion) -> None:
        """Log usage of deprecated API version."""
        logger.warning(
            f"Deprecated API version {version.short_version} used",
            extra={
                "api_version": version.short_version,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
                "deprecation_date": version.deprecation_date.isoformat() if version.deprecation_date else None,
                "sunset_date": version.sunset_date.isoformat() if version.sunset_date else None
            }
        )
    
    def _add_deprecation_headers(self, response: Response, version: APIVersion) -> None:
        """Add deprecation headers to response."""
        response.headers["X-API-Deprecated"] = "true"
        
        if version.deprecation_date:
            response.headers["X-API-Deprecated-Since"] = version.deprecation_date.isoformat()
        
        if version.sunset_date:
            response.headers["X-API-Sunset-Date"] = version.sunset_date.isoformat()
            
            if version.days_until_sunset is not None:
                response.headers["X-API-Days-Until-Sunset"] = str(version.days_until_sunset)
        
        # Add migration information
        latest_version = self.version_registry.get_latest_version()
        if latest_version:
            response.headers["X-API-Recommended-Version"] = latest_version.short_version
    
    def _add_deprecation_notice(self, response: Response, version: APIVersion) -> None:
        """Add deprecation notice to JSON response body."""
        try:
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    content = json.loads(body.decode())
                else:
                    content = body
                
                # Add deprecation notice
                if isinstance(content, dict):
                    content["_deprecation_notice"] = {
                        "message": f"API version {version.short_version} is deprecated",
                        "deprecated_since": version.deprecation_date.isoformat() if version.deprecation_date else None,
                        "sunset_date": version.sunset_date.isoformat() if version.sunset_date else None,
                        "days_until_sunset": version.days_until_sunset,
                        "recommended_version": self.version_registry.get_latest_version().short_version if self.version_registry.get_latest_version() else None,
                        "migration_guide": f"Please migrate to the latest API version to ensure continued service."
                    }
                    
                    # Update response body
                    new_body = json.dumps(content).encode()
                    response.headers["content-length"] = str(len(new_body))
                    
                    # Note: Modifying response body in middleware is complex
                    # This is a simplified example - in production, consider using
                    # response modification at the application level
        
        except Exception as e:
            logger.warning(f"Failed to add deprecation notice to response: {e}")


# Middleware factory functions
def create_version_middleware(
    version_registry: Optional[VersionRegistry] = None,
    skip_paths: Optional[list] = None,
    add_version_headers: bool = True
):
    """
    Create API version middleware with specified configuration.
    
    Args:
        version_registry: Custom version registry
        skip_paths: Paths to skip version processing
        add_version_headers: Whether to add version headers
        
    Returns:
        Callable that creates APIVersionMiddleware instance
    """
    def middleware_factory(app):
        return APIVersionMiddleware(
            app=app,
            version_registry=version_registry,
            skip_paths=skip_paths,
            add_version_headers=add_version_headers
        )
    return middleware_factory


def create_deprecation_middleware(
    version_registry: Optional[VersionRegistry] = None,
    add_deprecation_warnings: bool = True,
    log_deprecated_usage: bool = True
):
    """
    Create version deprecation middleware.
    
    Args:
        version_registry: Custom version registry
        add_deprecation_warnings: Whether to add deprecation warnings
        log_deprecated_usage: Whether to log deprecated API usage
        
    Returns:
        Callable that creates VersionDeprecationMiddleware instance
    """
    def middleware_factory(app):
        return VersionDeprecationMiddleware(
            app=app,
            version_registry=version_registry,
            add_deprecation_warnings=add_deprecation_warnings,
            log_deprecated_usage=log_deprecated_usage
        )
    return middleware_factory