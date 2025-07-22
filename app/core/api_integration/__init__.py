"""
API Integration Layer for Korea Public Open API Platform.

This package provides a unified API integration layer that abstracts different
public data sources and provides consistent interfaces for consuming applications.

Key Components:
- API Gateway: Unified interface for all data sources
- Request/Response Transformation: Data format standardization
- API Versioning: Version compatibility and migration
- Rate Limiting: Request throttling and quota management
- Middleware: Request/response processing pipeline
"""

from .gateway import APIGateway, APIRequest, APIResponse
from .transformers import RequestTransformer, ResponseTransformer, DataTransformer
from .versioning import APIVersionManager, VersionCompatibility
from .rate_limiting import RateLimiter, RateLimit, QuotaManager
from .middleware import MiddlewareManager, Middleware

__all__ = [
    "APIGateway",
    "APIRequest", 
    "APIResponse",
    "RequestTransformer",
    "ResponseTransformer",
    "DataTransformer",
    "APIVersionManager",
    "VersionCompatibility",
    "RateLimiter",
    "RateLimit",
    "QuotaManager",
    "MiddlewareManager",
    "Middleware"
]