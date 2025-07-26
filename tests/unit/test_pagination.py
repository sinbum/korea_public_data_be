"""
Unit tests for pagination, sorting, and filtering system.

Tests the standard pagination components including parameters,
result formatting, and MongoDB integration helpers.
"""

import pytest
from typing import List, Dict, Any
from pydantic import ValidationError

from app.shared.pagination import (
    PaginationParams,
    SortParams,
    FilterParams,
    PaginatedResult,
    SortOrder,
    CommonSortFields,
    PaginationHelper,
    paginate_query_result,
    build_pagination_links
)


class TestPaginationParams:
    """Test PaginationParams model and functionality."""
    
    def test_default_values(self):
        """Test default pagination parameters."""
        params = PaginationParams()
        
        assert params.page == 1
        assert params.size == 20
        assert params.sort == "id"
        assert params.order == SortOrder.DESC
    
    def test_custom_values(self):
        """Test custom pagination parameters."""
        params = PaginationParams(
            page=3,
            size=50,
            sort="created_at",
            order=SortOrder.ASC
        )
        
        assert params.page == 3
        assert params.size == 50
        assert params.sort == "created_at"
        assert params.order == SortOrder.ASC
    
    def test_validation_limits(self):
        """Test parameter validation limits."""
        # Test page limits
        with pytest.raises(ValidationError):
            PaginationParams(page=0)  # Below minimum
        
        with pytest.raises(ValidationError):
            PaginationParams(page=1001)  # Above maximum
        
        # Test size limits
        with pytest.raises(ValidationError):
            PaginationParams(size=0)  # Below minimum
        
        with pytest.raises(ValidationError):
            PaginationParams(size=101)  # Above maximum
    
    def test_sort_field_sanitization(self):
        """Test sort field sanitization."""
        # Test injection prevention
        params = PaginationParams(sort="id; DROP TABLE users;")
        assert "$" not in params.sort
        assert ";" in params.sort  # Basic string, not SQL injection in MongoDB
        
        # Test field cleaning
        params = PaginationParams(sort="User.Name$field")
        assert "$" not in params.sort
        assert params.sort == "user_namefield"
    
    def test_order_normalization(self):
        """Test sort order normalization."""
        # Test string normalization
        params = PaginationParams(order="asc")
        assert params.order == SortOrder.ASC
        
        params = PaginationParams(order="DESCENDING")
        assert params.order == SortOrder.DESC
        
        params = PaginationParams(order="1")
        assert params.order == SortOrder.ASC
        
        params = PaginationParams(order="-1")
        assert params.order == SortOrder.DESC
    
    def test_mongodb_properties(self):
        """Test MongoDB-specific helper properties."""
        params = PaginationParams(page=3, size=10, sort="name", order=SortOrder.ASC)
        
        # Test skip calculation
        assert params.skip == 20  # (3-1) * 10
        
        # Test limit
        assert params.limit == 10
        
        # Test MongoDB sort specification
        mongo_sort = params.mongo_sort
        assert mongo_sort == [("name", 1)]
        
        # Test DESC order
        params.order = SortOrder.DESC
        mongo_sort = params.mongo_sort
        assert mongo_sort == [("name", -1)]
    
    def test_to_dict(self):
        """Test dictionary conversion for logging."""
        params = PaginationParams(page=2, size=25, sort="updated_at", order=SortOrder.ASC)
        result = params.to_dict()
        
        expected = {
            "page": 2,
            "size": 25,
            "sort": "updated_at",
            "order": "asc",
            "skip": 25,
            "limit": 25
        }
        assert result == expected


