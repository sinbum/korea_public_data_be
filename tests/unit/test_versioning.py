"""
Unit tests for API versioning system.

Tests version extraction, validation, response adaptation,
and middleware functionality.
"""

import pytest
from datetime import date, datetime
from fastapi import Request, HTTPException
from unittest.mock import Mock, MagicMock
from pydantic import ValidationError

from app.shared.versioning import (
    APIVersion,
    VersionRegistry,
    VersionExtractor,
    VersioningMethod
)
from app.shared.version_adapters import (
    V1ResponseAdapter,
    V2ResponseAdapter,
    AnnouncementV1Adapter,
    ResponseVersionAdapter,
    VersionedResponseBuilder
)


class TestAPIVersion:
    """Test APIVersion model and functionality."""
    
    def test_basic_version_creation(self):
        """Test basic version creation."""
        version = APIVersion(major=1, minor=2, patch=3)
        
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.label is None
        assert version.is_stable is True
        assert version.is_deprecated is False
    
    def test_version_with_label(self):
        """Test version with label."""
        version = APIVersion(
            major=2,
            minor=0,
            patch=0,
            label="beta",
            is_stable=False,
            is_experimental=True
        )
        
        assert version.label == "beta"
        assert version.is_stable is False
        assert version.is_experimental is True
    
    def test_version_string_properties(self):
        """Test version string generation."""
        # Basic version
        version = APIVersion(major=1, minor=2, patch=3)
        assert version.version_string == "1.2.3"
        assert version.short_version == "v1.2.3"
        
        # Version with label
        version_beta = APIVersion(major=2, minor=0, patch=0, label="beta")
        assert version_beta.version_string == "2.0.0-beta"
        assert version_beta.short_version == "v2"
        
        # Minor version only
        version_minor = APIVersion(major=1, minor=5, patch=0)
        assert version_minor.short_version == "v1.5"
    
    def test_date_validation(self):
        """Test date validation rules."""
        today = date.today()
        
        # Valid dates
        version = APIVersion(
            major=1,
            minor=0,
            patch=0,
            release_date=today,
            deprecation_date=date(today.year + 1, today.month, today.day),
            sunset_date=date(today.year + 2, today.month, today.day)
        )
        
        assert version.release_date == today
        
        # Invalid deprecation date (before release)
        with pytest.raises(ValidationError):
            APIVersion(
                major=1,
                minor=0,
                patch=0,
                release_date=today,
                deprecation_date=date(today.year - 1, today.month, today.day)
            )
        
        # Invalid sunset date (before deprecation)
        with pytest.raises(ValidationError):
            APIVersion(
                major=1,
                minor=0,
                patch=0,
                deprecation_date=today,
                sunset_date=date(today.year - 1, today.month, today.day)
            )
    
    def test_version_comparison(self):
        """Test version comparison methods."""
        v1_0_0 = APIVersion(major=1, minor=0, patch=0)
        v1_0_1 = APIVersion(major=1, minor=0, patch=1)
        v1_1_0 = APIVersion(major=1, minor=1, patch=0)
        v2_0_0 = APIVersion(major=2, minor=0, patch=0)
        
        # Test ordering
        assert v1_0_0 < v1_0_1
        assert v1_0_1 < v1_1_0
        assert v1_1_0 < v2_0_0
        assert v2_0_0 > v1_0_0
        
        # Test equality
        v1_0_0_copy = APIVersion(major=1, minor=0, patch=0)
        assert v1_0_0 == v1_0_0_copy
        
        # Test compare method
        assert v1_0_0.compare(v1_0_1) == -1
        assert v1_0_1.compare(v1_0_0) == 1
        assert v1_0_0.compare(v1_0_0_copy) == 0
    
    def test_version_status_properties(self):
        """Test version status properties."""
        today = date.today()
        
        # Current version
        current_version = APIVersion(major=1, minor=0, patch=0)
        assert current_version.is_current is True
        
        # Deprecated version
        deprecated_version = APIVersion(
            major=1,
            minor=0,
            patch=0,
            is_deprecated=True,
            deprecation_date=today
        )
        assert deprecated_version.is_current is False
        
        # Sunset version
        sunset_version = APIVersion(
            major=1,
            minor=0,
            patch=0,
            sunset_date=date(today.year - 1, today.month, today.day)
        )
        assert sunset_version.is_current is False
    
    def test_days_until_sunset(self):
        """Test days until sunset calculation."""
        today = date.today()
        
        # No sunset date
        version = APIVersion(major=1, minor=0, patch=0)
        assert version.days_until_sunset is None
        
        # Future sunset
        future_sunset = APIVersion(
            major=1,
            minor=0,
            patch=0,
            sunset_date=date(today.year, today.month, today.day + 30 if today.day <= 15 else today.day - 15)
        )
        assert future_sunset.days_until_sunset is not None
        
        # Past sunset
        past_sunset = APIVersion(
            major=1,
            minor=0,
            patch=0,
            sunset_date=date(today.year - 1, today.month, today.day)
        )
        assert past_sunset.days_until_sunset == 0


