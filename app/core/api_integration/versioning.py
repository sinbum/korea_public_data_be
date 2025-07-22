"""
API Versioning and Compatibility System - manages API versions and compatibility.

Provides version management, compatibility checking, and migration support
for maintaining backward compatibility across different API versions.
"""

import re
from typing import Dict, List, Optional, Any, Union, Callable, Set
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator
import logging

from .gateway import APIRequest, APIResponse

logger = logging.getLogger(__name__)


class VersionFormat(str, Enum):
    """Supported version formats"""
    SEMANTIC = "semantic"  # v1.2.3
    SIMPLE = "simple"      # v1, v2
    DATE = "date"          # 2024-01-01


class CompatibilityLevel(str, Enum):
    """Compatibility levels between versions"""
    FULLY_COMPATIBLE = "fully_compatible"        # No changes needed
    BACKWARD_COMPATIBLE = "backward_compatible"  # Old clients work, new features available
    BREAKING_CHANGES = "breaking_changes"        # Migration required
    DEPRECATED = "deprecated"                    # Version is deprecated
    UNSUPPORTED = "unsupported"                  # Version no longer supported


class APIVersion(BaseModel):
    """API version information"""
    version: str = Field(..., description="Version string (e.g., v1.2.3)")
    format: VersionFormat = Field(VersionFormat.SEMANTIC, description="Version format")
    release_date: datetime = Field(default_factory=datetime.utcnow, description="Release date")
    is_active: bool = Field(True, description="Whether version is active")
    is_deprecated: bool = Field(False, description="Whether version is deprecated")
    deprecation_date: Optional[datetime] = Field(None, description="Deprecation date")
    end_of_life_date: Optional[datetime] = Field(None, description="End of life date")
    
    # Compatibility information
    compatible_versions: List[str] = Field(default_factory=list, description="Compatible version list")
    breaking_changes: List[str] = Field(default_factory=list, description="List of breaking changes")
    migration_notes: str = Field("", description="Migration instructions")
    
    # Version metadata
    description: str = Field("", description="Version description")
    changelog: List[str] = Field(default_factory=list, description="Changelog entries")
    features: List[str] = Field(default_factory=list, description="New features in this version")
    
    @validator('version')
    def validate_version_format(cls, v, values):
        """Validate version format"""
        format_type = values.get('format', VersionFormat.SEMANTIC)
        
        if format_type == VersionFormat.SEMANTIC:
            if not re.match(r'^v?\d+\.\d+\.\d+$', v):
                raise ValueError("Semantic version must follow vX.Y.Z format")
        elif format_type == VersionFormat.SIMPLE:
            if not re.match(r'^v?\d+$', v):
                raise ValueError("Simple version must follow vX format")
        elif format_type == VersionFormat.DATE:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError("Date version must follow YYYY-MM-DD format")
        
        return v
    
    @property
    def major_version(self) -> int:
        """Extract major version number"""
        if self.format == VersionFormat.SEMANTIC:
            return int(self.version.lstrip('v').split('.')[0])
        elif self.format == VersionFormat.SIMPLE:
            return int(self.version.lstrip('v'))
        return 1
    
    @property
    def minor_version(self) -> int:
        """Extract minor version number"""
        if self.format == VersionFormat.SEMANTIC:
            return int(self.version.lstrip('v').split('.')[1])
        return 0
    
    @property
    def patch_version(self) -> int:
        """Extract patch version number"""
        if self.format == VersionFormat.SEMANTIC:
            return int(self.version.lstrip('v').split('.')[2])
        return 0


class VersionCompatibility(BaseModel):
    """Version compatibility information"""
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(..., description="Target version")
    compatibility_level: CompatibilityLevel = Field(..., description="Compatibility level")
    migration_required: bool = Field(False, description="Whether migration is required")
    migration_path: List[str] = Field(default_factory=list, description="Migration steps")
    warnings: List[str] = Field(default_factory=list, description="Compatibility warnings")
    deprecated_features: List[str] = Field(default_factory=list, description="Deprecated features")


