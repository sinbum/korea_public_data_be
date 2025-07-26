"""
Classification services.

Provides business logic for managing classification codes including business categories and content categories.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from .models import (
    BusinessCategoryCode, ContentCategoryCode, ClassificationCodeBase,
    ClassificationCodeFilter, ClassificationCodeSearchRequest, ClassificationCodeSearchResponse,
    ClassificationCodeValidationResult, ClassificationCodeStats
)
from .validators import BusinessCategoryValidator, ContentCategoryValidator, UnifiedClassificationValidator
from .enums import BusinessCategory, ContentCategory, ClassificationCodeType

logger = logging.getLogger(__name__)


class ClassificationService:
    """
    Service for managing classification codes.
    
    Provides comprehensive functionality for business category codes and content category codes
    including validation, search, filtering, and statistics.
    """
    
    def __init__(self):
        self.business_validator = BusinessCategoryValidator()
        self.content_validator = ContentCategoryValidator()
        self.unified_validator = UnifiedClassificationValidator()
        
        # Cache for frequently accessed data
        self._cache = {}
        self._cache_ttl = timedelta(hours=1)
        self._last_cache_update = {}
    
    # Business Category Methods
    
    async def get_business_categories(
        self,
        filter_active: bool = True,
        include_details: bool = True
    ) -> List[BusinessCategoryCode]:
        """
        Get all business category codes.
        
        Args:
            filter_active: Whether to include only active categories
            include_details: Whether to include detailed information
            
        Returns:
            List of business category codes
        """
        cache_key = f"business_categories_{filter_active}_{include_details}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            categories = BusinessCategoryCode.get_all_categories()
            
            if filter_active:
                categories = [cat for cat in categories if cat.is_active]
            
            if not include_details:
                # Return minimal information
                categories = [
                    BusinessCategoryCode(
                        code=cat.code,
                        name=cat.name,
                        description=cat.description[:100] + "..." if len(cat.description) > 100 else cat.description
                    ) for cat in categories
                ]
            
            # Update cache
            self._update_cache(cache_key, categories)
            
            logger.info(f"Retrieved {len(categories)} business categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error retrieving business categories: {e}")
            return []
    
    async def get_business_category(self, code: str) -> Optional[BusinessCategoryCode]:
        """
        Get a specific business category by code.
        
        Args:
            code: The business category code
            
        Returns:
            BusinessCategoryCode or None if not found
        """
        try:
            validation_result = self.business_validator.validate(code)
            if not validation_result.is_valid:
                logger.warning(f"Invalid business category code: {code}")
                return None
            
            # Try to find from enum
            try:
                business_category = BusinessCategory(code)
                return BusinessCategoryCode.from_enum(business_category)
            except ValueError:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving business category {code}: {e}")
            return None
    
    async def validate_business_category(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate a business category code.
        
        Args:
            code: The code to validate
            
        Returns:
            Validation result with details
        """
        try:
            return self.business_validator.validate(code)
        except Exception as e:
            logger.error(f"Error validating business category code {code}: {e}")
            return ClassificationCodeValidationResult(
                code=code,
                is_valid=False,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    async def search_business_categories(
        self,
        query: str,
        search_fields: List[str] = None,
        limit: int = 10
    ) -> List[BusinessCategoryCode]:
        """
        Search business categories by query.
        
        Args:
            query: Search query
            search_fields: Fields to search in (name, description, features)
            limit: Maximum number of results
            
        Returns:
            List of matching business categories
        """
        if search_fields is None:
            search_fields = ["name", "description", "features"]
        
        try:
            all_categories = await self.get_business_categories()
            results = []
            query_lower = query.lower()
            
            for category in all_categories:
                match_score = 0
                
                # Search in name
                if "name" in search_fields and query_lower in category.name.lower():
                    match_score += 10
                
                # Search in description
                if "description" in search_fields and query_lower in category.description.lower():
                    match_score += 5
                
                # Search in features
                if "features" in search_fields:
                    for feature in category.features:
                        if query_lower in feature.lower():
                            match_score += 3
                            break
                
                if match_score > 0:
                    results.append((category, match_score))
            
            # Sort by match score and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            return [category for category, _ in results[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching business categories: {e}")
            return []
    
    # Content Category Methods
    
    async def get_content_categories(
        self,
        filter_active: bool = True,
        include_details: bool = True
    ) -> List[ContentCategoryCode]:
        """
        Get all content category codes.
        
        Args:
            filter_active: Whether to include only active categories
            include_details: Whether to include detailed information
            
        Returns:
            List of content category codes
        """
        cache_key = f"content_categories_{filter_active}_{include_details}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            categories = ContentCategoryCode.get_all_categories()
            
            if filter_active:
                categories = [cat for cat in categories if cat.is_active]
            
            if not include_details:
                # Return minimal information
                categories = [
                    ContentCategoryCode(
                        code=cat.code,
                        name=cat.name,
                        description=cat.description[:100] + "..." if len(cat.description) > 100 else cat.description
                    ) for cat in categories
                ]
            
            # Update cache
            self._update_cache(cache_key, categories)
            
            logger.info(f"Retrieved {len(categories)} content categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error retrieving content categories: {e}")
            return []
    
    async def get_content_category(self, code: str) -> Optional[ContentCategoryCode]:
        """
        Get a specific content category by code.
        
        Args:
            code: The content category code
            
        Returns:
            ContentCategoryCode or None if not found
        """
        try:
            validation_result = self.content_validator.validate(code)
            if not validation_result.is_valid:
                logger.warning(f"Invalid content category code: {code}")
                return None
            
            # Try to find from enum
            try:
                content_category = ContentCategory(code)
                return ContentCategoryCode.from_enum(content_category)
            except ValueError:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving content category {code}: {e}")
            return None
    
    async def validate_content_category(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate a content category code.
        
        Args:
            code: The code to validate
            
        Returns:
            Validation result with details
        """
        try:
            return self.content_validator.validate(code)
        except Exception as e:
            logger.error(f"Error validating content category code {code}: {e}")
            return ClassificationCodeValidationResult(
                code=code,
                is_valid=False,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    async def search_content_categories(
        self,
        query: str,
        search_fields: List[str] = None,
        limit: int = 10
    ) -> List[ContentCategoryCode]:
        """
        Search content categories by query.
        
        Args:
            query: Search query
            search_fields: Fields to search in (name, description, content_types)
            limit: Maximum number of results
            
        Returns:
            List of matching content categories
        """
        if search_fields is None:
            search_fields = ["name", "description", "content_types"]
        
        try:
            all_categories = await self.get_content_categories()
            results = []
            query_lower = query.lower()
            
            for category in all_categories:
                match_score = 0
                
                # Search in name
                if "name" in search_fields and query_lower in category.name.lower():
                    match_score += 10
                
                # Search in description
                if "description" in search_fields and query_lower in category.description.lower():
                    match_score += 5
                
                # Search in content types
                if "content_types" in search_fields:
                    for content_type in category.content_types:
                        if query_lower in content_type.lower():
                            match_score += 3
                            break
                
                if match_score > 0:
                    results.append((category, match_score))
            
            # Sort by match score and return top results
            results.sort(key=lambda x: x[1], reverse=True)
            return [category for category, _ in results[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching content categories: {e}")
            return []
    
    # Unified Methods
    
    async def validate_any_code(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate any classification code (auto-detect type).
        
        Args:
            code: The code to validate
            
        Returns:
            Validation result with details
        """
        try:
            return self.unified_validator.validate(code)
        except Exception as e:
            logger.error(f"Error validating code {code}: {e}")
            return ClassificationCodeValidationResult(
                code=code,
                is_valid=False,
                validation_errors=[f"Validation error: {str(e)}"]
            )
    
    async def detect_code_type(self, code: str) -> Optional[str]:
        """
        Detect the type of a classification code.
        
        Args:
            code: The code to analyze
            
        Returns:
            Code type string or None if undetectable
        """
        try:
            return self.unified_validator.detect_code_type(code)
        except Exception as e:
            logger.error(f"Error detecting code type for {code}: {e}")
            return None
    
    async def search_all_categories(
        self,
        request: ClassificationCodeSearchRequest
    ) -> ClassificationCodeSearchResponse:
        """
        Search across all classification categories.
        
        Args:
            request: Search request with parameters
            
        Returns:
            Search response with results
        """
        start_time = datetime.utcnow()
        
        try:
            results = []
            
            # Search business categories if no type specified or type matches
            if not request.code_type or request.code_type == ClassificationCodeType.BUSINESS_CATEGORY.value:
                business_results = await self.search_business_categories(
                    request.query,
                    request.fields,
                    request.limit
                )
                results.extend(business_results)
            
            # Search content categories if no type specified or type matches
            if not request.code_type or request.code_type == ClassificationCodeType.CONTENT_CATEGORY.value:
                content_results = await self.search_content_categories(
                    request.query,
                    request.fields,
                    request.limit
                )
                results.extend(content_results)
            
            # Apply offset and limit
            total_count = len(results)
            results = results[request.offset:request.offset + request.limit]
            
            # Calculate search time
            end_time = datetime.utcnow()
            search_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ClassificationCodeSearchResponse(
                query=request.query,
                total_count=total_count,
                results=results,
                filters_applied={
                    "code_type": request.code_type,
                    "fields": request.fields,
                    "exact_match": request.exact_match,
                    "case_sensitive": request.case_sensitive
                },
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            
            # Calculate search time even for errors
            end_time = datetime.utcnow()
            search_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ClassificationCodeSearchResponse(
                query=request.query,
                total_count=0,
                results=[],
                filters_applied={},
                search_time_ms=search_time_ms
            )
    
    async def get_all_valid_codes(self) -> Dict[str, List[str]]:
        """
        Get all valid classification codes organized by type.
        
        Returns:
            Dictionary mapping code types to lists of valid codes
        """
        try:
            return self.unified_validator.get_all_valid_codes()
        except Exception as e:
            logger.error(f"Error getting all valid codes: {e}")
            return {}
    
    async def validate_batch(self, codes: List[str]) -> Dict[str, ClassificationCodeValidationResult]:
        """
        Validate multiple classification codes.
        
        Args:
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping codes to validation results
        """
        try:
            return self.unified_validator.validate_batch(codes)
        except Exception as e:
            logger.error(f"Error in batch validation: {e}")
            return {code: ClassificationCodeValidationResult(
                code=code,
                is_valid=False,
                validation_errors=[f"Batch validation error: {str(e)}"]
            ) for code in codes}
    
    # Statistics and Analytics
    
    async def get_classification_statistics(self) -> ClassificationCodeStats:
        """
        Get statistics about classification codes.
        
        Returns:
            Statistics about all classification codes
        """
        try:
            business_categories = await self.get_business_categories(filter_active=False)
            content_categories = await self.get_content_categories(filter_active=False)
            
            active_business = len([cat for cat in business_categories if cat.is_active])
            active_content = len([cat for cat in content_categories if cat.is_active])
            
            # Mock usage statistics (in real implementation, this would come from usage logs)
            most_used_business = [
                {"code": BusinessCategory.COMMERCIALIZATION.value, "usage_count": 150, "name": "사업화"},
                {"code": BusinessCategory.STARTUP_EDUCATION.value, "usage_count": 120, "name": "창업교육"},
                {"code": BusinessCategory.TECHNOLOGY_RND.value, "usage_count": 100, "name": "기술개발 R&D"}
            ]
            
            most_used_content = [
                {"code": ContentCategory.SUCCESS_CASE.value, "usage_count": 80, "name": "창업우수사례"},
                {"code": ContentCategory.POLICY_NOTICE.value, "usage_count": 75, "name": "정책 및 규제정보"},
                {"code": ContentCategory.ECOSYSTEM_TRENDS.value, "usage_count": 60, "name": "생태계 이슈, 동향"}
            ]
            
            return ClassificationCodeStats(
                total_business_categories=len(business_categories),
                total_content_categories=len(content_categories),
                active_business_categories=active_business,
                active_content_categories=active_content,
                most_used_business_categories=most_used_business,
                most_used_content_categories=most_used_content
            )
            
        except Exception as e:
            logger.error(f"Error getting classification statistics: {e}")
            return ClassificationCodeStats(
                total_business_categories=0,
                total_content_categories=0,
                active_business_categories=0,
                active_content_categories=0
            )
    
    async def get_code_recommendations(
        self,
        context: str,
        code_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get code recommendations based on context.
        
        Args:
            context: Context description for recommendations
            code_type: Type of codes to recommend (optional)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended codes with scores
        """
        try:
            recommendations = []
            context_lower = context.lower()
            
            # Keyword mapping for business categories
            business_keywords = {
                BusinessCategory.COMMERCIALIZATION.value: ["사업화", "상용화", "판로", "마케팅", "상품화"],
                BusinessCategory.STARTUP_EDUCATION.value: ["교육", "강의", "학습", "과정", "커리큘럼"],
                BusinessCategory.FACILITIES_SPACE_INCUBATION.value: ["공간", "시설", "사무실", "보육", "인큐베이터"],
                BusinessCategory.MENTORING_CONSULTING.value: ["멘토링", "컨설팅", "자문", "상담", "코칭"],
                BusinessCategory.EVENTS_NETWORKING.value: ["행사", "이벤트", "네트워킹", "경진대회", "박람회"],
                BusinessCategory.TECHNOLOGY_RND.value: ["기술", "연구", "개발", "R&D", "혁신"],
                BusinessCategory.LOAN.value: ["융자", "대출", "자금", "투자", "금융"],
                BusinessCategory.HUMAN_RESOURCES.value: ["인력", "채용", "인사", "직원", "팀"],
                BusinessCategory.GLOBAL.value: ["글로벌", "해외", "수출", "국제", "해외진출"]
            }
            
            # Content category keywords  
            content_keywords = {
                ContentCategory.POLICY_NOTICE.value: ["정책", "규제", "공지", "법령", "제도"],
                ContentCategory.SUCCESS_CASE.value: ["사례", "성공", "스토리", "우수", "벤치마킹"],
                ContentCategory.ECOSYSTEM_TRENDS.value: ["동향", "트렌드", "이슈", "분석", "시장"]
            }
            
            # Score business categories
            if not code_type or code_type == ClassificationCodeType.BUSINESS_CATEGORY.value:
                for code, keywords in business_keywords.items():
                    score = sum(1 for keyword in keywords if keyword in context_lower)
                    if score > 0:
                        recommendations.append({
                            "code": code,
                            "name": BusinessCategory.get_description(code),
                            "type": ClassificationCodeType.BUSINESS_CATEGORY.value,
                            "score": score,
                            "matched_keywords": [kw for kw in keywords if kw in context_lower]
                        })
            
            # Score content categories
            if not code_type or code_type == ClassificationCodeType.CONTENT_CATEGORY.value:
                for code, keywords in content_keywords.items():
                    score = sum(1 for keyword in keywords if keyword in context_lower)
                    if score > 0:
                        recommendations.append({
                            "code": code,
                            "name": ContentCategory.get_description(code),
                            "type": ClassificationCodeType.CONTENT_CATEGORY.value,
                            "score": score,
                            "matched_keywords": [kw for kw in keywords if kw in context_lower]
                        })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting code recommendations: {e}")
            return []
    
    # Utility Methods
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid."""
        if cache_key not in self._cache:
            return False
        
        if cache_key not in self._last_cache_update:
            return False
        
        return datetime.utcnow() - self._last_cache_update[cache_key] < self._cache_ttl
    
    def _update_cache(self, cache_key: str, data: Any) -> None:
        """Update cache entry."""
        self._cache[cache_key] = data
        self._last_cache_update[cache_key] = datetime.utcnow()
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._last_cache_update.clear()
        logger.info("Classification service cache cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the classification service.
        
        Returns:
            Health check results
        """
        try:
            # Test validation
            business_test = await self.validate_business_category(BusinessCategory.COMMERCIALIZATION.value)
            content_test = await self.validate_content_category(ContentCategory.SUCCESS_CASE.value)
            
            # Test retrieval
            business_categories = await self.get_business_categories()
            content_categories = await self.get_content_categories()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "business_validation": business_test.is_valid,
                    "content_validation": content_test.is_valid,
                    "business_retrieval": len(business_categories) > 0,
                    "content_retrieval": len(content_categories) > 0
                },
                "cache_stats": {
                    "entries": len(self._cache),
                    "last_updated": max(self._last_cache_update.values()).isoformat() if self._last_cache_update else None
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }