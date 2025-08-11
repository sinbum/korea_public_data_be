"""
Advanced data validation and sanitization with performance optimization.

Provides comprehensive input validation, data sanitization, and security checks
with caching and performance optimizations for improved API security.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
import html
import unicodedata
import hashlib
from functools import wraps, lru_cache

from pydantic import BaseModel, Field, validator
from pydantic.error_wrappers import ValidationError

from .cache import cache_get, cache_set

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"        # Basic type and format validation
    STANDARD = "standard"  # Standard validation with sanitization
    STRICT = "strict"      # Strict validation with security checks
    PARANOID = "paranoid"  # Maximum security validation


class SanitizationStrategy(Enum):
    """Data sanitization strategies"""
    NONE = "none"              # No sanitization
    BASIC_HTML = "basic_html"  # Basic HTML entity encoding
    STRICT_HTML = "strict_html" # Strip all HTML tags
    SQL_SAFE = "sql_safe"      # SQL injection prevention
    XSS_SAFE = "xss_safe"     # XSS prevention
    COMPREHENSIVE = "comprehensive"  # All sanitization methods


@dataclass
class ValidationRule:
    """Individual validation rule"""
    field_name: str
    rule_type: str
    parameters: Dict[str, Any]
    error_message: str
    required: bool = True
    sanitization: SanitizationStrategy = SanitizationStrategy.BASIC_HTML


@dataclass
class ValidationResult:
    """Validation result with details"""
    is_valid: bool
    sanitized_data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "is_valid": self.is_valid,
            "sanitized_data": self.sanitized_data,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time_ms": self.execution_time_ms
        }


class SecurityValidator:
    """Security-focused validation and threat detection"""
    
    def __init__(self):
        self._setup_patterns()
        self._load_threat_patterns()
    
    def _setup_patterns(self):
        """Setup regex patterns for security validation"""
        self.sql_injection_patterns = [
            re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)", re.IGNORECASE),
            re.compile(r"(\b(OR|AND)\s+\d+\s*=\s*\d+)", re.IGNORECASE),
            re.compile(r"(\-\-|\#|\/\*|\*\/)", re.IGNORECASE),
            re.compile(r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)\b)", re.IGNORECASE)
        ]
        
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL),
            re.compile(r"<embed[^>]*>", re.IGNORECASE),
            re.compile(r"<object[^>]*>.*?</object>", re.IGNORECASE | re.DOTALL)
        ]
        
        self.path_traversal_patterns = [
            re.compile(r"(\.\.\/|\.\.\\)"),
            re.compile(r"(%2e%2e%2f|%2e%2e%5c)", re.IGNORECASE),
            re.compile(r"(\/etc\/passwd|\/windows\/system32)", re.IGNORECASE)
        ]
        
        self.command_injection_patterns = [
            re.compile(r"[;&|`]"),
            re.compile(r"(\$\(|\$\{|`)", re.IGNORECASE),
            re.compile(r"(\b(curl|wget|nc|netcat|telnet|ssh)\b)", re.IGNORECASE)
        ]
        
        # Safe characters for different contexts
        self.safe_filename_chars = re.compile(r"[^a-zA-Z0-9._-]")
        self.safe_sql_chars = re.compile(r"[^a-zA-Z0-9_가-힣\s]")  # Korean characters included
        self.safe_html_chars = re.compile(r"[<>&\"']")
    
    def _load_threat_patterns(self):
        """Load additional threat patterns from cache or external source"""
        try:
            cached_patterns = cache_get("security_patterns")
            if cached_patterns:
                self.additional_patterns = cached_patterns
            else:
                # Default additional patterns
                self.additional_patterns = {
                    "suspicious_keywords": [
                        "admin", "root", "administrator", "system", "config",
                        "password", "passwd", "secret", "key", "token"
                    ],
                    "file_extensions": [
                        ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".jar"
                    ],
                    "ip_patterns": [
                        re.compile(r"(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)"),
                        re.compile(r"(\b[0-9a-fA-F]{1,4}(:[0-9a-fA-F]{1,4}){7}\b)")  # IPv6
                    ]
                }
                cache_set("security_patterns", self.additional_patterns, 3600)
        except Exception as e:
            logger.warning(f"Failed to load threat patterns: {e}")
            self.additional_patterns = {"suspicious_keywords": [], "file_extensions": [], "ip_patterns": []}
    
    def detect_sql_injection(self, value: str) -> Tuple[bool, List[str]]:
        """Detect SQL injection attempts"""
        threats = []
        
        for pattern in self.sql_injection_patterns:
            if pattern.search(value):
                threats.append(f"SQL injection pattern detected: {pattern.pattern}")
        
        return len(threats) > 0, threats
    
    def detect_xss(self, value: str) -> Tuple[bool, List[str]]:
        """Detect XSS attempts"""
        threats = []
        
        for pattern in self.xss_patterns:
            if pattern.search(value):
                threats.append(f"XSS pattern detected: {pattern.pattern}")
        
        return len(threats) > 0, threats
    
    def detect_path_traversal(self, value: str) -> Tuple[bool, List[str]]:
        """Detect path traversal attempts"""
        threats = []
        
        for pattern in self.path_traversal_patterns:
            if pattern.search(value):
                threats.append(f"Path traversal pattern detected: {pattern.pattern}")
        
        return len(threats) > 0, threats
    
    def detect_command_injection(self, value: str) -> Tuple[bool, List[str]]:
        """Detect command injection attempts"""
        threats = []
        
        for pattern in self.command_injection_patterns:
            if pattern.search(value):
                threats.append(f"Command injection pattern detected: {pattern.pattern}")
        
        return len(threats) > 0, threats
    
    def validate_security(self, value: str, level: ValidationLevel = ValidationLevel.STANDARD) -> Tuple[bool, List[str]]:
        """Comprehensive security validation"""
        all_threats = []
        
        if level == ValidationLevel.BASIC:
            return True, []
        
        # Check for SQL injection
        has_sql, sql_threats = self.detect_sql_injection(value)
        all_threats.extend(sql_threats)
        
        # Check for XSS
        has_xss, xss_threats = self.detect_xss(value)
        all_threats.extend(xss_threats)
        
        if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            # Check for path traversal
            has_path, path_threats = self.detect_path_traversal(value)
            all_threats.extend(path_threats)
            
            # Check for command injection
            has_cmd, cmd_threats = self.detect_command_injection(value)
            all_threats.extend(cmd_threats)
        
        if level == ValidationLevel.PARANOID:
            # Check for suspicious keywords
            for keyword in self.additional_patterns["suspicious_keywords"]:
                if keyword.lower() in value.lower():
                    all_threats.append(f"Suspicious keyword detected: {keyword}")
            
            # Check for suspicious file extensions
            for ext in self.additional_patterns["file_extensions"]:
                if ext.lower() in value.lower():
                    all_threats.append(f"Suspicious file extension detected: {ext}")
        
        return len(all_threats) == 0, all_threats


class DataSanitizer:
    """Data sanitization with multiple strategies"""
    
    def __init__(self):
        self.security_validator = SecurityValidator()
    
    @lru_cache(maxsize=1000)
    def sanitize_html_basic(self, value: str) -> str:
        """Basic HTML sanitization - encode entities"""
        if not isinstance(value, str):
            return str(value)
        
        return html.escape(value, quote=True)
    
    @lru_cache(maxsize=1000)
    def sanitize_html_strict(self, value: str) -> str:
        """Strict HTML sanitization - remove all tags"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', value)
        # Encode remaining entities
        return html.escape(clean, quote=True)
    
    @lru_cache(maxsize=1000)
    def sanitize_sql_safe(self, value: str) -> str:
        """SQL-safe sanitization"""
        if not isinstance(value, str):
            return str(value)
        
        # Replace dangerous characters
        safe_value = value.replace("'", "''")  # Escape single quotes
        safe_value = safe_value.replace(";", "")  # Remove semicolons
        safe_value = safe_value.replace("--", "")  # Remove comment markers
        safe_value = safe_value.replace("/*", "").replace("*/", "")  # Remove block comments
        
        return safe_value
    
    @lru_cache(maxsize=1000)
    def sanitize_xss_safe(self, value: str) -> str:
        """XSS-safe sanitization"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        # Remove javascript: URLs
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        # Remove event handlers
        value = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
        # Encode remaining HTML
        return html.escape(value, quote=True)
    
    def normalize_unicode(self, value: str) -> str:
        """Normalize Unicode characters"""
        if not isinstance(value, str):
            return str(value)
        
        # Normalize to NFC (Canonical Decomposition, followed by Canonical Composition)
        normalized = unicodedata.normalize('NFC', value)
        
        # Remove control characters except whitespace
        cleaned = ''.join(char for char in normalized 
                         if unicodedata.category(char)[0] != 'C' or char in ['\t', '\n', '\r'])
        
        return cleaned
    
    def sanitize_value(self, value: Any, strategy: SanitizationStrategy) -> Any:
        """Sanitize value based on strategy"""
        if not isinstance(value, str) or strategy == SanitizationStrategy.NONE:
            return value
        
        # Start with Unicode normalization
        sanitized = self.normalize_unicode(value)
        
        if strategy == SanitizationStrategy.BASIC_HTML:
            sanitized = self.sanitize_html_basic(sanitized)
        elif strategy == SanitizationStrategy.STRICT_HTML:
            sanitized = self.sanitize_html_strict(sanitized)
        elif strategy == SanitizationStrategy.SQL_SAFE:
            sanitized = self.sanitize_sql_safe(sanitized)
        elif strategy == SanitizationStrategy.XSS_SAFE:
            sanitized = self.sanitize_xss_safe(sanitized)
        elif strategy == SanitizationStrategy.COMPREHENSIVE:
            # Apply all sanitization methods
            sanitized = self.sanitize_html_strict(sanitized)
            sanitized = self.sanitize_sql_safe(sanitized)
            sanitized = self.sanitize_xss_safe(sanitized)
        
        return sanitized


class AdvancedValidator:
    """Advanced validation system with caching and performance optimization"""
    
    def __init__(self):
        self.security_validator = SecurityValidator()
        self.data_sanitizer = DataSanitizer()
        self.validation_cache: Dict[str, ValidationResult] = {}
        self.rule_sets: Dict[str, List[ValidationRule]] = {}
        self._setup_common_rules()
    
    def _setup_common_rules(self):
        """Setup common validation rule sets"""
        self.rule_sets["user_input"] = [
            ValidationRule("name", "string", {"min_length": 1, "max_length": 100}, "Name must be 1-100 characters"),
            ValidationRule("email", "email", {}, "Invalid email format"),
            ValidationRule("phone", "phone_kr", {}, "Invalid Korean phone number format"),
        ]
        
        self.rule_sets["api_params"] = [
            ValidationRule("page", "integer", {"min_value": 1, "max_value": 1000}, "Page must be 1-1000"),
            ValidationRule("limit", "integer", {"min_value": 1, "max_value": 100}, "Limit must be 1-100"),
            ValidationRule("search", "string", {"max_length": 200}, "Search term too long"),
        ]
        
        self.rule_sets["file_upload"] = [
            ValidationRule("filename", "filename", {"allowed_extensions": [".jpg", ".png", ".pdf", ".txt"]}, 
                          "Invalid filename or extension"),
            ValidationRule("content_type", "string", {"allowed_values": ["image/jpeg", "image/png", "application/pdf", "text/plain"]}, 
                          "Invalid content type"),
        ]
    
    def _generate_cache_key(self, data: Dict[str, Any], rule_set: str, level: ValidationLevel) -> str:
        """Generate cache key for validation result"""
        data_str = str(sorted(data.items()))
        cache_input = f"{data_str}:{rule_set}:{level.value}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _validate_string(self, value: Any, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate string type and constraints"""
        errors = []
        
        if not isinstance(value, str):
            errors.append("Value must be a string")
            return False, errors
        
        min_len = params.get("min_length", 0)
        max_len = params.get("max_length", float('inf'))
        
        if len(value) < min_len:
            errors.append(f"String must be at least {min_len} characters")
        
        if len(value) > max_len:
            errors.append(f"String must be at most {max_len} characters")
        
        allowed_values = params.get("allowed_values")
        if allowed_values and value not in allowed_values:
            errors.append(f"Value must be one of: {allowed_values}")
        
        pattern = params.get("pattern")
        if pattern and not re.match(pattern, value):
            errors.append("Value does not match required pattern")
        
        return len(errors) == 0, errors
    
    def _validate_integer(self, value: Any, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate integer type and constraints"""
        errors = []
        
        if not isinstance(value, (int, str)):
            errors.append("Value must be an integer")
            return False, errors
        
        try:
            int_value = int(value)
        except ValueError:
            errors.append("Value must be a valid integer")
            return False, errors
        
        min_val = params.get("min_value", float('-inf'))
        max_val = params.get("max_value", float('inf'))
        
        if int_value < min_val:
            errors.append(f"Value must be at least {min_val}")
        
        if int_value > max_val:
            errors.append(f"Value must be at most {max_val}")
        
        return len(errors) == 0, errors
    
    def _validate_email(self, value: Any, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate email format"""
        if not isinstance(value, str):
            return False, ["Email must be a string"]
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        if not email_pattern.match(value):
            return False, ["Invalid email format"]
        
        # Additional security check for email injection
        if any(char in value for char in ['\n', '\r', '\t']):
            return False, ["Email contains invalid characters"]
        
        return True, []
    
    def _validate_phone_kr(self, value: Any, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Korean phone number format"""
        if not isinstance(value, str):
            return False, ["Phone number must be a string"]
        
        # Korean phone number patterns
        patterns = [
            re.compile(r'^01[016789]-?\d{3,4}-?\d{4}$'),  # Mobile
            re.compile(r'^0\d{1,2}-?\d{3,4}-?\d{4}$'),   # Landline
        ]
        
        clean_phone = re.sub(r'[^\d]', '', value)
        
        if len(clean_phone) < 10 or len(clean_phone) > 11:
            return False, ["Invalid phone number length"]
        
        for pattern in patterns:
            if pattern.match(value):
                return True, []
        
        return False, ["Invalid Korean phone number format"]
    
    def _validate_filename(self, value: Any, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate filename and extension"""
        if not isinstance(value, str):
            return False, ["Filename must be a string"]
        
        errors = []
        
        # Check for path traversal
        if '..' in value or '/' in value or '\\' in value:
            errors.append("Filename contains invalid path characters")
        
        # Check length
        if len(value) > 255:
            errors.append("Filename too long (max 255 characters)")
        
        # Check allowed extensions
        allowed_extensions = params.get("allowed_extensions", [])
        if allowed_extensions:
            file_ext = '.' + value.split('.')[-1].lower() if '.' in value else ''
            if file_ext not in [ext.lower() for ext in allowed_extensions]:
                errors.append(f"File extension must be one of: {allowed_extensions}")
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in value for char in dangerous_chars):
            errors.append("Filename contains dangerous characters")
        
        return len(errors) == 0, errors
    
    def _validate_field(self, field_name: str, value: Any, rule: ValidationRule, 
                       level: ValidationLevel) -> Tuple[bool, List[str], List[str], Any]:
        """Validate a single field"""
        errors = []
        warnings = []
        sanitized_value = value
        
        # Check if field is required
        if rule.required and (value is None or value == ""):
            errors.append(f"Field '{field_name}' is required")
            return False, errors, warnings, sanitized_value
        
        # Skip validation if value is None/empty and not required
        if not rule.required and (value is None or value == ""):
            return True, errors, warnings, sanitized_value
        
        # Apply security validation first
        if isinstance(value, str) and level in [ValidationLevel.STANDARD, ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            is_secure, security_threats = self.security_validator.validate_security(value, level)
            if not is_secure:
                errors.extend(security_threats)
                if level == ValidationLevel.PARANOID:
                    # Block immediately on security threats in paranoid mode
                    return False, errors, warnings, sanitized_value
                else:
                    # Add as warnings in other modes
                    warnings.extend(security_threats)
        
        # Apply sanitization
        sanitized_value = self.data_sanitizer.sanitize_value(value, rule.sanitization)
        
        # Apply type-specific validation
        if rule.rule_type == "string":
            is_valid, field_errors = self._validate_string(sanitized_value, rule.parameters)
        elif rule.rule_type == "integer":
            is_valid, field_errors = self._validate_integer(sanitized_value, rule.parameters)
        elif rule.rule_type == "email":
            is_valid, field_errors = self._validate_email(sanitized_value, rule.parameters)
        elif rule.rule_type == "phone_kr":
            is_valid, field_errors = self._validate_phone_kr(sanitized_value, rule.parameters)
        elif rule.rule_type == "filename":
            is_valid, field_errors = self._validate_filename(sanitized_value, rule.parameters)
        else:
            is_valid, field_errors = True, []
        
        if not is_valid:
            errors.extend(field_errors)
        
        return is_valid, errors, warnings, sanitized_value
    
    def validate_data(self, data: Dict[str, Any], rule_set_name: str = "user_input", 
                     level: ValidationLevel = ValidationLevel.STANDARD,
                     use_cache: bool = True) -> ValidationResult:
        """Validate data against rule set"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(data, rule_set_name, level)
            if cache_key in self.validation_cache:
                cached_result = self.validation_cache[cache_key]
                logger.debug(f"Using cached validation result for {rule_set_name}")
                return cached_result
        
        # Get rule set
        rules = self.rule_sets.get(rule_set_name, [])
        if not rules:
            logger.warning(f"No rules found for rule set: {rule_set_name}")
        
        all_errors = []
        all_warnings = []
        sanitized_data = {}
        
        # Validate each field in the rule set
        for rule in rules:
            field_value = data.get(rule.field_name)
            is_valid, errors, warnings, sanitized_value = self._validate_field(
                rule.field_name, field_value, rule, level
            )
            
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            sanitized_data[rule.field_name] = sanitized_value
        
        # Include fields not in rules (with basic sanitization if string)
        for key, value in data.items():
            if key not in sanitized_data:
                if isinstance(value, str) and level != ValidationLevel.BASIC:
                    sanitized_data[key] = self.data_sanitizer.sanitize_value(value, SanitizationStrategy.BASIC_HTML)
                else:
                    sanitized_data[key] = value
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        result = ValidationResult(
            is_valid=len(all_errors) == 0,
            sanitized_data=sanitized_data,
            errors=all_errors,
            warnings=all_warnings,
            execution_time_ms=execution_time
        )
        
        # Cache result
        if use_cache:
            self.validation_cache[cache_key] = result
            # Limit cache size
            if len(self.validation_cache) > 1000:
                # Remove oldest 20% of entries
                keys_to_remove = list(self.validation_cache.keys())[:200]
                for key in keys_to_remove:
                    del self.validation_cache[key]
        
        return result
    
    def add_rule_set(self, name: str, rules: List[ValidationRule]):
        """Add a custom rule set"""
        self.rule_sets[name] = rules
        logger.info(f"Added rule set: {name} with {len(rules)} rules")
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "cache_size": len(self.validation_cache),
            "rule_sets": list(self.rule_sets.keys()),
            "total_rules": sum(len(rules) for rules in self.rule_sets.values())
        }


# Global validator instance
validator = AdvancedValidator()


# Convenience functions and decorators
def validate_request_data(data: Dict[str, Any], rule_set: str = "user_input", 
                         level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
    """Validate request data"""
    return validator.validate_data(data, rule_set, level)

def sanitize_string(value: str, strategy: SanitizationStrategy = SanitizationStrategy.BASIC_HTML) -> str:
    """Sanitize a string value"""
    return validator.data_sanitizer.sanitize_value(value, strategy)

def validate_with_rules(rules: List[ValidationRule], level: ValidationLevel = ValidationLevel.STANDARD):
    """Decorator for validating function parameters with custom rules"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate kwargs against rules
            result = validator.validate_data(kwargs, "custom", level)
            
            if not result.is_valid:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "message": "Validation failed",
                        "errors": result.errors,
                        "warnings": result.warnings
                    }
                )
            
            # Replace kwargs with sanitized data
            return func(*args, **result.sanitized_data)
        
        return wrapper
    return decorator

def security_check(level: ValidationLevel = ValidationLevel.STANDARD):
    """Decorator for security checking all string parameters"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            security_validator = SecurityValidator()
            
            for key, value in kwargs.items():
                if isinstance(value, str):
                    is_secure, threats = security_validator.validate_security(value, level)
                    if not is_secure and level == ValidationLevel.PARANOID:
                        from fastapi import HTTPException, status
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "message": "Security validation failed",
                                "threats": threats
                            }
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Export commonly used items
__all__ = [
    'ValidationLevel',
    'SanitizationStrategy', 
    'ValidationRule',
    'ValidationResult',
    'AdvancedValidator',
    'SecurityValidator',
    'DataSanitizer',
    'validate_request_data',
    'sanitize_string',
    'validate_with_rules',
    'security_check',
    'validator'
]