class TestSortParams:
    """Test enhanced sorting with multiple fields."""
    
    def test_single_field(self):
        """Test single field sorting."""
        sort_params = SortParams(fields=["name"], orders=[SortOrder.ASC])
        
        assert sort_params.fields == ["name"]
        assert sort_params.orders == [SortOrder.ASC]
        
        mongo_sort = sort_params.mongo_sort
        assert mongo_sort == [("name", 1)]
    
    def test_multiple_fields(self):
        """Test multiple field sorting."""
        sort_params = SortParams(
            fields=["priority", "created_at", "name"],
            orders=[SortOrder.DESC, SortOrder.DESC, SortOrder.ASC]
        )
        
        mongo_sort = sort_params.mongo_sort
        expected = [
            ("priority", -1),
            ("created_at", -1),
            ("name", 1)
        ]
        assert mongo_sort == expected
    
    def test_order_padding(self):
        """Test automatic order padding when orders < fields."""
        sort_params = SortParams(
            fields=["priority", "name", "date"],
            orders=[SortOrder.ASC]  # Only one order for 3 fields
        )
        
        # Should pad with DESC
        assert len(sort_params.orders) == 3
        assert sort_params.orders == [SortOrder.ASC, SortOrder.DESC, SortOrder.DESC]
    
    def test_order_truncation(self):
        """Test order truncation when orders > fields."""
        sort_params = SortParams(
            fields=["name"],
            orders=[SortOrder.ASC, SortOrder.DESC, SortOrder.ASC]  # Extra orders
        )
        
        # Should truncate to match fields
        assert len(sort_params.orders) == 1
        assert sort_params.orders == [SortOrder.ASC]
    
    def test_field_sanitization(self):
        """Test field name sanitization."""
        sort_params = SortParams(fields=["user.name$field", "item$price"])
        
        # Should sanitize field names
        assert sort_params.fields == ["user_namefield", "itemprice"]


class TestFilterParams:
    """Test filtering parameters."""
    
    def test_basic_filters(self):
        """Test basic filter parameters."""
        filters = FilterParams(
            search="test query",
            status="active",
            category="news",
            tags=["python", "api"]
        )
        
        assert filters.search == "test query"
        assert filters.status == "active"
        assert filters.category == "news"
        assert filters.tags == ["python", "api"]
    
    def test_date_filters(self):
        """Test date range filters."""
        filters = FilterParams(
            date_from="2024-01-01",
            date_to="2024-12-31"
        )
        
        assert filters.date_from == "2024-01-01"
        assert filters.date_to == "2024-12-31"
    
    def test_mongodb_filter_conversion(self):
        """Test conversion to MongoDB filter specification."""
        filters = FilterParams(
            search="test",
            status="active",
            category="news",
            date_from="2024-01-01",
            date_to="2024-12-31",
            tags=["python", "api"]
        )
        
        mongo_filter = filters.to_mongo_filter()
        
        # Check text search
        assert mongo_filter["$text"]["$search"] == "test"
        
        # Check status regex
        assert mongo_filter["status"]["$regex"] == "^active$"
        assert mongo_filter["status"]["$options"] == "i"
        
        # Check category regex
        assert mongo_filter["category"]["$regex"] == "^news$"
        assert mongo_filter["category"]["$options"] == "i"
        
        # Check date range
        date_filter = mongo_filter["created_at"]
        assert date_filter["$gte"] == "2024-01-01"
        assert date_filter["$lte"] == "2024-12-31"
        
        # Check tags
        assert mongo_filter["tags"]["$in"] == ["python", "api"]
    
    def test_empty_filters(self):
        """Test empty filter conversion."""
        filters = FilterParams()
        mongo_filter = filters.to_mongo_filter()
        
        assert mongo_filter == {}
    
    def test_partial_date_filter(self):
        """Test partial date filters."""
        # Only from date
        filters = FilterParams(date_from="2024-01-01")
        mongo_filter = filters.to_mongo_filter()
        assert mongo_filter["created_at"]["$gte"] == "2024-01-01"
        assert "$lte" not in mongo_filter["created_at"]
        
        # Only to date
        filters = FilterParams(date_to="2024-12-31")
        mongo_filter = filters.to_mongo_filter()
        assert mongo_filter["created_at"]["$lte"] == "2024-12-31"
        assert "$gte" not in mongo_filter["created_at"]