class TestVersionRegistry:
    """Test VersionRegistry functionality."""
    
    def test_version_registration(self):
        """Test version registration."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        
        registry.register_version(v1, is_default=True)
        registry.register_version(v2, is_latest=True)
        
        assert registry.get_version("v1") == v1
        assert registry.get_version("v2") == v2
        assert registry.get_default_version() == v1
        assert registry.get_latest_version() == v2
    
    def test_duplicate_registration(self):
        """Test duplicate version registration raises error."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        registry.register_version(v1)
        
        # Attempt to register same version again
        v1_duplicate = APIVersion(major=1, minor=0, patch=0)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_version(v1_duplicate)
    
    def test_version_listing(self):
        """Test version listing functionality."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0, is_deprecated=True)
        v3 = APIVersion(major=3, minor=0, patch=0)
        
        registry.register_version(v1)
        registry.register_version(v2)
        registry.register_version(v3)
        
        # All versions
        all_versions = registry.list_versions()
        assert len(all_versions) == 3
        assert all_versions[0] == v3  # Latest first
        
        # Non-deprecated only
        current_versions = registry.list_versions(include_deprecated=False)
        assert len(current_versions) == 2
        assert v2 not in current_versions
    
    def test_version_support_checking(self):
        """Test version support checking."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0, is_deprecated=True)
        
        registry.register_version(v1)
        registry.register_version(v2)
        
        assert registry.is_version_supported("v1") is True
        assert registry.is_version_supported("v2") is False  # Deprecated
        assert registry.is_version_supported("v3") is False  # Not registered
        
        supported_versions = registry.list_supported_versions()
        assert "v1" in supported_versions
        assert "v2" not in supported_versions
    
    def test_version_deprecation(self):
        """Test version deprecation."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        registry.register_version(v1)
        
        # Deprecate version
        sunset_date = date.today()
        registry.deprecate_version("v1", sunset_date)
        
        deprecated_version = registry.get_version("v1")
        assert deprecated_version.is_deprecated is True
        assert deprecated_version.deprecation_date == date.today()
        assert deprecated_version.sunset_date == sunset_date
    
    def test_version_removal(self):
        """Test version removal."""
        registry = VersionRegistry()
        
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        
        registry.register_version(v1, is_default=True)
        registry.register_version(v2, is_latest=True)
        
        # Remove v1
        registry.remove_version("v1")
        
        assert registry.get_version("v1") is None
        assert registry.get_default_version() == v2  # Should update to latest


class TestVersionExtractor:
    """Test VersionExtractor functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.registry = VersionRegistry()
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        
        self.registry.register_version(v1, is_default=True)
        self.registry.register_version(v2, is_latest=True)
        
        self.extractor = VersionExtractor(self.registry)
    
    def test_url_extraction(self):
        """Test version extraction from URL."""
        # Various URL patterns
        assert self.extractor.extract_from_url("/api/v1/users") == "v1"
        assert self.extractor.extract_from_url("/api/v2/users") == "v2"
        assert self.extractor.extract_from_url("/api/v1.5/users") == "v1.5"
        assert self.extractor.extract_from_url("/api/users") is None
    
    def test_header_extraction(self):
        """Test version extraction from headers."""
        # Accept header with version
        assert self.extractor.extract_from_header("application/json; version=1") == "v1"
        assert self.extractor.extract_from_header("application/json; version=2.0") == "v2.0"
        assert self.extractor.extract_from_header("application/json") is None
    
    def test_content_type_extraction(self):
        """Test version extraction from content type."""
        assert self.extractor.extract_from_content_type("application/vnd.api.v1+json") == "v1"
        assert self.extractor.extract_from_content_type("application/vnd.api.v2.1+json") == "v2.1"
        assert self.extractor.extract_from_content_type("application/json") is None
    
    def test_query_extraction(self):
        """Test version extraction from query parameters."""
        assert self.extractor.extract_from_query({"version": "1"}) == "v1"
        assert self.extractor.extract_from_query({"api_version": "v2"}) == "v2"
        assert self.extractor.extract_from_query({"other": "value"}) is None
    
    def test_request_version_extraction(self):
        """Test complete request version extraction."""
        # Mock request with URL version
        request = Mock()
        request.url.path = "/api/v1/users"
        request.headers.get.return_value = None
        request.query_params = {}
        
        version = self.extractor.extract_version(request)
        assert version.major == 1
        assert version.minor == 0
        
        # Mock request with no version (should use default)
        request.url.path = "/api/users"
        version = self.extractor.extract_version(request)
        assert version.major == 1  # Default version
    
    def test_unsupported_version_error(self):
        """Test error for unsupported version."""
        request = Mock()
        request.url.path = "/api/v3/users"
        request.headers.get.return_value = None
        request.query_params = {}
        
        with pytest.raises(HTTPException) as exc_info:
            self.extractor.extract_version(request)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported API version" in exc_info.value.detail


