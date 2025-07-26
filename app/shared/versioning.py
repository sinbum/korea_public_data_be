"""
API versioning strategy implementation.

Provides flexible versioning support through URL path, headers, and query parameters
with backward compatibility and deprecation management.
"""

from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from fastapi import Request, HTTPException, Header, Query
from fastapi.routing import APIRoute
import re
import logging

logger = logging.getLogger(__name__)


class VersioningMethod(str, Enum):
    """Supported API versioning methods."""
    URL_PATH = "url_path"  # /api/v1/resource
    HEADER = "header"      # Accept: application/vnd.api+json;version=1
    QUERY_PARAM = "query"  # /api/resource?version=1
    CONTENT_TYPE = "content_type"  # Content-Type: application/vnd.api.v1+json


class APIVersion(BaseModel):
    """API version information and metadata."""
    
    major: int = Field(..., ge=1, description="Major version number")
    minor: int = Field(default=0, ge=0, description="Minor version number") 
    patch: int = Field(default=0, ge=0, description="Patch version number")
    label: Optional[str] = Field(None, description="Version label (alpha, beta, rc)")
    
    # Lifecycle metadata
    release_date: Optional[date] = Field(None, description="Version release date")
    deprecation_date: Optional[date] = Field(None, description="Version deprecation date")
    sunset_date: Optional[date] = Field(None, description="Version sunset/removal date")
    
    # Status flags
    is_stable: bool = Field(default=True, description="Whether version is stable")
    is_deprecated: bool = Field(default=False, description="Whether version is deprecated")
    is_experimental: bool = Field(default=False, description="Whether version is experimental")
    
    @validator('deprecation_date')
    def validate_deprecation_date(cls, v, values):
        """Ensure deprecation date is after release date."""
        if v and values.get('release_date') and v <= values['release_date']:
            raise ValueError("Deprecation date must be after release date")
        return v
    
    @validator('sunset_date') 
    def validate_sunset_date(cls, v, values):
        """Ensure sunset date is after deprecation date."""
        if v and values.get('deprecation_date') and v <= values['deprecation_date']:
            raise ValueError("Sunset date must be after deprecation date")
        return v
    
    @property
    def version_string(self) -> str:
        """Get full version string (e.g., '1.2.3-beta')."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.label:
            version += f"-{self.label}"
        return version
    
    @property
    def short_version(self) -> str:
        """Get short version string (e.g., 'v1', 'v2.1')."""
        if self.minor == 0 and self.patch == 0:
            return f"v{self.major}"
        elif self.patch == 0:
            return f"v{self.major}.{self.minor}"
        else:
            return f"v{self.major}.{self.minor}.{self.patch}"
    
    @property
    def is_current(self) -> bool:
        """Check if this version is current (not deprecated or sunset)."""
        today = date.today()
        if self.sunset_date and today >= self.sunset_date:
            return False
        return not self.is_deprecated
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Get number of days until sunset, if applicable."""
        if not self.sunset_date:
            return None
        delta = self.sunset_date - date.today()
        return max(0, delta.days)
    
    def compare(self, other: 'APIVersion') -> int:
        """Compare versions. Returns -1, 0, or 1."""
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)
        
        if self_tuple < other_tuple:
            return -1
        elif self_tuple > other_tuple:
            return 1
        else:
            return 0
    
    def __lt__(self, other: 'APIVersion') -> bool:
        return self.compare(other) < 0
    
    def __le__(self, other: 'APIVersion') -> bool:
        return self.compare(other) <= 0
    
    def __gt__(self, other: 'APIVersion') -> bool:
        return self.compare(other) > 0
    
    def __ge__(self, other: 'APIVersion') -> bool:
        return self.compare(other) >= 0
    
    def __eq__(self, other: 'APIVersion') -> bool:
        return self.compare(other) == 0


