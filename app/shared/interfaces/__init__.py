"""
Service interface definitions for the Korea Public API platform.

Provides abstract base classes and protocols for domain services.
"""

from .base_service import BaseService, IBaseService
from .repository_interface import IRepository, IQueryableRepository
from .domain_services import (
    IAnnouncementService,
    IBusinessService,
    IContentService,
    IStatisticsService
)

__all__ = [
    # Base interfaces
    'BaseService',
    'IBaseService',
    'IRepository',
    'IQueryableRepository',
    
    # Domain service interfaces
    'IAnnouncementService',
    'IBusinessService', 
    'IContentService',
    'IStatisticsService'
]