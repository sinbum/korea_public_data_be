"""
Core interfaces and abstract base classes for the application.

This module provides the foundation for implementing SOLID principles
and design patterns throughout the application.
"""

from .base_api_client import BaseAPIClient, APIClientError
from .base_repository import BaseRepository, RepositoryError
from .base_service import BaseService, ServiceError
from .factories import APIClientFactory, RepositoryFactory, ServiceFactory

__all__ = [
    "BaseAPIClient",
    "APIClientError", 
    "BaseRepository",
    "RepositoryError",
    "BaseService",
    "ServiceError",
    "APIClientFactory",
    "RepositoryFactory", 
    "ServiceFactory",
]