class TestPaginatedResult:
    """Test paginated result container."""
    
    def test_basic_result(self):
        """Test basic paginated result."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        result = PaginatedResult(
            items=items,
            total=100,
            page=1,
            size=20
        )
        
        assert result.items == items
        assert result.total == 100
        assert result.page == 1
        assert result.size == 20
    
    def test_pagination_metadata(self):
        """Test pagination metadata calculations."""
        result = PaginatedResult(
            items=[{"id": "1"}],
            total=100,
            page=3,
            size=20
        )
        
        # Test calculated properties
        assert result.total_pages == 5  # ceil(100/20)
        assert result.has_next is True
        assert result.has_previous is True
        assert result.is_first_page is False
        assert result.is_last_page is False
        assert result.next_page == 4
        assert result.previous_page == 2
    
    def test_first_page(self):
        """Test first page metadata."""
        result = PaginatedResult(
            items=[{"id": "1"}],
            total=100,
            page=1,
            size=20
        )
        
        assert result.has_previous is False
        assert result.is_first_page is True
        assert result.previous_page is None
    
    def test_last_page(self):
        """Test last page metadata."""
        result = PaginatedResult(
            items=[{"id": "1"}],
            total=100,
            page=5,
            size=20
        )
        
        assert result.has_next is False
        assert result.is_last_page is True
        assert result.next_page is None
    
    def test_empty_result(self):
        """Test empty result set."""
        result = PaginatedResult(
            items=[],
            total=0,
            page=1,
            size=20
        )
        
        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False
        assert result.is_first_page is True
        assert result.is_last_page is True
    
    def test_pagination_meta_dict(self):
        """Test pagination metadata dictionary conversion."""
        result = PaginatedResult(
            items=[{"id": "1"}],
            total=50,
            page=2,
            size=10
        )
        
        meta = result.to_pagination_meta()
        expected = {
            "total": 50,
            "page": 2,
            "size": 10,
            "total_pages": 5,
            "has_next": True,
            "has_previous": True,
            "is_first_page": False,
            "is_last_page": False,
            "next_page": 3,
            "previous_page": 1
        }
        assert meta == expected


class TestPaginationHelper:
    """Test pagination helper utilities."""
    
    def test_validate_pagination_params(self):
        """Test parameter validation and normalization."""
        # Normal case
        page, size = PaginationHelper.validate_pagination_params(2, 30)
        assert page == 2
        assert size == 30
        
        # Below minimum
        page, size = PaginationHelper.validate_pagination_params(0, -5, max_size=50)
        assert page == 1
        assert size == 1
        
        # Above maximum
        page, size = PaginationHelper.validate_pagination_params(1, 200, max_size=100)
        assert page == 1
        assert size == 100
    
    def test_calculate_offset_limit(self):
        """Test offset/limit calculation."""
        offset, limit = PaginationHelper.calculate_offset_limit(1, 20)
        assert offset == 0
        assert limit == 20
        
        offset, limit = PaginationHelper.calculate_offset_limit(3, 15)
        assert offset == 30  # (3-1) * 15
        assert limit == 15
    
    def test_create_empty_result(self):
        """Test empty result creation."""
        params = PaginationParams(page=2, size=25)
        result = PaginationHelper.create_empty_result(params)
        
        assert result.items == []
        assert result.total == 0
        assert result.page == 2
        assert result.size == 25


class TestPaginationUtilities:
    """Test pagination utility functions."""
    
    def test_paginate_query_result(self):
        """Test query result pagination."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        pagination = PaginationParams(page=2, size=3)
        
        result = paginate_query_result(items, total=50, pagination=pagination)
        
        assert result.items == items
        assert result.total == 50
        assert result.page == 2
        assert result.size == 3
    
    def test_build_pagination_links(self):
        """Test pagination link building."""
        result = PaginatedResult(
            items=[{"id": "1"}],
            total=100,
            page=3,
            size=20
        )
        
        links = build_pagination_links(
            base_url="/api/v1/items",
            pagination_result=result,
            query_params={"status": "active", "sort": "name"}
        )
        
        # Check link structure
        assert "self" in links
        assert "first" in links
        assert "last" in links
        assert "next" in links
        assert "previous" in links
        
        # Check URL construction
        assert "/api/v1/items?" in links["self"]
        assert "page=3" in links["self"]
        assert "status=active" in links["self"]
        assert "sort=name" in links["self"]
        
        assert "page=4" in links["next"]
        assert "page=2" in links["previous"]
        assert "page=1" in links["first"]
        assert "page=5" in links["last"]
    
    def test_build_pagination_links_edge_cases(self):
        """Test pagination links for edge cases."""
        # First page
        result = PaginatedResult(items=[], total=50, page=1, size=20)
        links = build_pagination_links("/api/v1/items", result)
        
        assert links["previous"] is None
        assert links["next"] is not None
        
        # Last page
        result = PaginatedResult(items=[], total=50, page=3, size=20)
        links = build_pagination_links("/api/v1/items", result)
        
        assert links["next"] is None
        assert links["previous"] is not None
        
        # Empty result
        result = PaginatedResult(items=[], total=0, page=1, size=20)
        links = build_pagination_links("/api/v1/items", result)
        
        assert links["first"] is None
        assert links["last"] is None


