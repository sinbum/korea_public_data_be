"""
Versioned routing system for API endpoints.

Provides automatic version routing, response adaptation, and 
backward compatibility management.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
import logging
from functools import wraps

from .versioning import (
    APIVersion, 
    VersionRegistry, 
    VersionExtractor, 
    get_api_version,
    get_version_registry,
    get_version_extractor
)
from .version_adapters import get_versioned_response_builder
from .responses import BaseResponse

logger = logging.getLogger(__name__)


class VersionedAPIRouter(APIRouter):
    """
    Extended APIRouter that supports automatic API versioning.
    
    Routes can be registered with version requirements and responses
    are automatically adapted to the requested version format.
    """
    
    def __init__(
        self,
        *,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[Depends]] = None,
        default_version: Optional[str] = None,
        supported_versions: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            **kwargs
        )
        
        self.default_version = default_version
        self.supported_versions = supported_versions or []
        self.version_registry = get_version_registry()
        self.version_extractor = get_version_extractor()
        self.response_builder = get_versioned_response_builder()
        
        # Version-specific route handlers
        self._version_handlers: Dict[str, Dict[str, Callable]] = {}
        
    def add_versioned_route(
        self,
        path: str,
        endpoint: Callable,
        *,
        methods: Optional[List[str]] = None,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
        deprecated_in: Optional[str] = None,
        removed_in: Optional[str] = None,
        **kwargs
    ):
        """
        Add a versioned route with version constraints.
        
        Args:
            path: Route path
            endpoint: Endpoint function
            methods: HTTP methods
            min_version: Minimum supported version
            max_version: Maximum supported version  
            deprecated_in: Version where this endpoint was deprecated
            removed_in: Version where this endpoint was removed
            **kwargs: Additional route parameters
        """
        methods = methods or ["GET"]
        
        # Create version-aware endpoint wrapper
        async def versioned_endpoint(request: Request, *args, **kwargs):
            # Get current API version
            try:
                current_version = self.version_extractor.extract_version(request)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Version extraction failed: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
            
            # Check version constraints
            if min_version:
                min_ver = self._parse_version(min_version)
                if current_version < min_ver:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint requires API version {min_version} or higher"
                    )
            
            if max_version:
                max_ver = self._parse_version(max_version)
                if current_version > max_ver:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint supports API version up to {max_version}"
                    )
            
            # Check if endpoint is deprecated or removed
            if removed_in:
                removed_ver = self._parse_version(removed_in)
                if current_version >= removed_ver:
                    raise HTTPException(
                        status_code=410,  # Gone
                        detail=f"This endpoint was removed in API version {removed_in}"
                    )
            
            if deprecated_in:
                deprecated_ver = self._parse_version(deprecated_in)
                if current_version >= deprecated_ver:
                    logger.warning(
                        f"Client using deprecated endpoint {path} in version {current_version.short_version}",
                        extra={
                            "endpoint": path,
                            "version": current_version.short_version,
                            "deprecated_since": deprecated_in
                        }
                    )
            
            # Call original endpoint
            response = await endpoint(request, *args, **kwargs)
            
            # Adapt response to requested version
            if isinstance(response, (dict, BaseResponse)):
                adapted_response = self.response_builder.build_response(
                    response, current_version
                )
                return adapted_response
            
            return response
        
        # Add route with versioned endpoint
        super().add_api_route(
            path=path,
            endpoint=versioned_endpoint,
            methods=methods,
            **kwargs
        )
    
    def _parse_version(self, version_string: str) -> APIVersion:
        """Parse version string to APIVersion object."""
        if not version_string.startswith('v'):
            version_string = f"v{version_string}"
        
        version = self.version_registry.get_version(version_string)
        if not version:
            raise ValueError(f"Unknown version: {version_string}")
        
        return version
    
    def get(self, path: str, **kwargs):
        """Add GET route with version support."""
        def decorator(func):
            self.add_versioned_route(path, func, methods=["GET"], **kwargs)
            return func
        return decorator
    
    def post(self, path: str, **kwargs):
        """Add POST route with version support."""
        def decorator(func):
            self.add_versioned_route(path, func, methods=["POST"], **kwargs)
            return func
        return decorator
    
    def put(self, path: str, **kwargs):
        """Add PUT route with version support."""
        def decorator(func):
            self.add_versioned_route(path, func, methods=["PUT"], **kwargs)
            return func
        return decorator
    
    def delete(self, path: str, **kwargs):
        """Add DELETE route with version support."""
        def decorator(func):
            self.add_versioned_route(path, func, methods=["DELETE"], **kwargs)
            return func
        return decorator
    
    def patch(self, path: str, **kwargs):
        """Add PATCH route with version support.""" 
        def decorator(func):
            self.add_versioned_route(path, func, methods=["PATCH"], **kwargs)
            return func
        return decorator


def version_specific(
    version: str,
    *,
    min_version: Optional[str] = None,
    max_version: Optional[str] = None,
    deprecated_in: Optional[str] = None,
    removed_in: Optional[str] = None
):
    """
    Decorator to mark endpoints as version-specific.
    
    Args:
        version: Specific version this endpoint applies to
        min_version: Minimum supported version
        max_version: Maximum supported version
        deprecated_in: Version where endpoint was deprecated
        removed_in: Version where endpoint was removed
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            request: Request,
            current_version: APIVersion = Depends(get_api_version),
            *args,
            **kwargs
        ):
            # Check version constraints
            target_version = version.lstrip('v')
            current_version_str = current_version.short_version.lstrip('v')
            
            if target_version != current_version_str and min_version:
                min_ver = min_version.lstrip('v')
                if current_version_str < min_ver:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint requires API version {min_version} or higher"
                    )
            
            if max_version:
                max_ver = max_version.lstrip('v')
                if current_version_str > max_ver:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint supports API version up to {max_version}"
                    )
            
            # Check deprecation/removal
            if removed_in:
                removed_ver = removed_in.lstrip('v')
                if current_version_str >= removed_ver:
                    raise HTTPException(
                        status_code=410,
                        detail=f"This endpoint was removed in API version {removed_in}"
                    )
            
            if deprecated_in:
                deprecated_ver = deprecated_in.lstrip('v')
                if current_version_str >= deprecated_ver:
                    logger.warning(
                        f"Client using deprecated endpoint in version {current_version.short_version}"
                    )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def deprecated(since_version: str, removed_in: Optional[str] = None):
    """
    Decorator to mark endpoints as deprecated.
    
    Args:
        since_version: Version when endpoint was deprecated
        removed_in: Version when endpoint will be removed
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            request: Request,
            current_version: APIVersion = Depends(get_api_version),
            *args,
            **kwargs
        ):
            # Log deprecation warning
            logger.warning(
                f"Client using deprecated endpoint {request.url.path}",
                extra={
                    "endpoint": str(request.url.path),
                    "version": current_version.short_version,
                    "deprecated_since": since_version,
                    "removed_in": removed_in,
                    "user_agent": request.headers.get("user-agent")
                }
            )
            
            # Check if endpoint should be removed
            if removed_in:
                removed_ver = APIVersion(
                    major=int(removed_in.split('.')[0].lstrip('v')),
                    minor=int(removed_in.split('.')[1]) if '.' in removed_in else 0
                )
                if current_version >= removed_ver:
                    raise HTTPException(
                        status_code=410,
                        detail=f"This endpoint was removed in API version {removed_in}"
                    )
            
            # Add deprecation headers
            response = await func(request, *args, **kwargs)
            
            if isinstance(response, Response):
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Deprecated-Since"] = since_version
                if removed_in:
                    response.headers["X-API-Removed-In"] = removed_in
            
            return response
        
        return wrapper
    return decorator


def experimental(version: str):
    """
    Decorator to mark endpoints as experimental.
    
    Args:
        version: Version when endpoint was introduced as experimental
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            logger.info(
                f"Client using experimental endpoint {request.url.path}",
                extra={
                    "endpoint": str(request.url.path),
                    "introduced_in": version,
                    "user_agent": request.headers.get("user-agent")
                }
            )
            
            response = await func(request, *args, **kwargs)
            
            if isinstance(response, Response):
                response.headers["X-API-Experimental"] = "true"
                response.headers["X-API-Introduced-In"] = version
            
            return response
        
        return wrapper
    return decorator


