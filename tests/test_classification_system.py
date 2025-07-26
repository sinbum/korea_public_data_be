"""
Comprehensive tests for the classification code system.

Tests all components including enums, models, validators, services, and API endpoints.
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from app.shared.classification.enums import BusinessCategory, ContentCategory, ClassificationCodeType
from app.shared.classification.models import (
    BusinessCategoryCode, ContentCategoryCode, ClassificationCodeValidationResult,
    ClassificationCodeSearchRequest, ClassificationCodeStats
)
from app.shared.classification.validators import (
    BusinessCategoryValidator, ContentCategoryValidator, UnifiedClassificationValidator
)
from app.shared.classification.services import ClassificationService


class TestBusinessCategoryEnum:
    """Test BusinessCategory enum functionality."""
    
    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert BusinessCategory.COMMERCIALIZATION.value == "cmrczn_tab1"
        assert BusinessCategory.STARTUP_EDUCATION.value == "cmrczn_tab2"
        assert BusinessCategory.FACILITIES_SPACE_INCUBATION.value == "cmrczn_tab3"
        assert BusinessCategory.MENTORING_CONSULTING.value == "cmrczn_tab4"
        assert BusinessCategory.EVENTS_NETWORKING.value == "cmrczn_tab5"
        assert BusinessCategory.TECHNOLOGY_RND.value == "cmrczn_tab6"
        assert BusinessCategory.LOAN.value == "cmrczn_tab7"
        assert BusinessCategory.HUMAN_RESOURCES.value == "cmrczn_tab8"
        assert BusinessCategory.GLOBAL.value == "cmrczn_tab9"
    
    def test_get_description(self):
        """Test description retrieval."""
        assert BusinessCategory.get_description("cmrczn_tab1") == "사업화"
        assert BusinessCategory.get_description("cmrczn_tab2") == "창업교육"
        assert BusinessCategory.get_description("invalid_code") == "알 수 없음"
    
    def test_get_detailed_description(self):
        """Test detailed description retrieval."""
        desc = BusinessCategory.get_detailed_description("cmrczn_tab1")
        assert "아이디어나 기술을 실제 사업으로 전환" in desc
    
    def test_get_main_features(self):
        """Test main features retrieval."""
        features = BusinessCategory.get_main_features("cmrczn_tab1")
        assert isinstance(features, list)
        assert len(features) > 0
        assert "사업 모델 개발 지원" in features
    
    def test_get_all_codes(self):
        """Test getting all valid codes."""
        codes = BusinessCategory.get_all_codes()
        assert len(codes) == 9
        assert "cmrczn_tab1" in codes
        assert "cmrczn_tab9" in codes
    
    def test_is_valid_code(self):
        """Test code validation."""
        assert BusinessCategory.is_valid_code("cmrczn_tab1") is True
        assert BusinessCategory.is_valid_code("cmrczn_tab9") is True
        assert BusinessCategory.is_valid_code("invalid_code") is False
        assert BusinessCategory.is_valid_code("cmrczn_tab0") is False
        assert BusinessCategory.is_valid_code("cmrczn_tab10") is False


class TestContentCategoryEnum:
    """Test ContentCategory enum functionality."""
    
    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert ContentCategory.POLICY_NOTICE.value == "notice_matr"
        assert ContentCategory.SUCCESS_CASE.value == "fnd_scs_case"
        assert ContentCategory.ECOSYSTEM_TRENDS.value == "kstartup_isse_trd"
    
    def test_get_description(self):
        """Test description retrieval."""
        assert ContentCategory.get_description("notice_matr") == "정책 및 규제정보(공지사항)"
        assert ContentCategory.get_description("fnd_scs_case") == "창업우수사례"
        assert ContentCategory.get_description("invalid_code") == "알 수 없음"
    
    def test_get_content_types(self):
        """Test content types retrieval."""
        types = ContentCategory.get_content_types("notice_matr")
        assert isinstance(types, list)
        assert len(types) > 0
        assert "정부 창업 정책 발표" in types
    
    def test_get_all_codes(self):
        """Test getting all valid codes."""
        codes = ContentCategory.get_all_codes()
        assert len(codes) == 3
        assert "notice_matr" in codes
        assert "fnd_scs_case" in codes
        assert "kstartup_isse_trd" in codes
    
    def test_is_valid_code(self):
        """Test code validation."""
        assert ContentCategory.is_valid_code("notice_matr") is True
        assert ContentCategory.is_valid_code("fnd_scs_case") is True
        assert ContentCategory.is_valid_code("invalid_code") is False


class TestBusinessCategoryCode:
    """Test BusinessCategoryCode model."""
    
    def test_from_enum(self):
        """Test creating model from enum."""
        code = BusinessCategoryCode.from_enum(BusinessCategory.COMMERCIALIZATION)
        assert code.code == "cmrczn_tab1"
        assert code.name == "사업화"
        assert len(code.features) > 0
    
    def test_validate_code_format(self):
        """Test code format validation."""
        code = BusinessCategoryCode.from_enum(BusinessCategory.COMMERCIALIZATION)
        assert code.validate_code_format() is True
        
        # Test invalid format
        invalid_code = BusinessCategoryCode(
            code="invalid",
            name="Test",
            description="Test"
        )
        assert invalid_code.validate_code_format() is False
    
    def test_get_all_categories(self):
        """Test getting all categories."""
        categories = BusinessCategoryCode.get_all_categories()
        assert len(categories) == 9
        assert all(isinstance(cat, BusinessCategoryCode) for cat in categories)
    
    def test_add_remove_feature(self):
        """Test adding and removing features."""
        code = BusinessCategoryCode.from_enum(BusinessCategory.COMMERCIALIZATION)
        initial_count = len(code.features)
        
        # Add feature
        code.add_feature("Test feature")
        assert len(code.features) == initial_count + 1
        assert "Test feature" in code.features
        
        # Remove feature
        success = code.remove_feature("Test feature")
        assert success is True
        assert len(code.features) == initial_count
        assert "Test feature" not in code.features
    
    def test_is_global_focused(self):
        """Test global focus detection."""
        global_code = BusinessCategoryCode.from_enum(BusinessCategory.GLOBAL)
        assert global_code.is_global_focused() is True
        
        other_code = BusinessCategoryCode.from_enum(BusinessCategory.COMMERCIALIZATION)
        assert other_code.is_global_focused() is False
    
    def test_is_funding_related(self):
        """Test funding relation detection."""
        loan_code = BusinessCategoryCode.from_enum(BusinessCategory.LOAN)
        assert loan_code.is_funding_related() is True
        
        education_code = BusinessCategoryCode.from_enum(BusinessCategory.STARTUP_EDUCATION)
        assert education_code.is_funding_related() is False


class TestContentCategoryCode:
    """Test ContentCategoryCode model."""
    
    def test_from_enum(self):
        """Test creating model from enum."""
        code = ContentCategoryCode.from_enum(ContentCategory.POLICY_NOTICE)
        assert code.code == "notice_matr"
        assert code.name == "정책 및 규제정보(공지사항)"
        assert len(code.content_types) > 0
    
    def test_validate_code_format(self):
        """Test code format validation."""
        code = ContentCategoryCode.from_enum(ContentCategory.POLICY_NOTICE)
        assert code.validate_code_format() is True
        
        # Test invalid format
        invalid_code = ContentCategoryCode(
            code="invalid",
            name="Test",
            description="Test"
        )
        assert invalid_code.validate_code_format() is False
    
    def test_add_remove_content_type(self):
        """Test adding and removing content types."""
        code = ContentCategoryCode.from_enum(ContentCategory.POLICY_NOTICE)
        initial_count = len(code.content_types)
        
        # Add content type
        code.add_content_type("Test content type")
        assert len(code.content_types) == initial_count + 1
        assert "Test content type" in code.content_types
        
        # Remove content type
        success = code.remove_content_type("Test content type")
        assert success is True
        assert len(code.content_types) == initial_count
        assert "Test content type" not in code.content_types
    
    def test_is_policy_related(self):
        """Test policy relation detection."""
        policy_code = ContentCategoryCode.from_enum(ContentCategory.POLICY_NOTICE)
        assert policy_code.is_policy_related() is True
        
        case_code = ContentCategoryCode.from_enum(ContentCategory.SUCCESS_CASE)
        assert case_code.is_policy_related() is False
    
    def test_is_trend_analysis(self):
        """Test trend analysis detection."""
        trend_code = ContentCategoryCode.from_enum(ContentCategory.ECOSYSTEM_TRENDS)
        assert trend_code.is_trend_analysis() is True
        
        policy_code = ContentCategoryCode.from_enum(ContentCategory.POLICY_NOTICE)
        assert policy_code.is_trend_analysis() is False


class TestBusinessCategoryValidator:
    """Test BusinessCategoryValidator."""
    
    def setUp(self):
        self.validator = BusinessCategoryValidator()
    
    def test_valid_codes(self):
        """Test validation of valid codes."""
        validator = BusinessCategoryValidator()
        
        for code in BusinessCategory.get_all_codes():
            result = validator.validate(code)
            assert result.is_valid is True
            assert len(result.validation_errors) == 0
    
    def test_invalid_codes(self):
        """Test validation of invalid codes."""
        validator = BusinessCategoryValidator()
        
        invalid_codes = [
            "invalid_code",
            "cmrczn_tab0",  # Out of range
            "cmrczn_tab10",  # Out of range
            "CMRCZN_TAB1",  # Wrong case
            "cmrczn_tab",   # Missing number
            "",             # Empty
            None            # None
        ]
        
        for code in invalid_codes:
            result = validator.validate(code)
            assert result.is_valid is False
            assert len(result.validation_errors) > 0
    
    def test_suggestions(self):
        """Test suggestion generation."""
        validator = BusinessCategoryValidator()
        
        # Test case insensitive suggestion
        suggestions = validator.get_suggestions("CMRCZN_TAB1")
        assert "cmrczn_tab1" in suggestions
        
        # Test partial match suggestions
        suggestions = validator.get_suggestions("cmrczn_tab0")
        assert len(suggestions) > 0
        assert all(code.startswith("cmrczn_tab") for code in suggestions)
    
    def test_get_code_info(self):
        """Test getting code information."""
        validator = BusinessCategoryValidator()
        
        info = validator.get_code_info("cmrczn_tab1")
        assert info is not None
        assert info["code"] == "cmrczn_tab1"
        assert info["name"] == "사업화"
        assert info["is_valid"] is True
        
        # Test invalid code
        info = validator.get_code_info("invalid_code")
        assert info is None


class TestContentCategoryValidator:
    """Test ContentCategoryValidator."""
    
    def test_valid_codes(self):
        """Test validation of valid codes."""
        validator = ContentCategoryValidator()
        
        for code in ContentCategory.get_all_codes():
            result = validator.validate(code)
            assert result.is_valid is True
            assert len(result.validation_errors) == 0
    
    def test_invalid_codes(self):
        """Test validation of invalid codes."""
        validator = ContentCategoryValidator()
        
        invalid_codes = [
            "invalid_code",
            "NOTICE_MATR",  # Wrong case
            "notice",       # Partial
            "",             # Empty
            None            # None
        ]
        
        for code in invalid_codes:
            result = validator.validate(code)
            assert result.is_valid is False
            assert len(result.validation_errors) > 0
    
    def test_suggestions(self):
        """Test suggestion generation."""
        validator = ContentCategoryValidator()
        
        # Test keyword-based suggestions
        suggestions = validator.get_suggestions("notice")
        assert "notice_matr" in suggestions
        
        suggestions = validator.get_suggestions("case")
        assert "fnd_scs_case" in suggestions
        
        suggestions = validator.get_suggestions("trend")
        assert "kstartup_isse_trd" in suggestions


class TestUnifiedClassificationValidator:
    """Test UnifiedClassificationValidator."""
    
    def test_auto_detection(self):
        """Test auto-detection of code types."""
        validator = UnifiedClassificationValidator()
        
        # Test business category detection
        result = validator.validate("cmrczn_tab1")
        assert result.is_valid is True
        assert result.code_type == ClassificationCodeType.BUSINESS_CATEGORY.value
        
        # Test content category detection
        result = validator.validate("notice_matr")
        assert result.is_valid is True
        assert result.code_type == ClassificationCodeType.CONTENT_CATEGORY.value
    
    def test_detect_code_type(self):
        """Test code type detection."""
        validator = UnifiedClassificationValidator()
        
        assert validator.detect_code_type("cmrczn_tab1") == ClassificationCodeType.BUSINESS_CATEGORY.value
        assert validator.detect_code_type("notice_matr") == ClassificationCodeType.CONTENT_CATEGORY.value
        assert validator.detect_code_type("invalid_code") is None
    
    def test_get_all_valid_codes(self):
        """Test getting all valid codes."""
        validator = UnifiedClassificationValidator()
        
        all_codes = validator.get_all_valid_codes()
        assert ClassificationCodeType.BUSINESS_CATEGORY.value in all_codes
        assert ClassificationCodeType.CONTENT_CATEGORY.value in all_codes
        assert len(all_codes[ClassificationCodeType.BUSINESS_CATEGORY.value]) == 9
        assert len(all_codes[ClassificationCodeType.CONTENT_CATEGORY.value]) == 3
    
    def test_batch_validation(self):
        """Test batch validation."""
        validator = UnifiedClassificationValidator()
        
        codes = ["cmrczn_tab1", "notice_matr", "invalid_code"]
        results = validator.validate_batch(codes)
        
        assert len(results) == 3
        assert results["cmrczn_tab1"].is_valid is True
        assert results["notice_matr"].is_valid is True
        assert results["invalid_code"].is_valid is False


class TestClassificationService:
    """Test ClassificationService functionality."""
    
    @pytest.fixture
    def service(self):
        return ClassificationService()
    
    @pytest.mark.asyncio
    async def test_get_business_categories(self, service):
        """Test getting business categories."""
        categories = await service.get_business_categories()
        assert len(categories) == 9
        assert all(isinstance(cat, BusinessCategoryCode) for cat in categories)
    
    @pytest.mark.asyncio
    async def test_get_business_category(self, service):
        """Test getting specific business category."""
        category = await service.get_business_category("cmrczn_tab1")
        assert category is not None
        assert category.code == "cmrczn_tab1"
        assert category.name == "사업화"
        
        # Test invalid code
        invalid_category = await service.get_business_category("invalid_code")
        assert invalid_category is None
    
    @pytest.mark.asyncio
    async def test_validate_business_category(self, service):
        """Test business category validation."""
        result = await service.validate_business_category("cmrczn_tab1")
        assert result.is_valid is True
        
        result = await service.validate_business_category("invalid_code")
        assert result.is_valid is False
    
    @pytest.mark.asyncio
    async def test_search_business_categories(self, service):
        """Test searching business categories."""
        results = await service.search_business_categories("사업화")
        assert len(results) > 0
        assert any("사업화" in cat.name for cat in results)
        
        results = await service.search_business_categories("교육")
        assert len(results) > 0
        assert any("교육" in cat.name for cat in results)
    
    @pytest.mark.asyncio
    async def test_get_content_categories(self, service):
        """Test getting content categories."""
        categories = await service.get_content_categories()
        assert len(categories) == 3
        assert all(isinstance(cat, ContentCategoryCode) for cat in categories)
    
    @pytest.mark.asyncio
    async def test_get_content_category(self, service):
        """Test getting specific content category."""
        category = await service.get_content_category("notice_matr")
        assert category is not None
        assert category.code == "notice_matr"
        
        # Test invalid code
        invalid_category = await service.get_content_category("invalid_code")
        assert invalid_category is None
    
    @pytest.mark.asyncio
    async def test_validate_any_code(self, service):
        """Test unified code validation."""
        # Test business code
        result = await service.validate_any_code("cmrczn_tab1")
        assert result.is_valid is True
        
        # Test content code
        result = await service.validate_any_code("notice_matr")
        assert result.is_valid is True
        
        # Test invalid code
        result = await service.validate_any_code("invalid_code")
        assert result.is_valid is False
    
    @pytest.mark.asyncio
    async def test_detect_code_type(self, service):
        """Test code type detection."""
        assert await service.detect_code_type("cmrczn_tab1") == ClassificationCodeType.BUSINESS_CATEGORY.value
        assert await service.detect_code_type("notice_matr") == ClassificationCodeType.CONTENT_CATEGORY.value
        assert await service.detect_code_type("invalid_code") is None
    
    @pytest.mark.asyncio
    async def test_search_all_categories(self, service):
        """Test unified search."""
        request = ClassificationCodeSearchRequest(
            query="정책",
            limit=10
        )
        
        response = await service.search_all_categories(request)
        assert response.total_count >= 0
        assert response.query == "정책"
        assert response.search_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_all_valid_codes(self, service):
        """Test getting all valid codes."""
        codes = await service.get_all_valid_codes()
        assert ClassificationCodeType.BUSINESS_CATEGORY.value in codes
        assert ClassificationCodeType.CONTENT_CATEGORY.value in codes
    
    @pytest.mark.asyncio
    async def test_validate_batch(self, service):
        """Test batch validation."""
        codes = ["cmrczn_tab1", "notice_matr", "invalid_code"]
        results = await service.validate_batch(codes)
        
        assert len(results) == 3
        assert results["cmrczn_tab1"].is_valid is True
        assert results["notice_matr"].is_valid is True
        assert results["invalid_code"].is_valid is False
    
    @pytest.mark.asyncio
    async def test_get_classification_statistics(self, service):
        """Test getting statistics."""
        stats = await service.get_classification_statistics()
        assert isinstance(stats, ClassificationCodeStats)
        assert stats.total_business_categories == 9
        assert stats.total_content_categories == 3
    
    @pytest.mark.asyncio
    async def test_get_code_recommendations(self, service):
        """Test getting code recommendations."""
        recommendations = await service.get_code_recommendations("사업화 지원")
        assert len(recommendations) > 0
        assert any("사업화" in rec["name"] for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check."""
        health = await service.health_check()
        assert health["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in health
        assert "checks" in health
    
    def test_cache_management(self, service):
        """Test cache management."""
        # Clear cache should not raise errors
        service.clear_cache()
        
        # Cache should be empty after clearing
        assert len(service._cache) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])