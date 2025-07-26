"""
Classification code models.

Defines Pydantic models for business category codes and content category codes.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from abc import ABC, abstractmethod

from .enums import BusinessCategory, ContentCategory


class ClassificationCodeBase(BaseModel, ABC):
    """
    Base class for all classification code models.
    
    Provides common fields and validation logic.
    """
    
    code: str = Field(..., description="Classification code")
    name: str = Field(..., description="Display name in Korean")
    description: str = Field(..., description="Detailed description")
    is_active: bool = Field(default=True, description="Whether the code is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @abstractmethod
    def validate_code_format(self) -> bool:
        """Validate the format of the classification code."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.dict()
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class BusinessCategoryCode(ClassificationCodeBase):
    """
    Business category code model for K-Startup support programs.
    
    Represents BIZ_CATEGORY_CD with detailed information about support program categories.
    """
    
    features: List[str] = Field(default_factory=list, description="Main features of this category")
    support_areas: List[str] = Field(default_factory=list, description="Areas of support provided")
    target_audience: List[str] = Field(default_factory=list, description="Target audience for this category")
    requirements: List[str] = Field(default_factory=list, description="Common requirements for programs")
    typical_duration: Optional[str] = Field(default=None, description="Typical program duration")
    funding_range: Optional[str] = Field(default=None, description="Typical funding range")
    success_metrics: List[str] = Field(default_factory=list, description="Success metrics for this category")
    related_categories: List[str] = Field(default_factory=list, description="Related business category codes")
    
    @validator('code')
    def validate_business_code(cls, v):
        """Validate business category code format."""
        if not BusinessCategory.is_valid_code(v):
            raise ValueError(f"Invalid business category code: {v}")
        return v
    
    def validate_code_format(self) -> bool:
        """Validate the format of the business category code."""
        return (
            self.code.startswith('cmrczn_tab') and
            len(self.code) == 11 and
            self.code[-1].isdigit() and
            '1' <= self.code[-1] <= '9'
        )
    
    @classmethod
    def from_enum(cls, business_category: BusinessCategory) -> 'BusinessCategoryCode':
        """Create BusinessCategoryCode from BusinessCategory enum."""
        code = business_category.value
        return cls(
            code=code,
            name=BusinessCategory.get_description(code),
            description=BusinessCategory.get_detailed_description(code),
            features=BusinessCategory.get_main_features(code)
        )
    
    @classmethod
    def get_all_categories(cls) -> List['BusinessCategoryCode']:
        """Get all business category codes."""
        return [cls.from_enum(category) for category in BusinessCategory]
    
    def get_category_summary(self) -> Dict[str, Any]:
        """Get a summary of the business category."""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "feature_count": len(self.features),
            "support_area_count": len(self.support_areas),
            "is_active": self.is_active
        }
    
    def add_feature(self, feature: str) -> None:
        """Add a feature to the category."""
        if feature not in self.features:
            self.features.append(feature)
            self.update_timestamp()
    
    def remove_feature(self, feature: str) -> bool:
        """Remove a feature from the category."""
        if feature in self.features:
            self.features.remove(feature)
            self.update_timestamp()
            return True
        return False
    
    def is_global_focused(self) -> bool:
        """Check if this category is focused on global/international support."""
        return self.code == BusinessCategory.GLOBAL.value or "글로벌" in self.name or "해외" in self.description
    
    def is_funding_related(self) -> bool:
        """Check if this category is related to funding/financial support."""
        funding_categories = [BusinessCategory.LOAN.value, BusinessCategory.COMMERCIALIZATION.value]
        return self.code in funding_categories or "자금" in self.description or "융자" in self.name


