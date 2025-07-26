"""
Version-specific response adapters and transformers.

Handles backward compatibility and response format transformation
between different API versions.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, Callable
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime
import logging

from .versioning import APIVersion
from .responses import BaseResponse

logger = logging.getLogger(__name__)

# Type variables for generic adapters
TSource = TypeVar('TSource', bound=BaseModel)
TTarget = TypeVar('TTarget', bound=BaseModel)


class VersionAdapter(ABC, Generic[TSource, TTarget]):
    """Abstract base class for version-specific adapters."""
    
    def __init__(self, source_version: APIVersion, target_version: APIVersion):
        self.source_version = source_version
        self.target_version = target_version
    
    @abstractmethod
    def transform(self, data: TSource) -> TTarget:
        """Transform data from source version to target version."""
        pass
    
    @abstractmethod
    def can_transform(self, from_version: APIVersion, to_version: APIVersion) -> bool:
        """Check if this adapter can handle the version transformation."""
        pass


class ResponseVersionAdapter:
    """Adapts responses between different API versions."""
    
    def __init__(self):
        self._adapters: List[VersionAdapter] = []
        self._field_mappings: Dict[str, Dict[str, str]] = {}
        self._field_transformers: Dict[str, Dict[str, Callable]] = {}
    
    def register_adapter(self, adapter: VersionAdapter) -> None:
        """Register a version adapter."""
        self._adapters.append(adapter)
        logger.debug(f"Registered adapter: {adapter.source_version.short_version} -> {adapter.target_version.short_version}")
    
    def register_field_mapping(
        self,
        version: str,
        field_mappings: Dict[str, str]
    ) -> None:
        """
        Register field name mappings for a version.
        
        Args:
            version: Version key (e.g., 'v1')
            field_mappings: Dict mapping old field names to new field names
        """
        self._field_mappings[version] = field_mappings
    
    def register_field_transformer(
        self,
        version: str,
        field: str,
        transformer: Callable[[Any], Any]
    ) -> None:
        """
        Register a field value transformer for a specific version.
        
        Args:
            version: Version key (e.g., 'v1')
            field: Field name to transform
            transformer: Function to transform field value
        """
        if version not in self._field_transformers:
            self._field_transformers[version] = {}
        self._field_transformers[version][field] = transformer
    
    def adapt_response(
        self,
        data: Any,
        target_version: APIVersion,
        source_version: Optional[APIVersion] = None
    ) -> Any:
        """
        Adapt response data to target version format.
        
        Args:
            data: Source data to transform
            target_version: Target API version
            source_version: Source API version (latest if not specified)
            
        Returns:
            Transformed data compatible with target version
        """
        if source_version and source_version == target_version:
            return data
        
        # Try registered adapters first
        for adapter in self._adapters:
            if adapter.can_transform(source_version, target_version):
                try:
                    return adapter.transform(data)
                except Exception as e:
                    logger.error(f"Adapter transformation failed: {e}")
                    continue
        
        # Fall back to generic field mapping and transformation
        return self._apply_field_transformations(data, target_version)
    
    def _apply_field_transformations(self, data: Any, target_version: APIVersion) -> Any:
        """Apply field mappings and transformations for a version."""
        if not isinstance(data, dict):
            return data
        
        version_key = target_version.short_version
        result = data.copy()
        
        # Apply field mappings
        if version_key in self._field_mappings:
            mappings = self._field_mappings[version_key]
            for old_field, new_field in mappings.items():
                if old_field in result:
                    result[new_field] = result.pop(old_field)
        
        # Apply field transformers
        if version_key in self._field_transformers:
            transformers = self._field_transformers[version_key]
            for field, transformer in transformers.items():
                if field in result:
                    try:
                        result[field] = transformer(result[field])
                    except Exception as e:
                        logger.warning(f"Field transformation failed for {field}: {e}")
        
        return result


class V1ResponseAdapter(VersionAdapter[Dict[str, Any], Dict[str, Any]]):
    """Adapter for V1 API responses."""
    
    def __init__(self):
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        super().__init__(source_version=v2, target_version=v1)
    
    def can_transform(self, from_version: APIVersion, to_version: APIVersion) -> bool:
        """Check if this adapter can handle the transformation."""
        return (to_version.major == 1 and from_version.major >= 2)
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform V2+ response to V1 format."""
        if not isinstance(data, dict):
            return data
        
        result = {}
        
        # V1 had different response structure
        if 'success' in data and 'data' in data:
            # V2 format: {"success": bool, "data": {...}, "message": str, ...}
            # V1 format: {"status": str, "result": {...}, "msg": str}
            result = {
                'status': 'success' if data.get('success') else 'error',
                'result': data.get('data'),
                'msg': data.get('message', ''),
                'timestamp': data.get('timestamp')
            }
            
            # Handle pagination differently in V1
            if 'pagination' in data:
                pagination = data['pagination']
                result['pagination'] = {
                    'current_page': pagination.get('page', 1),
                    'per_page': pagination.get('size', 20),
                    'total_count': pagination.get('total', 0),
                    'total_pages': pagination.get('total_pages', 1)
                }
            
            # Handle errors differently in V1
            if 'errors' in data:
                result['errors'] = [
                    {
                        'error_code': error.get('code'),
                        'error_message': error.get('message'),
                        'field_name': error.get('field')
                    }
                    for error in data['errors']
                ]
        else:
            result = data
        
        return result


