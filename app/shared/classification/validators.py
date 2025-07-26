"""
Classification code validators.

Provides validation logic for business category codes and content category codes.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

from .enums import BusinessCategory, ContentCategory, ClassificationCodeType
from .models import ClassificationCodeValidationResult


class ClassificationValidator(ABC):
    """
    Abstract base class for classification code validators.
    """
    
    @abstractmethod
    def validate(self, code: str) -> ClassificationCodeValidationResult:
        """Validate a classification code."""
        pass
    
    @abstractmethod
    def get_suggestions(self, invalid_code: str) -> List[str]:
        """Get suggestions for an invalid code."""
        pass
    
    @abstractmethod
    def get_all_valid_codes(self) -> List[str]:
        """Get all valid codes for this validator."""
        pass


class BusinessCategoryValidator(ClassificationValidator):
    """
    Validator for business category codes (BIZ_CATEGORY_CD).
    
    Validates codes according to K-Startup API specification:
    - Format: cmrczn_tab[1-9]
    - Must be lowercase
    - Must be exactly 11 characters
    """
    
    def __init__(self):
        self.valid_codes = BusinessCategory.get_all_codes()
        self.code_pattern = re.compile(r'^cmrczn_tab[1-9]$')
    
    def validate(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate a business category code.
        
        Args:
            code: The code to validate
            
        Returns:
            ClassificationCodeValidationResult with validation details
        """
        result = ClassificationCodeValidationResult(
            code=code,
            is_valid=True,
            code_type=ClassificationCodeType.BUSINESS_CATEGORY.value
        )
        
        # Check if code is None or empty
        if not code:
            result.add_error("Code cannot be empty")
            return result
        
        # Check if code is a string
        if not isinstance(code, str):
            result.add_error(f"Code must be a string, got {type(code)}")
            return result
        
        # Check basic format
        if not self.code_pattern.match(code):
            result.add_error("Code must follow format 'cmrczn_tab[1-9]'")
            
            # Check common format issues
            if not code.startswith('cmrczn_tab'):
                result.add_error("Code must start with 'cmrczn_tab'")
            
            if code.startswith('cmrczn_tab') and len(code) == 11:
                last_char = code[-1]
                if not last_char.isdigit():
                    result.add_error("Code must end with a digit")
                elif not ('1' <= last_char <= '9'):
                    result.add_error("Code must end with a digit between 1-9")
        
        # Check if code exists in valid codes
        if code not in self.valid_codes:
            result.add_error(f"Code '{code}' is not a valid business category code")
            
            # Add suggestions
            suggestions = self.get_suggestions(code)
            for suggestion in suggestions:
                result.add_suggestion(suggestion)
        
        # Check case sensitivity
        if code != code.lower():
            result.add_error("Code must be lowercase")
            result.add_suggestion(code.lower())
        
        return result
    
    def get_suggestions(self, invalid_code: str) -> List[str]:
        """
        Get suggestions for an invalid business category code.
        
        Args:
            invalid_code: The invalid code
            
        Returns:
            List of suggested valid codes
        """
        suggestions = []
        
        if not isinstance(invalid_code, str):
            return self.valid_codes[:3]  # Return first 3 valid codes
        
        # Case insensitive match
        lower_code = invalid_code.lower()
        if lower_code in self.valid_codes:
            suggestions.append(lower_code)
        
        # Partial matches
        for valid_code in self.valid_codes:
            if valid_code in lower_code or lower_code in valid_code:
                suggestions.append(valid_code)
        
        # If starts with correct prefix but wrong number
        if lower_code.startswith('cmrczn_tab'):
            if len(lower_code) == 11:
                for i in range(1, 10):
                    candidate = f"cmrczn_tab{i}"
                    if candidate != lower_code and candidate not in suggestions:
                        suggestions.append(candidate)
        
        # Remove duplicates and limit
        suggestions = list(dict.fromkeys(suggestions))[:5]
        
        # If no good suggestions, return most common codes
        if not suggestions:
            suggestions = [
                BusinessCategory.COMMERCIALIZATION.value,
                BusinessCategory.STARTUP_EDUCATION.value,
                BusinessCategory.TECHNOLOGY_RND.value
            ]
        
        return suggestions
    
    def get_all_valid_codes(self) -> List[str]:
        """Get all valid business category codes."""
        return self.valid_codes.copy()
    
    def validate_multiple(self, codes: List[str]) -> Dict[str, ClassificationCodeValidationResult]:
        """
        Validate multiple business category codes.
        
        Args:
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping codes to validation results
        """
        results = {}
        for code in codes:
            results[code] = self.validate(code)
        return results
    
    def get_code_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a business category code.
        
        Args:
            code: The business category code
            
        Returns:
            Dictionary with code information or None if invalid
        """
        if not self.validate(code).is_valid:
            return None
        
        return {
            "code": code,
            "name": BusinessCategory.get_description(code),
            "description": BusinessCategory.get_detailed_description(code),
            "features": BusinessCategory.get_main_features(code),
            "is_valid": True
        }


class ContentCategoryValidator(ClassificationValidator):
    """
    Validator for content category codes (CLSS_CD).
    
    Validates codes according to K-Startup API specification:
    - Three specific codes: notice_matr, fnd_scs_case, kstartup_isse_trd
    - Must be lowercase
    - Must match exactly
    """
    
    def __init__(self):
        self.valid_codes = ContentCategory.get_all_codes()
    
    def validate(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate a content category code.
        
        Args:
            code: The code to validate
            
        Returns:
            ClassificationCodeValidationResult with validation details
        """
        result = ClassificationCodeValidationResult(
            code=code,
            is_valid=True,
            code_type=ClassificationCodeType.CONTENT_CATEGORY.value
        )
        
        # Check if code is None or empty
        if not code:
            result.add_error("Code cannot be empty")
            return result
        
        # Check if code is a string
        if not isinstance(code, str):
            result.add_error(f"Code must be a string, got {type(code)}")
            return result
        
        # Check if code exists in valid codes
        if code not in self.valid_codes:
            result.add_error(f"Code '{code}' is not a valid content category code")
            
            # Add suggestions
            suggestions = self.get_suggestions(code)
            for suggestion in suggestions:
                result.add_suggestion(suggestion)
        
        # Check case sensitivity
        if code != code.lower():
            result.add_error("Code must be lowercase")
            result.add_suggestion(code.lower())
        
        return result
    
    def get_suggestions(self, invalid_code: str) -> List[str]:
        """
        Get suggestions for an invalid content category code.
        
        Args:
            invalid_code: The invalid code
            
        Returns:
            List of suggested valid codes
        """
        suggestions = []
        
        if not isinstance(invalid_code, str):
            return self.valid_codes.copy()
        
        # Case insensitive match
        lower_code = invalid_code.lower()
        if lower_code in self.valid_codes:
            suggestions.append(lower_code)
        
        # Partial matches by keywords
        keyword_mapping = {
            'notice': ContentCategory.POLICY_NOTICE.value,
            'policy': ContentCategory.POLICY_NOTICE.value,
            '정책': ContentCategory.POLICY_NOTICE.value,
            '공지': ContentCategory.POLICY_NOTICE.value,
            'case': ContentCategory.SUCCESS_CASE.value,
            'success': ContentCategory.SUCCESS_CASE.value,
            '사례': ContentCategory.SUCCESS_CASE.value,
            '성공': ContentCategory.SUCCESS_CASE.value,
            'trend': ContentCategory.ECOSYSTEM_TRENDS.value,
            'issue': ContentCategory.ECOSYSTEM_TRENDS.value,
            'ecosystem': ContentCategory.ECOSYSTEM_TRENDS.value,
            '동향': ContentCategory.ECOSYSTEM_TRENDS.value,
            '트렌드': ContentCategory.ECOSYSTEM_TRENDS.value,
            '생태계': ContentCategory.ECOSYSTEM_TRENDS.value
        }
        
        for keyword, valid_code in keyword_mapping.items():
            if keyword.lower() in lower_code:
                if valid_code not in suggestions:
                    suggestions.append(valid_code)
        
        # Fuzzy matching for typos
        for valid_code in self.valid_codes:
            # Simple edit distance check
            if self._simple_edit_distance(lower_code, valid_code) <= 2:
                if valid_code not in suggestions:
                    suggestions.append(valid_code)
        
        # If no suggestions, return all valid codes
        if not suggestions:
            suggestions = self.valid_codes.copy()
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def get_all_valid_codes(self) -> List[str]:
        """Get all valid content category codes."""
        return self.valid_codes.copy()
    
    def validate_multiple(self, codes: List[str]) -> Dict[str, ClassificationCodeValidationResult]:
        """
        Validate multiple content category codes.
        
        Args:
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping codes to validation results
        """
        results = {}
        for code in codes:
            results[code] = self.validate(code)
        return results
    
    def get_code_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a content category code.
        
        Args:
            code: The content category code
            
        Returns:
            Dictionary with code information or None if invalid
        """
        if not self.validate(code).is_valid:
            return None
        
        return {
            "code": code,
            "name": ContentCategory.get_description(code),
            "description": ContentCategory.get_detailed_description(code),
            "content_types": ContentCategory.get_content_types(code),
            "is_valid": True
        }
    
    def _simple_edit_distance(self, s1: str, s2: str) -> int:
        """
        Calculate simple edit distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns: 
            Edit distance
        """
        if len(s1) < len(s2):
            return self._simple_edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class UnifiedClassificationValidator:
    """
    Unified validator for all classification codes.
    
    Automatically detects code type and uses appropriate validator.
    """
    
    def __init__(self):
        self.business_validator = BusinessCategoryValidator()
        self.content_validator = ContentCategoryValidator()
    
    def validate(self, code: str) -> ClassificationCodeValidationResult:
        """
        Validate any classification code by auto-detecting type.
        
        Args:
            code: The code to validate
            
        Returns:
            ClassificationCodeValidationResult with validation details
        """
        if not code or not isinstance(code, str):
            return ClassificationCodeValidationResult(
                code=code or "",
                is_valid=False,
                validation_errors=["Code cannot be empty or non-string"]
            )
        
        # Try business category first
        business_result = self.business_validator.validate(code)
        if business_result.is_valid:
            return business_result
        
        # Try content category
        content_result = self.content_validator.validate(code)
        if content_result.is_valid:
            return content_result
        
        # Neither worked, combine errors and suggestions
        combined_result = ClassificationCodeValidationResult(
            code=code,
            is_valid=False
        )
        
        # Add all errors
        for error in business_result.validation_errors:
            combined_result.add_error(f"Business category: {error}")
        for error in content_result.validation_errors:
            combined_result.add_error(f"Content category: {error}")
        
        # Add all suggestions
        for suggestion in business_result.suggestions:
            combined_result.add_suggestion(f"Business: {suggestion}")
        for suggestion in content_result.suggestions:
            combined_result.add_suggestion(f"Content: {suggestion}")
        
        return combined_result
    
    def detect_code_type(self, code: str) -> Optional[str]:
        """
        Detect the type of classification code.
        
        Args:
            code: The code to analyze
            
        Returns:
            Code type string or None if undetectable
        """
        if not code or not isinstance(code, str):
            return None
        
        if self.business_validator.validate(code).is_valid:
            return ClassificationCodeType.BUSINESS_CATEGORY.value
        
        if self.content_validator.validate(code).is_valid:
            return ClassificationCodeType.CONTENT_CATEGORY.value
        
        # Try to guess based on format
        if code.startswith('cmrczn_tab'):
            return ClassificationCodeType.BUSINESS_CATEGORY.value
        
        if any(keyword in code for keyword in ['notice', 'case', 'trend', 'issue']):
            return ClassificationCodeType.CONTENT_CATEGORY.value
        
        return None
    
    def get_all_valid_codes(self) -> Dict[str, List[str]]:
        """
        Get all valid codes organized by type.
        
        Returns:
            Dictionary mapping code types to lists of valid codes
        """
        return {
            ClassificationCodeType.BUSINESS_CATEGORY.value: self.business_validator.get_all_valid_codes(),
            ClassificationCodeType.CONTENT_CATEGORY.value: self.content_validator.get_all_valid_codes()
        }
    
    def validate_batch(self, codes: List[str]) -> Dict[str, ClassificationCodeValidationResult]:
        """
        Validate a batch of classification codes.
        
        Args:
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping codes to validation results
        """
        results = {}
        for code in codes:
            results[code] = self.validate(code)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about classification codes.
        
        Returns:
            Dictionary with code statistics
        """
        business_codes = self.business_validator.get_all_valid_codes()
        content_codes = self.content_validator.get_all_valid_codes()
        
        return {
            "total_codes": len(business_codes) + len(content_codes),
            "business_category_count": len(business_codes),
            "content_category_count": len(content_codes),
            "business_categories": business_codes,
            "content_categories": content_codes,
            "supported_types": [
                ClassificationCodeType.BUSINESS_CATEGORY.value,
                ClassificationCodeType.CONTENT_CATEGORY.value
            ]
        }