class VersionMigration(ABC):
    """Base class for version migrations"""
    
    @abstractmethod
    def get_source_version(self) -> str:
        """Get source version for this migration"""
        pass
    
    @abstractmethod
    def get_target_version(self) -> str:
        """Get target version for this migration"""
        pass
    
    @abstractmethod
    async def migrate_request(self, request: APIRequest) -> APIRequest:
        """Migrate request from source to target version"""
        pass
    
    @abstractmethod
    async def migrate_response(self, response: APIResponse) -> APIResponse:
        """Migrate response from target to source version"""
        pass
    
    def get_migration_info(self) -> Dict[str, Any]:
        """Get migration information"""
        return {
            "source_version": self.get_source_version(),
            "target_version": self.get_target_version(),
            "migration_type": self.__class__.__name__
        }


class APIVersionManager:
    """
    API version manager for handling version compatibility and migrations.
    
    Manages API versions, compatibility checking, and automatic migrations
    between different API versions.
    """
    
    def __init__(self):
        self._versions: Dict[str, APIVersion] = {}
        self._compatibility_matrix: Dict[str, Dict[str, VersionCompatibility]] = {}
        self._migrations: Dict[str, Dict[str, VersionMigration]] = {}
        self._default_version = "v1"
        self._supported_versions: Set[str] = set()
        
        # Version routing rules
        self._version_routes: Dict[str, Dict[str, str]] = {}  # version -> path -> handler_version
        
        # Setup default versions
        self._setup_default_versions()
    
    def _setup_default_versions(self):
        """Setup default API versions"""
        # Register v1 as default
        v1 = APIVersion(
            version="v1",
            format=VersionFormat.SIMPLE,
            description="Initial API version",
            features=["Basic CRUD operations", "Search and filtering"]
        )
        self.register_version(v1)
        self._default_version = "v1"
        self._supported_versions.add("v1")
    
    def register_version(self, version: APIVersion) -> bool:
        """
        Register a new API version.
        
        Args:
            version: API version information
            
        Returns:
            True if registration successful
        """
        try:
            version_key = version.version
            
            if version_key in self._versions:
                logger.warning(f"Version {version_key} already registered")
                return False
            
            self._versions[version_key] = version
            
            if version.is_active:
                self._supported_versions.add(version_key)
            
            # Initialize compatibility matrix for this version
            if version_key not in self._compatibility_matrix:
                self._compatibility_matrix[version_key] = {}
            
            # Initialize migration mappings
            if version_key not in self._migrations:
                self._migrations[version_key] = {}
            
            logger.info(f"Registered API version: {version_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register version {version.version}: {e}")
            return False
    
    def get_version(self, version: str) -> Optional[APIVersion]:
        """Get version information"""
        return self._versions.get(version)
    
    def list_versions(self, active_only: bool = False) -> List[APIVersion]:
        """
        List all registered versions.
        
        Args:
            active_only: Only return active versions
            
        Returns:
            List of API versions
        """
        versions = list(self._versions.values())
        
        if active_only:
            versions = [v for v in versions if v.is_active]
        
        # Sort by version (descending)
        return sorted(versions, key=lambda v: self._version_sort_key(v.version), reverse=True)
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported version strings"""
        return sorted(list(self._supported_versions))
    
    def set_default_version(self, version: str) -> bool:
        """
        Set default API version.
        
        Args:
            version: Version string
            
        Returns:
            True if set successfully
        """
        if version not in self._versions:
            logger.error(f"Version {version} not registered")
            return False
        
        self._default_version = version
        logger.info(f"Set default version to: {version}")
        return True
    
    def get_default_version(self) -> str:
        """Get default API version"""
        return self._default_version
    
    def extract_version_from_request(self, request: APIRequest) -> str:
        """
        Extract API version from request.
        
        Args:
            request: API request
            
        Returns:
            Version string
        """
        # Check explicit version in request
        if request.version and request.version in self._supported_versions:
            return request.version
        
        # Check version in URL path
        version_from_path = self._extract_version_from_path(request.path)
        if version_from_path and version_from_path in self._supported_versions:
            return version_from_path
        
        # Check version in headers
        version_header = request.headers.get('API-Version')
        if version_header and version_header in self._supported_versions:
            return version_header
        
        # Check version in query parameters
        version_param = request.query_params.get('version')
        if version_param and version_param in self._supported_versions:
            return version_param
        
        # Return default version
        return self._default_version
    
    def _extract_version_from_path(self, path: str) -> Optional[str]:
        """Extract version from URL path"""
        # Match patterns like /api/v1/... or /v2/...
        match = re.search(r'/v(\d+(?:\.\d+(?:\.\d+)?)?)', path)
        if match:
            return f"v{match.group(1)}"
        return None
    
    def is_version_supported(self, version: str) -> bool:
        """Check if version is supported"""
        return version in self._supported_versions
    
    def deprecate_version(self, version: str, deprecation_date: Optional[datetime] = None, 
                         end_of_life_date: Optional[datetime] = None) -> bool:
        """
        Deprecate an API version.
        
        Args:
            version: Version to deprecate
            deprecation_date: When version was deprecated
            end_of_life_date: When version will be removed
            
        Returns:
            True if deprecation successful
        """
        if version not in self._versions:
            logger.error(f"Version {version} not found")
            return False
        
        version_info = self._versions[version]
        version_info.is_deprecated = True
        version_info.deprecation_date = deprecation_date or datetime.utcnow()
        
        if end_of_life_date:
            version_info.end_of_life_date = end_of_life_date
        
        logger.info(f"Deprecated version: {version}")
        return True
    
    def register_compatibility(self, compatibility: VersionCompatibility) -> bool:
        """
        Register version compatibility information.
        
        Args:
            compatibility: Compatibility information
            
        Returns:
            True if registration successful
        """
        try:
            source = compatibility.source_version
            target = compatibility.target_version
            
            if source not in self._versions or target not in self._versions:
                logger.error(f"Source or target version not registered: {source} -> {target}")
                return False
            
            if source not in self._compatibility_matrix:
                self._compatibility_matrix[source] = {}
            
            self._compatibility_matrix[source][target] = compatibility
            logger.info(f"Registered compatibility: {source} -> {target}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register compatibility: {e}")
            return False
    
    def check_compatibility(self, source_version: str, target_version: str) -> Optional[VersionCompatibility]:
        """
        Check compatibility between two versions.
        
        Args:
            source_version: Source version
            target_version: Target version
            
        Returns:
            Compatibility information or None if not found
        """
        if source_version == target_version:
            return VersionCompatibility(
                source_version=source_version,
                target_version=target_version,
                compatibility_level=CompatibilityLevel.FULLY_COMPATIBLE
            )
        
        return self._compatibility_matrix.get(source_version, {}).get(target_version)
    
    def register_migration(self, migration: VersionMigration) -> bool:
        """
        Register a version migration.
        
        Args:
            migration: Migration implementation
            
        Returns:
            True if registration successful
        """
        try:
            source = migration.get_source_version()
            target = migration.get_target_version()
            
            if source not in self._versions or target not in self._versions:
                logger.error(f"Source or target version not registered: {source} -> {target}")
                return False
            
            if source not in self._migrations:
                self._migrations[source] = {}
            
            self._migrations[source][target] = migration
            logger.info(f"Registered migration: {source} -> {target}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register migration: {e}")
            return False
    
    async def migrate_request(self, request: APIRequest, target_version: str) -> APIRequest:
        """
        Migrate request to target version.
        
        Args:
            request: Original request
            target_version: Target version
            
        Returns:
            Migrated request
        """
        source_version = self.extract_version_from_request(request)
        
        if source_version == target_version:
            return request
        
        # Find migration path
        migration_path = self._find_migration_path(source_version, target_version)
        if not migration_path:
            logger.warning(f"No migration path found: {source_version} -> {target_version}")
            return request
        
        # Apply migrations in sequence
        current_request = request
        for i in range(len(migration_path) - 1):
            from_version = migration_path[i]
            to_version = migration_path[i + 1]
            
            migration = self._migrations.get(from_version, {}).get(to_version)
            if migration:
                current_request = await migration.migrate_request(current_request)
                current_request.version = to_version
        
        return current_request
    
    async def migrate_response(self, response: APIResponse, target_version: str) -> APIResponse:
        """
        Migrate response to target version.
        
        Args:
            response: Original response
            target_version: Target version
            
        Returns:
            Migrated response
        """
        source_version = response.version
        
        if source_version == target_version:
            return response
        
        # Find reverse migration path
        migration_path = self._find_migration_path(source_version, target_version)
        if not migration_path:
            logger.warning(f"No migration path found: {source_version} -> {target_version}")
            return response
        
        # Apply reverse migrations
        current_response = response
        for i in range(len(migration_path) - 1, 0, -1):
            from_version = migration_path[i]
            to_version = migration_path[i - 1]
            
            migration = self._migrations.get(to_version, {}).get(from_version)
            if migration:
                current_response = await migration.migrate_response(current_response)
                current_response.version = to_version
        
        return current_response
    
    def _find_migration_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find migration path between versions using BFS"""
        if source == target:
            return [source]
        
        from collections import deque
        
        queue = deque([(source, [source])])
        visited = {source}
        
        while queue:
            current_version, path = queue.popleft()
            
            # Check all possible migrations from current version
            for next_version in self._migrations.get(current_version, {}):
                if next_version == target:
                    return path + [next_version]
                
                if next_version not in visited:
                    visited.add(next_version)
                    queue.append((next_version, path + [next_version]))
        
        return None
    
    def _version_sort_key(self, version: str) -> tuple:
        """Generate sort key for version string"""
        version_clean = version.lstrip('v')
        
        # Handle semantic versions
        if '.' in version_clean:
            parts = version_clean.split('.')
            return tuple(int(p) for p in parts)
        
        # Handle simple versions
        try:
            return (int(version_clean), 0, 0)
        except ValueError:
            return (0, 0, 0)
    
    def get_version_stats(self) -> Dict[str, Any]:
        """Get version manager statistics"""
        active_versions = [v for v in self._versions.values() if v.is_active]
        deprecated_versions = [v for v in self._versions.values() if v.is_deprecated]
        
        return {
            "total_versions": len(self._versions),
            "active_versions": len(active_versions),
            "deprecated_versions": len(deprecated_versions),
            "supported_versions": len(self._supported_versions),
            "default_version": self._default_version,
            "latest_version": self.list_versions(active_only=True)[0].version if active_versions else None,
            "total_compatibility_rules": sum(len(compat) for compat in self._compatibility_matrix.values()),
            "total_migrations": sum(len(migrations) for migrations in self._migrations.values())
        }