class TestSortOrderEnum:
    """Test sort order enumeration."""
    
    def test_enum_values(self):
        """Test enum value definitions."""
        assert SortOrder.ASC == "asc"
        assert SortOrder.DESC == "desc"
        assert SortOrder.ASCENDING == "ascending"
        assert SortOrder.DESCENDING == "descending"
    
    def test_enum_comparison(self):
        """Test enum comparison in logic."""
        # Test ASC variations
        asc_values = [SortOrder.ASC, SortOrder.ASCENDING]
        for value in asc_values:
            # This is how it's used in the code
            direction = 1 if value in [SortOrder.ASC, SortOrder.ASCENDING] else -1
            assert direction == 1
        
        # Test DESC variations
        desc_values = [SortOrder.DESC, SortOrder.DESCENDING]
        for value in desc_values:
            direction = 1 if value in [SortOrder.ASC, SortOrder.ASCENDING] else -1
            assert direction == -1


class TestCommonSortFields:
    """Test common sort field enumeration."""
    
    def test_field_values(self):
        """Test common field definitions."""
        assert CommonSortFields.ID == "id"
        assert CommonSortFields.CREATED_AT == "created_at"
        assert CommonSortFields.UPDATED_AT == "updated_at"
        assert CommonSortFields.NAME == "name"
        assert CommonSortFields.TITLE == "title"
        assert CommonSortFields.STATUS == "status"
        assert CommonSortFields.PRIORITY == "priority"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_typical_api_request(self):
        """Test typical API request scenario."""
        # Simulate typical API request parameters
        params = PaginationParams(
            page=2,
            size=10,
            sort="created_at",
            order=SortOrder.DESC
        )
        
        filters = FilterParams(
            search="python tutorial",
            status="published",
            tags=["programming", "tutorial"]
        )
        
        # Test MongoDB query construction
        mongo_filter = filters.to_mongo_filter()
        mongo_sort = params.mongo_sort
        skip = params.skip
        limit = params.limit
        
        # Verify query components
        assert skip == 10
        assert limit == 10
        assert mongo_sort == [("created_at", -1)]
        assert "$text" in mongo_filter
        assert "status" in mongo_filter
        assert "tags" in mongo_filter
    
    def test_complex_sorting_scenario(self):
        """Test complex multi-field sorting."""
        sort_params = SortParams(
            fields=["priority", "created_at", "title"],
            orders=[SortOrder.DESC, SortOrder.DESC, SortOrder.ASC]
        )
        
        mongo_sort = sort_params.mongo_sort
        expected = [
            ("priority", -1),  # High priority first
            ("created_at", -1),  # Recent first
            ("title", 1)  # Alphabetical
        ]
        
        assert mongo_sort == expected
    
    def test_pagination_with_results(self):
        """Test complete pagination flow with results."""
        # Simulate database query results
        query_items = [
            {"id": "21", "title": "Item 21"},
            {"id": "22", "title": "Item 22"},
            {"id": "23", "title": "Item 23"}
        ]
        total_count = 145
        
        params = PaginationParams(page=8, size=20)
        result = paginate_query_result(query_items, total_count, params)
        
        # Verify result structure
        assert len(result.items) == 3
        assert result.total == 145
        assert result.page == 8
        assert result.size == 20
        assert result.total_pages == 8  # ceil(145/20) = 8
        assert result.has_next is False  # Last page
        assert result.has_previous is True
        
        # Test metadata
        meta = result.to_pagination_meta()
        assert meta["total_pages"] == 8
        assert meta["is_last_page"] is True