def version_compatibility_check(
    min_version: str,
    max_version: Optional[str] = None
):
    """
    Dependency to check version compatibility.
    
    Args:
        min_version: Minimum required version
        max_version: Maximum allowed version
    """
    def check_version(current_version: APIVersion = Depends(get_api_version)) -> APIVersion:
        # Parse minimum version
        min_parts = min_version.lstrip('v').split('.')
        min_major = int(min_parts[0])
        min_minor = int(min_parts[1]) if len(min_parts) > 1 else 0
        min_patch = int(min_parts[2]) if len(min_parts) > 2 else 0
        
        min_ver = APIVersion(major=min_major, minor=min_minor, patch=min_patch)
        
        if current_version < min_ver:
            raise HTTPException(
                status_code=400,
                detail=f"This endpoint requires API version {min_version} or higher. "
                       f"Current version: {current_version.short_version}"
            )
        
        # Check maximum version if specified
        if max_version:
            max_parts = max_version.lstrip('v').split('.')
            max_major = int(max_parts[0])
            max_minor = int(max_parts[1]) if len(max_parts) > 1 else 999
            max_patch = int(max_parts[2]) if len(max_parts) > 2 else 999
            
            max_ver = APIVersion(major=max_major, minor=max_minor, patch=max_patch)
            
            if current_version > max_ver:
                raise HTTPException(
                    status_code=400,
                    detail=f"This endpoint supports API version up to {max_version}. "
                           f"Current version: {current_version.short_version}"
                )
        
        return current_version
    
    return check_version