class ContentCategoryCode(ClassificationCodeBase):
    """
    Content category code model for K-Startup content information.
    
    Represents CLSS_CD with detailed information about content categories.
    """
    
    content_types: List[str] = Field(default_factory=list, description="Types of content in this category")
    typical_format: List[str] = Field(default_factory=list, description="Typical content formats")
    update_frequency: Optional[str] = Field(default=None, description="How often content is updated")
    target_readers: List[str] = Field(default_factory=list, description="Target readers for this content")
    information_source: List[str] = Field(default_factory=list, description="Typical information sources")
    relevance_keywords: List[str] = Field(default_factory=list, description="Keywords relevant to this category")
    related_categories: List[str] = Field(default_factory=list, description="Related content category codes")
    
    @validator('code')
    def validate_content_code(cls, v):
        """Validate content category code format."""
        if not ContentCategory.is_valid_code(v):
            raise ValueError(f"Invalid content category code: {v}")
        return v
    
    def validate_code_format(self) -> bool:
        """Validate the format of the content category code."""
        valid_codes = ContentCategory.get_all_codes()
        return self.code in valid_codes
    
    @classmethod
    def from_enum(cls, content_category: ContentCategory) -> 'ContentCategoryCode':
        """Create ContentCategoryCode from ContentCategory enum."""
        code = content_category.value
        return cls(
            code=code,
            name=ContentCategory.get_description(code),
            description=ContentCategory.get_detailed_description(code),
            content_types=ContentCategory.get_content_types(code)
        )
    
    @classmethod
    def get_all_categories(cls) -> List['ContentCategoryCode']:
        """Get all content category codes."""
        return [cls.from_enum(category) for category in ContentCategory]
    
    def get_category_summary(self) -> Dict[str, Any]:
        """Get a summary of the content category."""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "content_type_count": len(self.content_types),
            "format_count": len(self.typical_format),
            "is_active": self.is_active
        }
    
    def add_content_type(self, content_type: str) -> None:
        """Add a content type to the category."""
        if content_type not in self.content_types:
            self.content_types.append(content_type)
            self.update_timestamp()
    
    def remove_content_type(self, content_type: str) -> bool:
        """Remove a content type from the category."""
        if content_type in self.content_types:
            self.content_types.remove(content_type)
            self.update_timestamp()
            return True
        return False
    
    def is_policy_related(self) -> bool:
        """Check if this category is related to policy information."""
        return self.code == ContentCategory.POLICY_NOTICE.value or "정책" in self.name or "규제" in self.description
    
    def is_trend_analysis(self) -> bool:
        """Check if this category focuses on trend analysis."""
        return self.code == ContentCategory.ECOSYSTEM_TRENDS.value or "동향" in self.name or "트렌드" in self.description


class ClassificationCodeFilter(BaseModel):
    """
    Filter model for querying classification codes.
    """
    
    code_type: Optional[str] = Field(default=None, description="Type of classification code")
    codes: Optional[List[str]] = Field(default=None, description="Specific codes to filter by")
    is_active: Optional[bool] = Field(default=True, description="Filter by active status")
    name_contains: Optional[str] = Field(default=None, description="Filter by name containing text")
    description_contains: Optional[str] = Field(default=None, description="Filter by description containing text")
    has_features: Optional[bool] = Field(default=None, description="Filter by presence of features")
    created_after: Optional[datetime] = Field(default=None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(default=None, description="Filter by creation date")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClassificationCodeSearchRequest(BaseModel):
    """
    Search request model for classification codes.
    """
    
    query: str = Field(..., description="Search query string")
    code_type: Optional[str] = Field(default=None, description="Type of classification code to search")
    fields: List[str] = Field(default=["name", "description"], description="Fields to search in")
    exact_match: bool = Field(default=False, description="Whether to use exact matching")
    case_sensitive: bool = Field(default=False, description="Whether search is case sensitive")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class ClassificationCodeSearchResponse(BaseModel):
    """
    Search response model for classification codes.
    """
    
    query: str = Field(..., description="Original search query")
    total_count: int = Field(..., description="Total number of matching results")
    results: List[Union[BusinessCategoryCode, ContentCategoryCode]] = Field(..., description="Search results")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClassificationCodeValidationResult(BaseModel):
    """
    Validation result model for classification codes.
    """
    
    code: str = Field(..., description="The code that was validated")
    is_valid: bool = Field(..., description="Whether the code is valid")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    suggestions: List[str] = Field(default_factory=list, description="Suggested valid codes")
    code_type: Optional[str] = Field(default=None, description="Detected code type")
    
    def add_error(self, error: str) -> None:
        """Add a validation error."""
        if error not in self.validation_errors:
            self.validation_errors.append(error)
            self.is_valid = False
    
    def add_suggestion(self, suggestion: str) -> None:
        """Add a code suggestion."""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)


class ClassificationCodeStats(BaseModel):
    """
    Statistics model for classification codes.
    """
    
    total_business_categories: int = Field(..., description="Total number of business categories")
    total_content_categories: int = Field(..., description="Total number of content categories")
    active_business_categories: int = Field(..., description="Number of active business categories")
    active_content_categories: int = Field(..., description="Number of active content categories")
    most_used_business_categories: List[Dict[str, Any]] = Field(default_factory=list, description="Most used business categories")
    most_used_content_categories: List[Dict[str, Any]] = Field(default_factory=list, description="Most used content categories")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When statistics were last calculated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }