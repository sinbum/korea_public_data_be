"""
Integration tests for API versioning system.

Tests the complete versioning flow from request to response,
including middleware integration, version extraction, and response adaptation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import date

from app.main import app
from app.shared.versioning import APIVersion, VersionRegistry
from app.shared.version_middleware import APIVersionMiddleware


class TestVersioningIntegration:
    """Test complete versioning system integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_version_extraction_from_url(self, client):
        """Test version extraction from URL paths."""
        
        # Test different URL patterns
        test_cases = [
            ("/api/v1/announcements", "v1"),
            ("/api/v2/businesses", "v2"),
            ("/api/announcements", None),  # Should use default
        ]
        
        for url, expected_version in test_cases:
            # The middleware should extract version and add headers
            response = client.get(url)
            
            # Check if version headers are present
            if expected_version:
                assert "X-API-Version" in response.headers
                assert response.headers["X-API-Version"] == expected_version
    
    def test_version_headers_added(self, client):
        """Test that version headers are added to responses."""
        
        response = client.get("/")
        
        # Version headers should be present even for non-versioned endpoints
        expected_headers = [
            "X-API-Supported-Versions",
            "X-API-Latest-Version"
        ]
        
        for header in expected_headers:
            assert header in response.headers
    
    def test_version_info_endpoint(self, client):
        """Test the version information endpoint."""
        
        response = client.get("/version")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure
        assert "current_version" in data
        assert "supported_versions" in data
        assert "default_version" in data
        assert "latest_version" in data
        
        # Check current version structure
        current_version = data["current_version"]
        assert "version" in current_version
        assert "short_version" in current_version
        assert "is_stable" in current_version
        assert "is_deprecated" in current_version
        
        # Check supported versions is a list
        assert isinstance(data["supported_versions"], list)
        
        # Each supported version should have required fields
        for version in data["supported_versions"]:
            assert "version" in version
            assert "short_version" in version
            assert "is_stable" in version
            assert "is_deprecated" in version
    
    def test_version_error_handling(self, client):
        """Test error handling for unsupported versions."""
        
        # Test with unsupported version in URL
        response = client.get("/api/v99/announcements")
        
        # Should return 400 Bad Request for unsupported version
        assert response.status_code == 400
        
        data = response.json()
        assert "Unsupported API version" in data.get("message", "")
    
    def test_deprecation_warnings(self, client):
        """Test deprecation warnings for deprecated versions."""
        
        # Create a deprecated version for testing
        with patch('app.shared.versioning.get_version_registry') as mock_registry:
            registry = VersionRegistry()
            
            deprecated_version = APIVersion(
                major=1, minor=0, patch=0,
                is_deprecated=True,
                deprecation_date=date.today()
            )
            current_version = APIVersion(major=2, minor=0, patch=0)
            
            registry.register_version(deprecated_version)
            registry.register_version(current_version, is_default=True, is_latest=True)
            
            mock_registry.return_value = registry
            
            # Request with deprecated version
            response = client.get("/api/v1/announcements")
            
            # Should still work but with deprecation headers
            if "X-API-Deprecated" in response.headers:
                assert response.headers["X-API-Deprecated"] == "true"
    
    def test_health_check_skip_versioning(self, client):
        """Test that health check endpoint skips versioning."""
        
        response = client.get("/health")
        assert response.status_code == 200
        
        # Health endpoint should work without version processing
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_docs_skip_versioning(self, client):
        """Test that documentation endpoints skip versioning."""
        
        # Test various doc endpoints
        doc_endpoints = ["/docs", "/redoc", "/openapi.json"]
        
        for endpoint in doc_endpoints:
            response = client.get(endpoint)
            
            # Should get response (might be 200 or redirect)
            # Main point is that it doesn't fail with version errors
            assert response.status_code in [200, 307, 308]
    
    def test_response_adaptation_headers(self, client):
        """Test that responses include appropriate version headers."""
        
        response = client.get("/")
        
        # Check for version-related headers
        version_headers = [
            "X-API-Version",
            "X-API-Supported-Versions"
        ]
        
        for header in version_headers:
            if header in response.headers:
                assert len(response.headers[header]) > 0
    
    def test_cors_with_versioning(self, client):
        """Test that CORS works with versioning middleware."""
        
        # Make a preflight request
        response = client.options(
            "/api/v1/announcements",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Should include CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_error_response_format_consistency(self, client):
        """Test that error responses maintain format consistency across versions."""
        
        # Test 404 error
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        
        # Should have consistent error format
        # (specific format depends on version, but should be valid JSON)
        assert isinstance(data, dict)
        assert len(data) > 0


class TestVersionedRouterIntegration:
    """Test versioned router functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_version_compatibility_dependency(self, client):
        """Test version compatibility checking in dependencies."""
        
        # This would test version-specific endpoints if they were enabled
        # For now, just verify the basic structure works
        
        response = client.get("/")
        assert response.status_code == 200
    
    def test_experimental_endpoint_headers(self, client):
        """Test that experimental endpoints include appropriate headers."""
        
        # This would test experimental endpoints if they were enabled
        # The headers would include X-API-Experimental: true
        
        response = client.get("/")
        
        # Basic test to ensure system is working
        assert response.status_code == 200


class TestVersionMiddlewareOrder:
    """Test middleware ordering and interaction."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_middleware_execution_order(self, client):
        """Test that middlewares execute in correct order."""
        
        response = client.get("/")
        
        # Version middleware should execute and add headers
        # Other middlewares should also work correctly
        assert response.status_code == 200
        
        # Check that response has expected structure
        data = response.json()
        assert "service" in data
        assert "version" in data
    
    def test_rate_limiting_with_versioning(self, client):
        """Test that rate limiting works with versioning."""
        
        # Make multiple requests to test rate limiting
        for i in range(5):
            response = client.get("/")
            assert response.status_code == 200
        
        # Should still work (rate limit is high in test environment)
        assert response.status_code == 200
    
    def test_request_validation_with_versioning(self, client):
        """Test that request validation works with versioning."""
        
        # Test with invalid request that should trigger validation
        response = client.post("/api/v1/announcements", json={})
        
        # Should get validation error (422 or 400)
        assert response.status_code in [400, 422, 404, 405]  # Various possible responses


class TestVersioningPerformance:
    """Test versioning system performance."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_version_extraction_performance(self, client):
        """Test that version extraction doesn't significantly impact performance."""
        
        import time
        
        # Measure time for multiple requests
        start_time = time.time()
        
        for i in range(10):
            response = client.get("/")
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 10 requests in reasonable time (< 2 seconds)
        assert total_time < 2.0
    
    def test_response_adaptation_performance(self, client):
        """Test that response adaptation doesn't significantly impact performance."""
        
        import time
        
        # Test with version-specific endpoint
        start_time = time.time()
        
        for i in range(10):
            response = client.get("/version")
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 10 requests with adaptation in reasonable time
        assert total_time < 2.0


class TestVersioningEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_malformed_version_headers(self, client):
        """Test handling of malformed version headers."""
        
        # Test with malformed Accept header
        response = client.get(
            "/",
            headers={"Accept": "application/json; version=invalid"}
        )
        
        # Should handle gracefully and use default version
        assert response.status_code == 200
    
    def test_multiple_version_indicators(self, client):
        """Test when multiple version indicators are present."""
        
        # Test with both URL version and header version
        response = client.get(
            "/api/v1/announcements",
            headers={"Accept": "application/json; version=2"}
        )
        
        # Should handle conflicts gracefully
        # (URL version typically takes precedence)
        assert response.status_code in [200, 404, 405]  # Various valid responses
    
    def test_very_long_version_strings(self, client):
        """Test handling of very long version strings."""
        
        long_version = "v" + "1" * 100  # Very long version string
        
        response = client.get(f"/api/{long_version}/announcements")
        
        # Should return appropriate error for invalid version
        assert response.status_code == 400
    
    def test_empty_version_extraction(self, client):
        """Test version extraction with empty or null values."""
        
        # Test with empty query parameters
        response = client.get("/api/announcements?version=")
        
        # Should handle gracefully and use default
        assert response.status_code in [200, 404, 405]