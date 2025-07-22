"""
Data-related exception classes.

Handles data validation, transformation, and parsing errors.
"""

from typing import List, Dict, Any, Optional
from .api_exceptions import KoreanPublicAPIError


class DataValidationError(KoreanPublicAPIError):
    """Data validation error"""
    
    def __init__(
        self, 
        message: str = "Data validation failed",
        validation_errors: Optional[List[str]] = None,
        field_name: Optional[str] = None
    ):
        super().__init__(message)
        self.validation_errors = validation_errors or []
        self.field_name = field_name


class DataTransformationError(KoreanPublicAPIError):
    """Data transformation error"""
    
    def __init__(
        self, 
        message: str = "Data transformation failed",
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        original_data: Optional[Any] = None
    ):
        super().__init__(message)
        self.source_format = source_format
        self.target_format = target_format
        self.original_data = original_data


class DataParsingError(KoreanPublicAPIError):
    """Data parsing error"""
    
    def __init__(
        self, 
        message: str = "Data parsing failed",
        data_format: Optional[str] = None,
        parser_type: Optional[str] = None,
        raw_content: Optional[str] = None
    ):
        super().__init__(message)
        self.data_format = data_format
        self.parser_type = parser_type
        self.raw_content = raw_content[:1000] if raw_content else None  # Limit for logging


class DataSourceError(KoreanPublicAPIError):
    """Data source configuration or access error"""
    
    def __init__(
        self, 
        message: str = "Data source error",
        source_name: Optional[str] = None,
        source_type: Optional[str] = None
    ):
        super().__init__(message)
        self.source_name = source_name
        self.source_type = source_type