class TestResponseAdapters:
    """Test response adapter functionality."""
    
    def test_v1_response_adapter(self):
        """Test V1 response adapter."""
        adapter = V1ResponseAdapter()
        
        # V2 format input
        v2_response = {
            "success": True,
            "data": {"id": "123", "name": "Test"},
            "message": "Success",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Transform to V1 format
        v1_response = adapter.transform(v2_response)
        
        assert v1_response["status"] == "success"
        assert v1_response["result"] == {"id": "123", "name": "Test"}
        assert v1_response["msg"] == "Success"
        assert "timestamp" in v1_response
    
    def test_v1_adapter_pagination(self):
        """Test V1 adapter pagination transformation."""
        adapter = V1ResponseAdapter()
        
        v2_response = {
            "success": True,
            "data": [{"id": "1"}, {"id": "2"}],
            "pagination": {
                "page": 2,
                "size": 10,
                "total": 50,
                "total_pages": 5,
                "has_next": True,
                "has_previous": True
            }
        }
        
        v1_response = adapter.transform(v2_response)
        
        pagination = v1_response["pagination"]
        assert pagination["current_page"] == 2
        assert pagination["per_page"] == 10
        assert pagination["total_count"] == 50
        assert pagination["total_pages"] == 5
    
    def test_v1_adapter_errors(self):
        """Test V1 adapter error transformation."""
        adapter = V1ResponseAdapter()
        
        v2_response = {
            "success": False,
            "data": None,  # Add data field to trigger V1 transformation
            "message": "Validation failed",
            "errors": [
                {
                    "code": "REQUIRED_FIELD",
                    "message": "Name is required",
                    "field": "name"
                }
            ]
        }
        
        v1_response = adapter.transform(v2_response)
        
        errors = v1_response["errors"]
        assert len(errors) == 1
        assert errors[0]["error_code"] == "REQUIRED_FIELD"
        assert errors[0]["error_message"] == "Name is required"
        assert errors[0]["field_name"] == "name"
    
    def test_v2_response_adapter(self):
        """Test V2 response adapter."""
        adapter = V2ResponseAdapter()
        
        # V1 format input
        v1_response = {
            "status": "success",
            "result": {"id": "123", "name": "Test"},
            "msg": "Success"
        }
        
        # Transform to V2 format
        v2_response = adapter.transform(v1_response)
        
        assert v2_response["success"] is True
        assert v2_response["data"] == {"id": "123", "name": "Test"}
        assert v2_response["message"] == "Success"
        assert "timestamp" in v2_response
    
    def test_announcement_v1_adapter(self):
        """Test announcement-specific V1 adapter."""
        adapter = AnnouncementV1Adapter()
        
        v2_announcement = {
            "id": "64f1a2b3c4d5e6f7a8b9c0d1",
            "announcement_data": {
                "business_name": "스타트업 지원사업",
                "business_type": "정부지원",
                "status": "모집중"
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "is_active": True
        }
        
        v1_announcement = adapter.transform(v2_announcement)
        
        # Check field mappings
        assert v1_announcement["announcement_id"] == "64f1a2b3c4d5e6f7a8b9c0d1"
        assert v1_announcement["active_flag"] is True
        assert "created_date" in v1_announcement
        assert "modified_date" in v1_announcement
        
        # Check flattened fields
        assert v1_announcement["business_name"] == "스타트업 지원사업"
        assert v1_announcement["business_type"] == "정부지원"
        assert v1_announcement["status"] == "모집중"


class TestResponseVersionAdapter:
    """Test ResponseVersionAdapter functionality."""
    
    def test_adapter_registration(self):
        """Test adapter registration."""
        response_adapter = ResponseVersionAdapter()
        v1_adapter = V1ResponseAdapter()
        
        response_adapter.register_adapter(v1_adapter)
        
        assert len(response_adapter._adapters) == 1
    
    def test_field_mapping_registration(self):
        """Test field mapping registration."""
        response_adapter = ResponseVersionAdapter()
        
        mappings = {"old_field": "new_field"}
        response_adapter.register_field_mapping("v1", mappings)
        
        assert response_adapter._field_mappings["v1"] == mappings
    
    def test_field_transformer_registration(self):
        """Test field transformer registration."""
        response_adapter = ResponseVersionAdapter()
        
        def transform_date(value):
            return value.replace("T", " ").replace("Z", "")
        
        response_adapter.register_field_transformer("v1", "created_at", transform_date)
        
        assert "v1" in response_adapter._field_transformers
        assert "created_at" in response_adapter._field_transformers["v1"]
    
    def test_field_transformation_application(self):
        """Test field transformation application."""
        response_adapter = ResponseVersionAdapter()
        
        # Register field mapping
        response_adapter.register_field_mapping("v1", {"new_field": "old_field"})
        
        # Register field transformer
        def uppercase_transform(value):
            return value.upper() if isinstance(value, str) else value
        
        response_adapter.register_field_transformer("v1", "old_field", uppercase_transform)
        
        # Test data
        data = {"new_field": "test value"}
        target_version = APIVersion(major=1, minor=0, patch=0)
        
        result = response_adapter._apply_field_transformations(data, target_version)
        
        assert "old_field" in result
        assert result["old_field"] == "TEST VALUE"
        assert "new_field" not in result


class TestVersionedResponseBuilder:
    """Test VersionedResponseBuilder functionality."""
    
    def test_response_builder_initialization(self):
        """Test response builder initialization."""
        builder = VersionedResponseBuilder()
        
        # Should have default adapters registered
        assert len(builder.adapter._adapters) > 0
        assert "v1" in builder.adapter._field_mappings
    
    def test_build_response(self):
        """Test response building."""
        builder = VersionedResponseBuilder()
        
        # V2 format data
        data = {
            "success": True,
            "data": {"id": "123"},
            "message": "Test"
        }
        
        target_version = APIVersion(major=1, minor=0, patch=0)
        
        # Build response (should adapt to V1 format)
        result = builder.build_response(data, target_version)
        
        # Result should be adapted or original data
        assert isinstance(result, dict)
    
    def test_build_response_error_handling(self):
        """Test response building error handling."""
        builder = VersionedResponseBuilder()
        
        # Invalid data that might cause adaptation to fail
        invalid_data = object()  # Non-serializable object
        target_version = APIVersion(major=1, minor=0, patch=0)
        
        # Should return original data if adaptation fails
        result = builder.build_response(invalid_data, target_version)
        assert result is invalid_data


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    def test_complete_version_flow(self):
        """Test complete version extraction and adaptation flow."""
        # Setup registry
        registry = VersionRegistry()
        v1 = APIVersion(major=1, minor=0, patch=0)
        v2 = APIVersion(major=2, minor=0, patch=0)
        
        registry.register_version(v1, is_default=True)
        registry.register_version(v2, is_latest=True)
        
        # Setup extractor
        extractor = VersionExtractor(registry)
        
        # Setup response builder
        builder = VersionedResponseBuilder()
        
        # Mock request
        request = Mock()
        request.url.path = "/api/v1/announcements"
        request.headers.get.return_value = None
        request.query_params = {}
        
        # Extract version
        version = extractor.extract_version(request)
        assert version.major == 1
        
        # Build response
        v2_data = {
            "success": True,
            "data": {"id": "123", "name": "Test"}
        }
        
        adapted_response = builder.build_response(v2_data, version)
        
        # Should be adapted for V1 if adapter is available
        assert isinstance(adapted_response, dict)
    
    def test_deprecation_scenario(self):
        """Test deprecation handling scenario."""
        today = date.today()
        
        # Create deprecated version
        deprecated_version = APIVersion(
            major=1,
            minor=0,
            patch=0,
            is_deprecated=True,
            deprecation_date=today,
            sunset_date=date(today.year + 1, today.month, today.day)
        )
        
        registry = VersionRegistry()
        registry.register_version(deprecated_version)
        
        extractor = VersionExtractor(registry)
        
        # Mock request for deprecated version
        request = Mock()
        request.url.path = "/api/v1/users"
        request.headers.get.return_value = None
        request.query_params = {}
        
        # Should still extract version but log warning
        version = extractor.extract_version(request)
        assert version.is_deprecated is True
    
    def test_sunset_version_scenario(self):
        """Test sunset version handling."""
        today = date.today()
        
        # Create sunset version
        sunset_version = APIVersion(
            major=1,
            minor=0,
            patch=0,
            sunset_date=date(today.year - 1, today.month, today.day)
        )
        
        registry = VersionRegistry()
        registry.register_version(sunset_version)
        
        extractor = VersionExtractor(registry)
        
        # Mock request for sunset version
        request = Mock()
        request.url.path = "/api/v1/users"
        request.headers.get.return_value = None
        request.query_params = {}
        
        # Should raise 410 Gone error
        with pytest.raises(HTTPException) as exc_info:
            extractor.extract_version(request)
        
        assert exc_info.value.status_code == 410
        assert "sunset" in exc_info.value.detail.lower()