"""
Factory interfaces and implementations for creating service instances.

Implements Factory and Abstract Factory patterns for flexible object creation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, TypeVar, Generic, Optional, Any, List
from enum import Enum
import logging

from .base_api_client import BaseAPIClient, AuthenticationStrategy, APIKeyAuthStrategy
from .base_repository import BaseRepository
from .base_service import BaseService
from ..database import get_database

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataSourceType(Enum):
    """Supported data source types"""
    KSTARTUP = "kstartup"
    GOVERNMENT_DATA = "government_data"
    CUSTOM_API = "custom_api"


class DomainType(Enum):
    """Supported domain types"""
    ANNOUNCEMENTS = "announcements"
    CONTENTS = "contents"
    STATISTICS = "statistics"
    BUSINESSES = "businesses"


class FactoryError(Exception):
    """Factory creation error"""
    pass


class APIClientFactory(ABC):
    """Abstract factory for creating API clients"""
    
    @abstractmethod
    def create_client(
        self, 
        data_source_type: DataSourceType,
        config: Dict[str, Any]
    ) -> BaseAPIClient:
        """Create API client for specific data source"""
        pass


class RepositoryFactory(ABC):
    """Abstract factory for creating repositories"""
    
    @abstractmethod
    def create_repository(
        self,
        domain_type: DomainType,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseRepository:
        """Create repository for specific domain"""
        pass


class ServiceFactory(ABC):
    """Abstract factory for creating services"""
    
    @abstractmethod
    def create_service(
        self,
        domain_type: DomainType,
        repository: BaseRepository,
        api_client: Optional[BaseAPIClient] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseService:
        """Create service for specific domain"""
        pass


class DefaultAPIClientFactory(APIClientFactory):
    """Default implementation of API client factory"""
    
    def __init__(self):
        self._client_registry: Dict[DataSourceType, Type[BaseAPIClient]] = {}
        self._auth_strategies: Dict[DataSourceType, Type[AuthenticationStrategy]] = {}
    
    def register_client(
        self,
        data_source_type: DataSourceType,
        client_class: Type[BaseAPIClient],
        auth_strategy_class: Type[AuthenticationStrategy] = APIKeyAuthStrategy
    ):
        """Register API client for data source type"""
        self._client_registry[data_source_type] = client_class
        self._auth_strategies[data_source_type] = auth_strategy_class
    
    def create_client(
        self,
        data_source_type: DataSourceType,
        config: Dict[str, Any]
    ) -> BaseAPIClient:
        """Create API client for specific data source"""
        try:
            if data_source_type not in self._client_registry:
                raise FactoryError(f"No client registered for {data_source_type}")
            
            client_class = self._client_registry[data_source_type]
            auth_strategy_class = self._auth_strategies[data_source_type]
            
            # Extract configuration
            base_url = config.get("base_url")
            if not base_url:
                raise FactoryError("base_url is required in config")
            
            # Create authentication strategy
            auth_config = config.get("auth", {})
            if auth_strategy_class == APIKeyAuthStrategy:
                api_key = auth_config.get("api_key")
                key_param = auth_config.get("key_param", "serviceKey")
                auth_strategy = auth_strategy_class(api_key, key_param)
            else:
                auth_strategy = auth_strategy_class(**auth_config)
            
            # Create client
            client_config = {
                "base_url": base_url,
                "auth_strategy": auth_strategy,
                "timeout": config.get("timeout", 30),
                "max_retries": config.get("max_retries", 3)
            }
            
            return client_class(**client_config)
            
        except Exception as e:
            logger.error(f"Failed to create API client for {data_source_type}: {e}")
            raise FactoryError(f"API client creation failed: {e}")


class DefaultRepositoryFactory(RepositoryFactory):
    """Default implementation of repository factory"""
    
    def __init__(self):
        self._repository_registry: Dict[DomainType, Type[BaseRepository]] = {}
        self._collection_names: Dict[DomainType, str] = {
            DomainType.ANNOUNCEMENTS: "announcements",
            DomainType.CONTENTS: "contents",
            DomainType.STATISTICS: "statistics",
            DomainType.BUSINESSES: "businesses"
        }
    
    def register_repository(
        self,
        domain_type: DomainType,
        repository_class: Type[BaseRepository],
        collection_name: Optional[str] = None
    ):
        """Register repository for domain type"""
        self._repository_registry[domain_type] = repository_class
        if collection_name:
            self._collection_names[domain_type] = collection_name
    
    def create_repository(
        self,
        domain_type: DomainType,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseRepository:
        """Create repository for specific domain"""
        try:
            if domain_type not in self._repository_registry:
                raise FactoryError(f"No repository registered for {domain_type}")
            
            repository_class = self._repository_registry[domain_type]
            collection_name = self._collection_names[domain_type]
            
            # Get database instance
            db = get_database()
            if not db:
                raise FactoryError("Database connection not available")
            
            # Create repository
            return repository_class(db, collection_name)
            
        except Exception as e:
            logger.error(f"Failed to create repository for {domain_type}: {e}")
            raise FactoryError(f"Repository creation failed: {e}")


class DefaultServiceFactory(ServiceFactory):
    """Default implementation of service factory"""
    
    def __init__(self):
        self._service_registry: Dict[DomainType, Type[BaseService]] = {}
    
    def register_service(
        self,
        domain_type: DomainType,
        service_class: Type[BaseService]
    ):
        """Register service for domain type"""
        self._service_registry[domain_type] = service_class
    
    def create_service(
        self,
        domain_type: DomainType,
        repository: BaseRepository,
        api_client: Optional[BaseAPIClient] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseService:
        """Create service for specific domain"""
        try:
            if domain_type not in self._service_registry:
                raise FactoryError(f"No service registered for {domain_type}")
            
            service_class = self._service_registry[domain_type]
            
            # Create service
            service_config = {
                "repository": repository,
                "api_client": api_client
            }
            
            # Add additional config if provided
            if config:
                service_config.update(config)
            
            return service_class(**service_config)
            
        except Exception as e:
            logger.error(f"Failed to create service for {domain_type}: {e}")
            raise FactoryError(f"Service creation failed: {e}")


class ApplicationFactory:
    """
    Main application factory orchestrating all component creation.
    
    Implements Abstract Factory pattern for creating complete application stacks.
    """
    
    def __init__(
        self,
        api_client_factory: Optional[APIClientFactory] = None,
        repository_factory: Optional[RepositoryFactory] = None,
        service_factory: Optional[ServiceFactory] = None
    ):
        self.api_client_factory = api_client_factory or DefaultAPIClientFactory()
        self.repository_factory = repository_factory or DefaultRepositoryFactory()
        self.service_factory = service_factory or DefaultServiceFactory()
        
        self._data_source_configs: Dict[DataSourceType, Dict[str, Any]] = {}
    
    def configure_data_source(
        self,
        data_source_type: DataSourceType,
        config: Dict[str, Any]
    ):
        """Configure data source with connection details"""
        self._data_source_configs[data_source_type] = config
    
    def create_complete_service(
        self,
        domain_type: DomainType,
        data_source_type: Optional[DataSourceType] = None,
        service_config: Optional[Dict[str, Any]] = None
    ) -> BaseService:
        """
        Create complete service with repository and API client.
        
        This method orchestrates the creation of all required components.
        """
        try:
            # Create repository
            repository = self.repository_factory.create_repository(domain_type)
            
            # Create API client if data source is specified
            api_client = None
            if data_source_type and data_source_type in self._data_source_configs:
                api_client = self.api_client_factory.create_client(
                    data_source_type,
                    self._data_source_configs[data_source_type]
                )
            
            # Create service
            service = self.service_factory.create_service(
                domain_type,
                repository,
                api_client,
                service_config
            )
            
            return service
            
        except Exception as e:
            logger.error(f"Failed to create complete service for {domain_type}: {e}")
            raise FactoryError(f"Complete service creation failed: {e}")
    
    def get_available_data_sources(self) -> List[DataSourceType]:
        """Get list of configured data sources"""
        return list(self._data_source_configs.keys())
    
    def is_data_source_configured(self, data_source_type: DataSourceType) -> bool:
        """Check if data source is configured"""
        return data_source_type in self._data_source_configs


# Global application factory instance
_app_factory: Optional[ApplicationFactory] = None


def get_application_factory() -> ApplicationFactory:
    """Get global application factory instance"""
    global _app_factory
    if _app_factory is None:
        _app_factory = ApplicationFactory()
    return _app_factory


def configure_application_factory(
    api_client_factory: Optional[APIClientFactory] = None,
    repository_factory: Optional[RepositoryFactory] = None,
    service_factory: Optional[ServiceFactory] = None
) -> ApplicationFactory:
    """Configure global application factory"""
    global _app_factory
    _app_factory = ApplicationFactory(
        api_client_factory,
        repository_factory,
        service_factory
    )
    return _app_factory