# Utility functions for route registration
def create_versioned_router(
    prefix: str,
    tags: Optional[List[str]] = None,
    default_version: str = "v1",
    supported_versions: Optional[List[str]] = None
) -> VersionedAPIRouter:
    """
    Create a new versioned API router.
    
    Args:
        prefix: Router prefix
        tags: OpenAPI tags
        default_version: Default API version
        supported_versions: List of supported versions
        
    Returns:
        VersionedAPIRouter instance
    """
    return VersionedAPIRouter(
        prefix=prefix,
        tags=tags,
        default_version=default_version,
        supported_versions=supported_versions or ["v1", "v2"]
    )


def add_version_info_endpoint(router: APIRouter):
    """Add version information endpoint to router."""
    
    @router.get(
        "/version",
        summary="API 버전 정보",
        description="현재 지원되는 API 버전 정보를 조회합니다.",
        response_description="API 버전 정보"
    )
    async def get_version_info(
        current_version: APIVersion = Depends(get_api_version)
    ):
        """API 버전 정보 조회"""
        registry = get_version_registry()
        
        supported_versions = []
        for version in registry.list_versions():
            supported_versions.append({
                "version": version.version_string,
                "short_version": version.short_version,
                "is_stable": version.is_stable,
                "is_deprecated": version.is_deprecated,
                "is_current": version.is_current,
                "release_date": version.release_date.isoformat() if version.release_date else None,
                "deprecation_date": version.deprecation_date.isoformat() if version.deprecation_date else None,
                "sunset_date": version.sunset_date.isoformat() if version.sunset_date else None,
                "days_until_sunset": version.days_until_sunset
            })
        
        return {
            "current_version": {
                "version": current_version.version_string,
                "short_version": current_version.short_version,
                "is_stable": current_version.is_stable,
                "is_deprecated": current_version.is_deprecated
            },
            "supported_versions": supported_versions,
            "default_version": registry.get_default_version().short_version if registry.get_default_version() else None,
            "latest_version": registry.get_latest_version().short_version if registry.get_latest_version() else None
        }