class VersionRegistry:
    """Central registry for managing API versions."""
    
    def __init__(self):
        self._versions: Dict[str, APIVersion] = {}
        self._default_version: Optional[str] = None
        self._latest_version: Optional[str] = None
    
    def register_version(
        self,
        version: APIVersion,
        is_default: bool = False,
        is_latest: bool = False
    ) -> None:
        """Register a new API version."""
        version_key = version.short_version
        
        # Validate version doesn't already exist
        if version_key in self._versions:
            raise ValueError(f"Version {version_key} already registered")
        
        self._versions[version_key] = version
        
        if is_default or self._default_version is None:
            self._default_version = version_key
        
        if is_latest or self._latest_version is None:
            self._latest_version = version_key
        elif version > self._versions[self._latest_version]:
            self._latest_version = version_key
        
        logger.info(f"Registered API version {version.version_string} as {version_key}")
    
    def get_version(self, version_key: str) -> Optional[APIVersion]:
        """Get version by key (e.g., 'v1', 'v2.1')."""
        return self._versions.get(version_key)
    
    def get_default_version(self) -> Optional[APIVersion]:
        """Get the default API version."""
        if self._default_version:
            return self._versions[self._default_version]
        return None
    
    def get_latest_version(self) -> Optional[APIVersion]:
        """Get the latest API version."""
        if self._latest_version:
            return self._versions[self._latest_version]
        return None
    
    def list_versions(self, include_deprecated: bool = True) -> List[APIVersion]:
        """List all registered versions."""
        versions = list(self._versions.values())
        if not include_deprecated:
            versions = [v for v in versions if not v.is_deprecated]
        return sorted(versions, reverse=True)  # Latest first
    
    def list_supported_versions(self) -> List[str]:
        """List all currently supported version keys."""
        return [
            key for key, version in self._versions.items()
            if version.is_current
        ]
    
    def is_version_supported(self, version_key: str) -> bool:
        """Check if a version is currently supported."""
        version = self.get_version(version_key)
        return version is not None and version.is_current
    
    def deprecate_version(self, version_key: str, sunset_date: Optional[date] = None) -> None:
        """Mark a version as deprecated."""
        if version_key not in self._versions:
            raise ValueError(f"Version {version_key} not found")
        
        version = self._versions[version_key]
        version.is_deprecated = True
        version.deprecation_date = date.today()
        
        if sunset_date:
            version.sunset_date = sunset_date
        
        logger.warning(f"Deprecated API version {version_key}")
    
    def remove_version(self, version_key: str) -> None:
        """Remove a version from registry (for sunset versions)."""
        if version_key not in self._versions:
            raise ValueError(f"Version {version_key} not found")
        
        del self._versions[version_key]
        
        # Update default/latest if needed
        if self._default_version == version_key:
            self._default_version = None
            if self._versions:
                # Set to latest remaining version
                latest = max(self._versions.values())
                self._default_version = latest.short_version
        
        if self._latest_version == version_key:
            self._latest_version = None
            if self._versions:
                latest = max(self._versions.values())
                self._latest_version = latest.short_version
        
        logger.info(f"Removed API version {version_key}")