# Example migration implementations
class V1ToV2Migration(VersionMigration):
    """Example migration from v1 to v2"""
    
    def get_source_version(self) -> str:
        return "v1"
    
    def get_target_version(self) -> str:
        return "v2"
    
    async def migrate_request(self, request: APIRequest) -> APIRequest:
        """Migrate v1 request to v2 format"""
        # Example: Add new required fields, rename fields, etc.
        if request.body and isinstance(request.body, dict):
            # Add default values for new fields
            if 'metadata' not in request.body:
                request.body['metadata'] = {}
        
        return request
    
    async def migrate_response(self, response: APIResponse) -> APIResponse:
        """Migrate v2 response back to v1 format"""
        # Example: Remove new fields, rename fields back, etc.
        if response.data and isinstance(response.data, dict):
            # Remove fields that don't exist in v1
            if 'metadata' in response.data:
                del response.data['metadata']
        
        return response


# Global version manager instance
_version_manager: Optional[APIVersionManager] = None


def get_version_manager() -> APIVersionManager:
    """Get the global version manager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = APIVersionManager()
    return _version_manager


def setup_version_manager() -> APIVersionManager:
    """Setup and return the global version manager with default configurations"""
    global _version_manager
    _version_manager = APIVersionManager()
    
    # Register v2 version
    v2 = APIVersion(
        version="v2",
        format=VersionFormat.SIMPLE,
        description="Enhanced API with metadata support",
        features=["Metadata fields", "Enhanced filtering", "Improved error handling"],
        changelog=["Added metadata support", "Enhanced search capabilities"]
    )
    _version_manager.register_version(v2)
    
    # Register compatibility
    v1_to_v2_compat = VersionCompatibility(
        source_version="v1",
        target_version="v2",
        compatibility_level=CompatibilityLevel.BACKWARD_COMPATIBLE,
        migration_required=False,
        warnings=["Some new features not available in v1"]
    )
    _version_manager.register_compatibility(v1_to_v2_compat)
    
    # Register migration
    v1_to_v2_migration = V1ToV2Migration()
    _version_manager.register_migration(v1_to_v2_migration)
    
    return _version_manager