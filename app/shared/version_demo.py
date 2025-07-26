"""
API Versioning System Demonstration.

This module demonstrates how the API versioning system works with examples
of version extraction, response adaptation, and backward compatibility.
"""

from typing import Dict, Any
import json
from datetime import datetime

from .versioning import APIVersion, VersionRegistry, VersionExtractor
from .version_adapters import (
    V1ResponseAdapter,
    V2ResponseAdapter,
    AnnouncementV1Adapter,
    VersionedResponseBuilder
)


def demo_version_system():
    """Demonstrate the complete versioning system functionality."""
    
    print("=== API Versioning System Demonstration ===\n")
    
    # 1. Version Registry Demo
    print("1. Version Registry Setup:")
    registry = VersionRegistry()
    
    v1 = APIVersion(major=1, minor=0, patch=0)
    v1_5 = APIVersion(major=1, minor=5, patch=0)
    v2 = APIVersion(major=2, minor=0, patch=0, is_deprecated=False)
    v3 = APIVersion(major=3, minor=0, patch=0, is_experimental=True)
    
    registry.register_version(v1, is_default=True)
    registry.register_version(v1_5)
    registry.register_version(v2, is_latest=True)
    registry.register_version(v3)
    
    print(f"Registered versions: {registry.list_supported_versions()}")
    print(f"Default version: {registry.get_default_version().short_version}")
    print(f"Latest version: {registry.get_latest_version().short_version}")
    print()
    
    # 2. Version Extraction Demo
    print("2. Version Extraction Examples:")
    extractor = VersionExtractor(registry)
    
    # URL-based extraction
    url_examples = [
        "/api/v1/announcements",
        "/api/v2/businesses",
        "/api/v1.5/contents",
        "/api/announcements"  # No version - should use default
    ]
    
    for url in url_examples:
        version_str = extractor.extract_from_url(url)
        print(f"URL: {url:25} -> Version: {version_str or 'default'}")
    
    # Header-based extraction
    header_examples = [
        "application/json; version=1",
        "application/json; version=2.0",
        "application/vnd.api.v1+json",
        "application/json"
    ]
    
    print("\nHeader-based extraction:")
    for header in header_examples:
        version_str = extractor.extract_from_header(header) or extractor.extract_from_content_type(header)
        print(f"Header: {header:30} -> Version: {version_str or 'none'}")
    print()
    
    # 3. Response Adaptation Demo
    print("3. Response Adaptation Examples:")
    
    # Sample V2 response data
    v2_response = {
        "success": True,
        "data": {
            "id": "64f1a2b3c4d5e6f7a8b9c0d1",
            "announcement_data": {
                "business_name": "스타트업 지원사업",
                "business_type": "정부지원",
                "status": "모집중"
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "is_active": True
        },
        "message": "조회 성공",
        "timestamp": "2024-01-01T00:00:00Z",
        "pagination": {
            "page": 1,
            "size": 20,
            "total": 100,
            "total_pages": 5,
            "has_next": True,
            "has_previous": False
        }
    }
    
    print("Original V2 Response:")
    print(json.dumps(v2_response, indent=2, ensure_ascii=False))
    print()
    
    # Adapt to V1 format
    v1_adapter = V1ResponseAdapter()
    v1_response = v1_adapter.transform(v2_response)
    
    print("Adapted to V1 Format:")
    print(json.dumps(v1_response, indent=2, ensure_ascii=False))
    print()
    
    # 4. Announcement-specific adaptation
    print("4. Announcement-specific V1 Adaptation:")
    
    announcement_data = {
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
    
    announcement_adapter = AnnouncementV1Adapter()
    v1_announcement = announcement_adapter.transform(announcement_data)
    
    print("Original announcement data:")
    print(json.dumps(announcement_data, indent=2, ensure_ascii=False))
    print()
    
    print("Adapted to V1 announcement format:")
    print(json.dumps(v1_announcement, indent=2, ensure_ascii=False))
    print()
    
    # 5. Versioned Response Builder Demo
    print("5. Versioned Response Builder:")
    
    builder = VersionedResponseBuilder()
    
    # Test response building for different versions
    test_data = {
        "success": True,
        "data": {"id": "123", "name": "Test Item"},
        "message": "Success"
    }
    
    for version in [v1, v2]:
        adapted = builder.build_response(test_data, version)
        print(f"Response for {version.short_version}:")
        print(json.dumps(adapted, indent=2, ensure_ascii=False))
        print()
    
    # 6. Error Response Adaptation
    print("6. Error Response Adaptation:")
    
    v2_error = {
        "success": False,
        "data": None,
        "message": "Validation failed",
        "errors": [
            {
                "code": "REQUIRED_FIELD",
                "message": "Name is required",
                "field": "name"
            }
        ]
    }
    
    v1_error = v1_adapter.transform(v2_error)
    
    print("V2 Error Format:")
    print(json.dumps(v2_error, indent=2, ensure_ascii=False))
    print()
    
    print("V1 Error Format:")
    print(json.dumps(v1_error, indent=2, ensure_ascii=False))
    print()
    
    print("=== Demonstration Complete ===")


def demo_version_lifecycle():
    """Demonstrate version lifecycle management."""
    
    print("=== Version Lifecycle Demonstration ===\n")
    
    registry = VersionRegistry()
    
    # Create versions with lifecycle information
    from datetime import date, timedelta
    
    today = date.today()
    
    v1 = APIVersion(
        major=1, minor=0, patch=0,
        release_date=today - timedelta(days=365),
        deprecation_date=today - timedelta(days=30),
        sunset_date=today + timedelta(days=60),
        is_deprecated=True
    )
    
    v2 = APIVersion(
        major=2, minor=0, patch=0,
        release_date=today - timedelta(days=180),
        is_stable=True
    )
    
    v3 = APIVersion(
        major=3, minor=0, patch=0,
        release_date=today,
        is_experimental=True,
        is_stable=False
    )
    
    registry.register_version(v1)
    registry.register_version(v2, is_default=True, is_latest=True)
    registry.register_version(v3)
    
    print("Version Lifecycle Status:")
    for version in registry.list_versions():
        print(f"\nVersion {version.short_version}:")
        print(f"  Status: {'Deprecated' if version.is_deprecated else 'Active'}")
        print(f"  Stable: {version.is_stable}")
        print(f"  Experimental: {version.is_experimental}")
        print(f"  Release Date: {version.release_date}")
        
        if version.deprecation_date:
            print(f"  Deprecation Date: {version.deprecation_date}")
        
        if version.sunset_date:
            print(f"  Sunset Date: {version.sunset_date}")
            print(f"  Days Until Sunset: {version.days_until_sunset}")
    
    print("\n=== Lifecycle Demonstration Complete ===")


if __name__ == "__main__":
    demo_version_system()
    print("\n" + "="*60 + "\n")
    demo_version_lifecycle()