class VersionExtractor:
    """Extract version information from requests."""
    
    def __init__(
        self,
        registry: VersionRegistry,
        default_method: VersioningMethod = VersioningMethod.URL_PATH,
        fallback_methods: Optional[List[VersioningMethod]] = None
    ):
        self.registry = registry
        self.default_method = default_method
        self.fallback_methods = fallback_methods or [
            VersioningMethod.HEADER,
            VersioningMethod.QUERY_PARAM
        ]
        
        # Regex patterns for version extraction
        self.url_pattern = re.compile(r'/api/v(\d+(?:\.\d+)?(?:\.\d+)?)')
        self.header_pattern = re.compile(r'version=(\d+(?:\.\d+)?(?:\.\d+)?)')
        self.content_type_pattern = re.compile(r'application/vnd\.api\.v(\d+(?:\.\d+)?(?:\.\d+)?)\+json')
    
    def extract_from_url(self, path: str) -> Optional[str]:
        """Extract version from URL path."""
        match = self.url_pattern.search(path)
        if match:
            version = match.group(1)
            # Normalize to short version format
            parts = version.split('.')
            if len(parts) == 1:
                return f"v{parts[0]}"
            elif len(parts) == 2:
                return f"v{parts[0]}.{parts[1]}"
            else:
                return f"v{version}"
        return None
    
    def extract_from_header(self, accept_header: Optional[str]) -> Optional[str]:
        """Extract version from Accept header."""
        if not accept_header:
            return None
        
        match = self.header_pattern.search(accept_header)
        if match:
            version = match.group(1)
            return f"v{version}"
        return None
    
    def extract_from_content_type(self, content_type: Optional[str]) -> Optional[str]:
        """Extract version from Content-Type header."""
        if not content_type:
            return None
        
        match = self.content_type_pattern.search(content_type)
        if match:
            version = match.group(1)
            return f"v{version}"
        return None
    
    def extract_from_query(self, query_params: Dict[str, Any]) -> Optional[str]:
        """Extract version from query parameters."""
        version = query_params.get('version') or query_params.get('api_version')
        if version:
            if isinstance(version, str) and version.startswith('v'):
                return version
            else:
                return f"v{version}"
        return None
    
    def extract_version(self, request: Request, version_param: Optional[str] = None) -> APIVersion:
        """
        Extract API version from request using configured methods.
        
        Args:
            request: FastAPI request object
            version_param: Optional explicit version parameter
            
        Returns:
            APIVersion object
            
        Raises:
            HTTPException: If version is unsupported or invalid
        """
        extracted_version = None
        
        # Try explicit version parameter first
        if version_param:
            extracted_version = version_param if version_param.startswith('v') else f"v{version_param}"
        
        # Try default method
        if not extracted_version:
            if self.default_method == VersioningMethod.URL_PATH:
                extracted_version = self.extract_from_url(str(request.url.path))
            elif self.default_method == VersioningMethod.HEADER:
                extracted_version = self.extract_from_header(request.headers.get('accept'))
            elif self.default_method == VersioningMethod.QUERY_PARAM:
                extracted_version = self.extract_from_query(dict(request.query_params))
            elif self.default_method == VersioningMethod.CONTENT_TYPE:
                extracted_version = self.extract_from_content_type(request.headers.get('content-type'))
        
        # Try fallback methods
        if not extracted_version:
            for method in self.fallback_methods:
                if method == VersioningMethod.URL_PATH:
                    extracted_version = self.extract_from_url(str(request.url.path))
                elif method == VersioningMethod.HEADER:
                    extracted_version = self.extract_from_header(request.headers.get('accept'))
                elif method == VersioningMethod.QUERY_PARAM:
                    extracted_version = self.extract_from_query(dict(request.query_params))
                elif method == VersioningMethod.CONTENT_TYPE:
                    extracted_version = self.extract_from_content_type(request.headers.get('content-type'))
                
                if extracted_version:
                    break
        
        # Use default version if none found
        if not extracted_version:
            default_version = self.registry.get_default_version()
            if default_version:
                extracted_version = default_version.short_version
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No API version specified and no default version configured"
                )
        
        # Validate version exists and is supported
        version = self.registry.get_version(extracted_version)
        if not version:
            supported_versions = self.registry.list_supported_versions()
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported API version '{extracted_version}'. "
                       f"Supported versions: {', '.join(supported_versions)}"
            )
        
        # Check if version is deprecated or sunset
        if not version.is_current:
            if version.sunset_date and date.today() >= version.sunset_date:
                raise HTTPException(
                    status_code=410,  # Gone
                    detail=f"API version '{extracted_version}' has been sunset and is no longer available"
                )
            elif version.is_deprecated:
                logger.warning(
                    f"Client using deprecated API version {extracted_version}",
                    extra={
                        "version": extracted_version,
                        "user_agent": request.headers.get("user-agent"),
                        "path": str(request.url.path)
                    }
                )
        
        return version


