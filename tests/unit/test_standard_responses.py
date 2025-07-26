"""
Unit tests for standard response formats and exception handlers.

Tests the standardized HTTP response system and custom exception handling.
"""

import pytest
from datetime import datetime
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from app.shared.responses import (
    BaseResponse,
    ErrorResponse,
    PaginatedResponse,
    CreatedResponse,
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    created_response,
    paginated_response,
    HTTPStatusCodes
)
from app.shared.exceptions.custom_exceptions import (
    ValidationException,
    NotFoundException,
    ConflictException,
    BadRequestException
)


class TestResponseModels:
    """Test response model structures."""
    
    def test_base_response_structure(self):
        """Test BaseResponse model structure."""
        response = BaseResponse(
            success=True,
            data={"id": "123", "name": "Test"},
            message="Success"
        )
        
        assert response.success is True
        assert response.data == {"id": "123", "name": "Test"}
        assert response.message == "Success"
        assert response.status == "success"
        assert response.timestamp is not None
        assert response.metadata is None
    
    def test_error_response_structure(self):
        """Test ErrorResponse model structure."""
        response = ErrorResponse(
            errors=[
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid email",
                    "field": "email"
                }
            ],
            message="Validation failed"
        )
        
        assert response.success is False
        assert len(response.errors) == 1
        assert response.errors[0].code == "VALIDATION_ERROR"
        assert response.status == "error"
        assert response.timestamp is not None
    
    def test_paginated_response_structure(self):
        """Test PaginatedResponse model structure."""
        response = PaginatedResponse(
            items=[{"id": "1"}, {"id": "2"}],
            pagination={
                "total": 100,
                "page": 1,
                "size": 20,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        )
        
        assert response.success is True
        assert len(response.items) == 2
        assert response.pagination.total == 100
        assert response.pagination.has_next is True
        assert response.pagination.has_previous is False
    
    def test_created_response_structure(self):
        """Test CreatedResponse model structure."""
        response = CreatedResponse(
            data={"id": "new_123", "name": "New Item"},
            location="/api/v1/items/new_123"
        )
        
        assert response.success is True
        assert response.data["id"] == "new_123"
        assert response.location == "/api/v1/items/new_123"
        assert response.message == "Resource created successfully"


class TestResponseFactories:
    """Test response factory functions."""
    
    def test_success_response_factory(self):
        """Test success_response factory function."""
        response = success_response(
            data={"result": "ok"},
            message="Operation completed"
        )
        
        assert response.status_code == 200
        content = response.body.decode()
        assert '"success":true' in content
        assert '"result":"ok"' in content
        assert '"message":"Operation completed"' in content
    
    def test_error_response_factory(self):
        """Test error_response factory function."""
        response = error_response(
            errors=[{"code": "ERROR_CODE", "message": "Error occurred"}],
            message="Request failed",
            status_code=400
        )
        
        assert response.status_code == 400
        content = response.body.decode()
        assert '"success":false' in content
        assert '"ERROR_CODE"' in content
        assert '"Request failed"' in content
    
    def test_validation_error_response_factory(self):
        """Test validation_error_response factory function."""
        response = validation_error_response(
            errors=[
                {"code": "VALIDATION_ERROR", "message": "Invalid format", "field": "email"}
            ]
        )
        
        assert response.status_code == 422
        content = response.body.decode()
        assert '"success":false' in content
        assert '"VALIDATION_ERROR"' in content
        assert '"email"' in content
    
    def test_not_found_response_factory(self):
        """Test not_found_response factory function."""
        response = not_found_response(
            resource="user",
            resource_id="123"
        )
        
        assert response.status_code == 404
        content = response.body.decode()
        assert '"success":false' in content
        assert '"RESOURCE_NOT_FOUND"' in content
        assert "user with id '123' not found" in content
    
    def test_created_response_factory(self):
        """Test created_response factory function."""
        response = created_response(
            data={"id": "new_456", "name": "Created Item"},
            location="/api/v1/items/new_456"
        )
        
        assert response.status_code == 201
        assert response.headers.get("Location") == "/api/v1/items/new_456"
        content = response.body.decode()
        assert '"success":true' in content
        assert '"new_456"' in content
    
    def test_paginated_response_factory(self):
        """Test paginated_response factory function."""
        response = paginated_response(
            items=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            total=50,
            page=2,
            size=3
        )
        
        assert response.status_code == 200
        content = response.body.decode()
        assert '"success":true' in content
        assert '"total":50' in content
        assert '"page":2' in content
        assert '"size":3' in content
        assert '"has_next":true' in content
        assert '"has_previous":true' in content


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException(
            message="Validation failed",
            errors=[
                {"field": "email", "message": "Invalid email format"},
                {"field": "age", "message": "Must be positive"}
            ]
        )
        
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.detail == "Validation failed"
        assert len(exc.errors) == 2
    
    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException(
            resource="announcement",
            resource_id="abc123"
        )
        
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "announcement with id 'abc123' not found" in exc.detail
        assert exc.context["resource"] == "announcement"
        assert exc.context["resource_id"] == "abc123"
    
    def test_conflict_exception(self):
        """Test ConflictException."""
        exc = ConflictException(
            message="Email already exists",
            conflict_field="email",
            conflict_value="test@example.com"
        )
        
        assert exc.status_code == 409
        assert exc.error_code == "RESOURCE_CONFLICT"
        assert exc.detail == "Email already exists"
        assert exc.context["conflict_field"] == "email"
        assert exc.context["conflict_value"] == "test@example.com"
    
    def test_bad_request_exception(self):
        """Test BadRequestException."""
        exc = BadRequestException(
            message="Invalid request parameters",
            invalid_params=["start_date", "end_date"]
        )
        
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.detail == "Invalid request parameters"
        assert exc.context["invalid_params"] == ["start_date", "end_date"]


class TestHTTPStatusCodes:
    """Test HTTP status code constants."""
    
    def test_success_codes(self):
        """Test success status codes."""
        assert HTTPStatusCodes.OK == 200
        assert HTTPStatusCodes.CREATED == 201
        assert HTTPStatusCodes.ACCEPTED == 202
        assert HTTPStatusCodes.NO_CONTENT == 204
    
    def test_client_error_codes(self):
        """Test client error status codes."""
        assert HTTPStatusCodes.BAD_REQUEST == 400
        assert HTTPStatusCodes.UNAUTHORIZED == 401
        assert HTTPStatusCodes.FORBIDDEN == 403
        assert HTTPStatusCodes.NOT_FOUND == 404
        assert HTTPStatusCodes.UNPROCESSABLE_ENTITY == 422
        assert HTTPStatusCodes.TOO_MANY_REQUESTS == 429
    
    def test_server_error_codes(self):
        """Test server error status codes."""
        assert HTTPStatusCodes.INTERNAL_SERVER_ERROR == 500
        assert HTTPStatusCodes.NOT_IMPLEMENTED == 501
        assert HTTPStatusCodes.BAD_GATEWAY == 502
        assert HTTPStatusCodes.SERVICE_UNAVAILABLE == 503


class TestResponseIntegration:
    """Test response integration scenarios."""
    
    def test_success_response_with_metadata(self):
        """Test success response with metadata."""
        response = success_response(
            data={"count": 42},
            message="Query successful",
            metadata={
                "query_time_ms": 125,
                "cache_hit": True
            }
        )
        
        assert response.status_code == 200
        content = response.body.decode()
        assert '"query_time_ms":125' in content
        assert '"cache_hit":true' in content
    
    def test_error_response_with_multiple_errors(self):
        """Test error response with multiple errors."""
        response = error_response(
            errors=[
                {"code": "FIELD_REQUIRED", "message": "Name is required", "field": "name"},
                {"code": "INVALID_FORMAT", "message": "Invalid date format", "field": "date"},
                {"code": "OUT_OF_RANGE", "message": "Age must be 0-120", "field": "age"}
            ],
            message="Multiple validation errors",
            status_code=422,
            request_id="req_abc123"
        )
        
        assert response.status_code == 422
        content = response.body.decode()
        assert content.count('"code"') == 3
        assert '"request_id":"req_abc123"' in content
    
    def test_paginated_response_edge_cases(self):
        """Test paginated response edge cases."""
        # Empty results
        response = paginated_response(
            items=[],
            total=0,
            page=1,
            size=20
        )
        
        content = response.body.decode()
        assert '"total":0' in content
        assert '"total_pages":0' in content
        assert '"has_next":false' in content
        assert '"has_previous":false' in content
        
        # Last page
        response = paginated_response(
            items=[{"id": "99"}, {"id": "100"}],
            total=100,
            page=10,
            size=10
        )
        
        content = response.body.decode()
        assert '"page":10' in content
        assert '"total_pages":10' in content
        assert '"has_next":false' in content
        assert '"has_previous":true' in content