class V2ResponseAdapter(VersionAdapter[Dict[str, Any], Dict[str, Any]]):
    """Adapter for V2 API responses."""
    
    def __init__(self):
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        super().__init__(source_version=v1, target_version=v2)
    
    def can_transform(self, from_version: APIVersion, to_version: APIVersion) -> bool:
        """Check if this adapter can handle the transformation."""
        return (from_version.major == 1 and to_version.major >= 2)
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform V1 response to V2+ format."""
        if not isinstance(data, dict):
            return data
        
        result = {}
        
        # V1 format: {"status": str, "result": {...}, "msg": str}
        # V2 format: {"success": bool, "data": {...}, "message": str, ...}
        if 'status' in data:
            result = {
                'success': data.get('status') == 'success',
                'data': data.get('result'),
                'message': data.get('msg', ''),
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                'status': 'success' if data.get('status') == 'success' else 'error'
            }
            
            # Handle pagination conversion
            if 'pagination' in data:
                pagination = data['pagination']
                result['pagination'] = {
                    'page': pagination.get('current_page', 1),
                    'size': pagination.get('per_page', 20),
                    'total': pagination.get('total_count', 0),
                    'total_pages': pagination.get('total_pages', 1),
                    'has_next': pagination.get('current_page', 1) < pagination.get('total_pages', 1),
                    'has_previous': pagination.get('current_page', 1) > 1
                }
            
            # Handle error format conversion
            if 'errors' in data:
                result['errors'] = [
                    {
                        'code': error.get('error_code'),
                        'message': error.get('error_message'),
                        'field': error.get('field_name'),
                        'context': {}
                    }
                    for error in data['errors']
                ]
        else:
            result = data
        
        return result


class AnnouncementV1Adapter(VersionAdapter[Dict[str, Any], Dict[str, Any]]):
    """Adapter for Announcement responses in V1."""
    
    def __init__(self):
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        super().__init__(source_version=v2, target_version=v1)
    
    def can_transform(self, from_version: APIVersion, to_version: APIVersion) -> bool:
        """Check if this adapter can handle the transformation."""
        return to_version.major == 1 and from_version.major >= 2
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform announcement data to V1 format."""
        if not isinstance(data, dict):
            return data
        
        # V1 announcement format differences
        result = data.copy()
        
        # V1 used different field names
        field_mappings = {
            'id': 'announcement_id',
            'created_at': 'created_date',
            'updated_at': 'modified_date',
            'is_active': 'active_flag'
        }
        
        for old_field, new_field in field_mappings.items():
            if old_field in result:
                result[new_field] = result.pop(old_field)
        
        # V1 had flattened announcement_data structure
        if 'announcement_data' in result:
            announcement_data = result['announcement_data']
            if isinstance(announcement_data, dict):
                # Flatten some fields to top level in V1
                for field in ['business_name', 'business_type', 'status']:
                    if field in announcement_data:
                        result[field] = announcement_data[field]
        
        # V1 datetime format was different
        for date_field in ['created_date', 'modified_date']:
            if date_field in result and result[date_field]:
                # Convert ISO format to V1 format
                try:
                    dt = datetime.fromisoformat(result[date_field].replace('Z', '+00:00'))
                    result[date_field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        return result


class VersionedResponseBuilder:
    """Builds version-appropriate responses."""
    
    def __init__(self):
        self.adapter = ResponseVersionAdapter()
        self._setup_default_adapters()
    
    def _setup_default_adapters(self):
        """Setup default adapters for common transformations."""
        # Register response format adapters
        self.adapter.register_adapter(V1ResponseAdapter())
        self.adapter.register_adapter(V2ResponseAdapter())
        self.adapter.register_adapter(AnnouncementV1Adapter())
        
        # Register field mappings for different versions
        v1_mappings = {
            'created_at': 'created_date',
            'updated_at': 'modified_date',
            'is_active': 'active_flag'
        }
        self.adapter.register_field_mapping('v1', v1_mappings)
        
        # Register field transformers
        def datetime_to_v1_format(dt_str: str) -> str:
            """Convert ISO datetime to V1 format."""
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return dt_str
        
        self.adapter.register_field_transformer('v1', 'created_date', datetime_to_v1_format)
        self.adapter.register_field_transformer('v1', 'modified_date', datetime_to_v1_format)
    
    def build_response(
        self,
        data: Any,
        target_version: APIVersion,
        response_type: Optional[str] = None
    ) -> Any:
        """
        Build version-appropriate response.
        
        Args:
            data: Response data
            target_version: Target API version
            response_type: Optional response type hint
            
        Returns:
            Version-adapted response
        """
        try:
            return self.adapter.adapt_response(data, target_version)
        except Exception as e:
            logger.error(f"Response adaptation failed: {e}")
            # Return original data if adaptation fails
            return data


# Utility functions for backward compatibility
def ensure_v1_compatibility(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure data is compatible with V1 API format."""
    adapter = AnnouncementV1Adapter()
    v1_version = APIVersion(major=1, minor=0, patch=0)
    v2_version = APIVersion(major=2, minor=0, patch=0)
    
    if adapter.can_transform(v2_version, v1_version):
        return adapter.transform(data)
    return data


def ensure_v2_compatibility(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure data is compatible with V2 API format."""
    adapter = V2ResponseAdapter()
    v1_version = APIVersion(major=1, minor=0, patch=0)
    v2_version = APIVersion(major=2, minor=0, patch=0)
    
    if adapter.can_transform(v1_version, v2_version):
        return adapter.transform(data)
    return data


# Global versioned response builder
_global_response_builder: Optional[VersionedResponseBuilder] = None


def get_versioned_response_builder() -> VersionedResponseBuilder:
    """Get the global versioned response builder."""
    global _global_response_builder
    if _global_response_builder is None:
        _global_response_builder = VersionedResponseBuilder()
    return _global_response_builder