class VersionedRoute(APIRoute):
    """Custom route class that adds version information to request state."""
    
    def __init__(self, *args, version_extractor: VersionExtractor, **kwargs):
        super().__init__(*args, **kwargs)
        self.version_extractor = version_extractor
    
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request):
            # Extract and validate version
            try:
                version = self.version_extractor.extract_version(request)
                request.state.api_version = version
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error extracting API version: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
            
            return await original_route_handler(request)
        
        return custom_route_handler


# FastAPI dependency functions
def get_api_version(request: Request) -> APIVersion:
    """FastAPI dependency to get current API version."""
    if hasattr(request.state, 'api_version'):
        return request.state.api_version
    else:
        raise HTTPException(
            status_code=500,
            detail="API version not available in request state"
        )


def require_version(min_version: str, max_version: Optional[str] = None):
    """
    Dependency factory to require specific version range.
    
    Args:
        min_version: Minimum required version (e.g., 'v2.0')
        max_version: Maximum allowed version (optional)
    
    Returns:
        FastAPI dependency function
    """
    def version_requirement(version: APIVersion = get_api_version) -> APIVersion:
        # Parse min version
        min_parts = min_version.lstrip('v').split('.')
        min_major = int(min_parts[0])
        min_minor = int(min_parts[1]) if len(min_parts) > 1 else 0
        min_patch = int(min_parts[2]) if len(min_parts) > 2 else 0
        
        if (version.major < min_major or 
            (version.major == min_major and version.minor < min_minor) or
            (version.major == min_major and version.minor == min_minor and version.patch < min_patch)):
            raise HTTPException(
                status_code=400,
                detail=f"This endpoint requires API version {min_version} or higher"
            )
        
        # Check max version if specified
        if max_version:
            max_parts = max_version.lstrip('v').split('.')
            max_major = int(max_parts[0])
            max_minor = int(max_parts[1]) if len(max_parts) > 1 else 999
            max_patch = int(max_parts[2]) if len(max_parts) > 2 else 999
            
            if (version.major > max_major or 
                (version.major == max_major and version.minor > max_minor) or
                (version.major == max_major and version.minor == max_minor and version.patch > max_patch)):
                raise HTTPException(
                    status_code=400,
                    detail=f"This endpoint supports API version up to {max_version}"
                )
        
        return version
    
    return version_requirement


# Utility functions
def create_version_registry() -> VersionRegistry:
    """Create and configure the default version registry."""
    registry = VersionRegistry()
    
    # Register current supported versions
    # Version 1.0 - Initial stable release
    v1 = APIVersion(
        major=1,
        minor=0,
        patch=0,
        release_date=date(2024, 1, 1),
        is_stable=True
    )
    registry.register_version(v1, is_default=True)
    
    # Version 2.0 - Current development version
    v2 = APIVersion(
        major=2,
        minor=0,
        patch=0,
        release_date=date(2024, 7, 1),
        is_stable=True
    )
    registry.register_version(v2, is_latest=True)
    
    return registry


def create_version_extractor(registry: VersionRegistry) -> VersionExtractor:
    """Create version extractor with default configuration."""
    return VersionExtractor(
        registry=registry,
        default_method=VersioningMethod.URL_PATH,
        fallback_methods=[VersioningMethod.HEADER, VersioningMethod.QUERY_PARAM]
    )


# Global registry instance
_global_registry: Optional[VersionRegistry] = None
_global_extractor: Optional[VersionExtractor] = None


def get_version_registry() -> VersionRegistry:
    """Get the global version registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = create_version_registry()
    return _global_registry


def get_version_extractor() -> VersionExtractor:
    """Get the global version extractor instance."""
    global _global_extractor
    if _global_extractor is None:
        _global_extractor = create_version_extractor(get_version_registry())
    return _global_extractor