"""
Data Source Factory - creates data source instances from plugins and configurations.

Provides factory pattern implementation for creating and configuring
data source components (API clients, repositories, services) from plugins.
"""

from typing import Dict, List, Optional, Any, Type, Tuple
import logging
from datetime import datetime

from ..interfaces.base_api_client import BaseAPIClient
from ..interfaces.base_repository import BaseRepository
from ..interfaces.base_service import BaseService
from ..plugins.base import DataSourcePlugin
from ..plugins.manager import PluginManager, get_plugin_manager
from ..dependency_injection.container import DIContainer
from .registry import DataSourceRegistry, DataSourceInfo, DataSourceStatus, get_data_source_registry

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """
    Factory for creating data source instances from plugins.
    
    Manages the creation and configuration of data source components
    including API clients, repositories, and services.
    """
    
    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        registry: Optional[DataSourceRegistry] = None,
        di_container: Optional[DIContainer] = None
    ):
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.registry = registry or get_data_source_registry()
        self.di_container = di_container
        
        # Cache for created instances
        self._api_client_cache: Dict[str, BaseAPIClient] = {}
        self._repository_cache: Dict[str, BaseRepository] = {}
        self._service_cache: Dict[str, BaseService] = {}
        
        # Factory statistics
        self._creation_stats = {
            "total_clients_created": 0,
            "total_repositories_created": 0,
            "total_services_created": 0,
            "creation_errors": 0,
            "last_creation_time": None
        }
    
    def create_api_client(
        self,
        data_source_name: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[BaseAPIClient]:
        """
        Create an API client for a data source.
        
        Args:
            data_source_name: Name of the data source
            config: Optional configuration override
            use_cache: Whether to use cached instance
            
        Returns:
            API client instance or None if creation failed
        """
        try:
            # Check cache first
            if use_cache and data_source_name in self._api_client_cache:
                logger.debug(f"Returning cached API client for {data_source_name}")
                return self._api_client_cache[data_source_name]
            
            # Get data source info
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                logger.error(f"Data source not found: {data_source_name}")
                return None
            
            # Get API client class
            api_client_class = data_source_info.api_client_class
            if not api_client_class:
                logger.error(f"No API client class for data source: {data_source_name}")
                return None
            
            # Prepare configuration
            client_config = self._prepare_config(data_source_info, config)
            
            # Create API client instance
            api_client = api_client_class(config=client_config)
            
            # Initialize if needed
            if hasattr(api_client, 'initialize'):
                if not api_client.initialize():
                    logger.error(f"Failed to initialize API client for {data_source_name}")
                    return None
            
            # Cache the instance
            if use_cache:
                self._api_client_cache[data_source_name] = api_client
            
            # Update statistics
            self._creation_stats["total_clients_created"] += 1
            self._creation_stats["last_creation_time"] = datetime.utcnow()
            
            # Update data source status
            self.registry.update_data_source_status(data_source_name, DataSourceStatus.ACTIVE)
            
            logger.info(f"Created API client for data source: {data_source_name}")
            return api_client
            
        except Exception as e:
            logger.error(f"Failed to create API client for {data_source_name}: {e}")
            self._creation_stats["creation_errors"] += 1
            self.registry.update_data_source_status(
                data_source_name, 
                DataSourceStatus.ERROR, 
                f"Failed to create API client: {e}"
            )
            return None
    
    def create_repository(
        self,
        data_source_name: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[BaseRepository]:
        """
        Create a repository for a data source.
        
        Args:
            data_source_name: Name of the data source
            config: Optional configuration override
            use_cache: Whether to use cached instance
            
        Returns:
            Repository instance or None if creation failed
        """
        try:
            # Check cache first
            if use_cache and data_source_name in self._repository_cache:
                logger.debug(f"Returning cached repository for {data_source_name}")
                return self._repository_cache[data_source_name]
            
            # Get data source info
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                logger.error(f"Data source not found: {data_source_name}")
                return None
            
            # Get repository class
            repository_class = data_source_info.repository_class
            if not repository_class:
                logger.error(f"No repository class for data source: {data_source_name}")
                return None
            
            # Create repository instance
            repository = repository_class()
            
            # Initialize if needed
            if hasattr(repository, 'initialize'):
                repo_config = self._prepare_config(data_source_info, config)
                if not repository.initialize(repo_config):
                    logger.error(f"Failed to initialize repository for {data_source_name}")
                    return None
            
            # Cache the instance
            if use_cache:
                self._repository_cache[data_source_name] = repository
            
            # Update statistics
            self._creation_stats["total_repositories_created"] += 1
            self._creation_stats["last_creation_time"] = datetime.utcnow()
            
            logger.info(f"Created repository for data source: {data_source_name}")
            return repository
            
        except Exception as e:
            logger.error(f"Failed to create repository for {data_source_name}: {e}")
            self._creation_stats["creation_errors"] += 1
            return None
    
    def create_service(
        self,
        data_source_name: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[BaseService]:
        """
        Create a service for a data source.
        
        Args:
            data_source_name: Name of the data source
            config: Optional configuration override
            use_cache: Whether to use cached instance
            
        Returns:
            Service instance or None if creation failed
        """
        try:
            # Check cache first
            if use_cache and data_source_name in self._service_cache:
                logger.debug(f"Returning cached service for {data_source_name}")
                return self._service_cache[data_source_name]
            
            # Get data source info
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                logger.error(f"Data source not found: {data_source_name}")
                return None
            
            # Get service class
            service_class = data_source_info.service_class
            if not service_class:
                logger.error(f"No service class for data source: {data_source_name}")
                return None
            
            # Create dependencies
            api_client = self.create_api_client(data_source_name, config, use_cache)
            repository = self.create_repository(data_source_name, config, use_cache)
            
            if not api_client or not repository:
                logger.error(f"Failed to create dependencies for service: {data_source_name}")
                return None
            
            # Create service instance
            service = service_class(api_client=api_client, repository=repository)
            
            # Initialize if needed
            if hasattr(service, 'initialize'):
                service_config = self._prepare_config(data_source_info, config)
                if not service.initialize(service_config):
                    logger.error(f"Failed to initialize service for {data_source_name}")
                    return None
            
            # Cache the instance
            if use_cache:
                self._service_cache[data_source_name] = service
            
            # Register with DI container if available
            if self.di_container:
                self.di_container.register_instance(f"{data_source_name}_service", service)
            
            # Update statistics
            self._creation_stats["total_services_created"] += 1
            self._creation_stats["last_creation_time"] = datetime.utcnow()
            
            logger.info(f"Created service for data source: {data_source_name}")
            return service
            
        except Exception as e:
            logger.error(f"Failed to create service for {data_source_name}: {e}")
            self._creation_stats["creation_errors"] += 1
            return None
    
    def create_full_stack(
        self,
        data_source_name: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[Tuple[BaseAPIClient, BaseRepository, BaseService]]:
        """
        Create complete data source stack (client, repository, service).
        
        Args:
            data_source_name: Name of the data source
            config: Optional configuration override
            use_cache: Whether to use cached instances
            
        Returns:
            Tuple of (client, repository, service) or None if creation failed
        """
        try:
            api_client = self.create_api_client(data_source_name, config, use_cache)
            repository = self.create_repository(data_source_name, config, use_cache)
            service = self.create_service(data_source_name, config, use_cache)
            
            if not all([api_client, repository, service]):
                logger.error(f"Failed to create complete stack for {data_source_name}")
                return None
            
            logger.info(f"Created complete data source stack for: {data_source_name}")
            return api_client, repository, service
            
        except Exception as e:
            logger.error(f"Failed to create full stack for {data_source_name}: {e}")
            return None
    
    def create_from_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[BaseAPIClient, BaseRepository, BaseService]]:
        """
        Create data source components directly from a plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: Optional configuration
            
        Returns:
            Tuple of (client, repository, service) or None if creation failed
        """
        try:
            if not self.plugin_manager:
                logger.error("Plugin manager not available")
                return None
            
            # Get plugin instance
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin or not isinstance(plugin, DataSourcePlugin):
                logger.error(f"Data source plugin not found or invalid: {plugin_name}")
                return None
            
            # Get component classes
            api_client_class = plugin.get_api_client_class()
            repository_class = plugin.get_repository_class()
            service_class = plugin.get_service_class()
            
            # Prepare configuration
            plugin_config = config or plugin.get_metadata().default_config
            
            # Create instances
            api_client = api_client_class(config=plugin_config)
            repository = repository_class()
            service = service_class(api_client=api_client, repository=repository)
            
            # Initialize components
            if hasattr(api_client, 'initialize'):
                api_client.initialize()
            
            if hasattr(repository, 'initialize'):
                repository.initialize(plugin_config)
            
            if hasattr(service, 'initialize'):
                service.initialize(plugin_config)
            
            logger.info(f"Created data source components from plugin: {plugin_name}")
            return api_client, repository, service
            
        except Exception as e:
            logger.error(f"Failed to create components from plugin {plugin_name}: {e}")
            return None
    
    def register_data_source_from_plugin(self, plugin: DataSourcePlugin) -> bool:
        """
        Register a data source from a plugin and create components.
        
        Args:
            plugin: Data source plugin instance
            
        Returns:
            True if registration and creation successful
        """
        try:
            # Register data source in registry
            if not self.registry.register_from_plugin(plugin):
                return False
            
            # Create initial components to validate
            metadata = plugin.get_metadata()
            components = self.create_from_plugin(metadata.name)
            
            if not components:
                # Rollback registration
                self.registry.unregister_data_source(metadata.name)
                return False
            
            logger.info(f"Successfully registered and created data source from plugin: {metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register data source from plugin: {e}")
            return False
    
    def clear_cache(self, data_source_name: Optional[str] = None):
        """
        Clear cached instances.
        
        Args:
            data_source_name: Specific data source to clear (all if None)
        """
        if data_source_name:
            self._api_client_cache.pop(data_source_name, None)
            self._repository_cache.pop(data_source_name, None)
            self._service_cache.pop(data_source_name, None)
            logger.info(f"Cleared cache for data source: {data_source_name}")
        else:
            self._api_client_cache.clear()
            self._repository_cache.clear()
            self._service_cache.clear()
            logger.info("Cleared all data source caches")
    
    def get_cached_instances(self, data_source_name: str) -> Dict[str, Any]:
        """
        Get cached instances for a data source.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            Dictionary of cached instances
        """
        return {
            "api_client": self._api_client_cache.get(data_source_name),
            "repository": self._repository_cache.get(data_source_name),
            "service": self._service_cache.get(data_source_name)
        }
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics.
        
        Returns:
            Factory statistics
        """
        return {
            **self._creation_stats,
            "cached_clients": len(self._api_client_cache),
            "cached_repositories": len(self._repository_cache),
            "cached_services": len(self._service_cache),
            "cache_keys": {
                "clients": list(self._api_client_cache.keys()),
                "repositories": list(self._repository_cache.keys()),
                "services": list(self._service_cache.keys())
            }
        }
    
    def validate_data_source(self, data_source_name: str) -> List[str]:
        """
        Validate that a data source can be created successfully.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Check if data source exists
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                errors.append(f"Data source not found: {data_source_name}")
                return errors
            
            # Check required classes
            if not data_source_info.api_client_class:
                errors.append("API client class not available")
            
            if not data_source_info.repository_class:
                errors.append("Repository class not available")
            
            if not data_source_info.service_class:
                errors.append("Service class not available")
            
            # Validate configuration requirements
            config_errors = self.registry.validate_data_source_config(
                data_source_name, 
                data_source_info.default_config
            )
            errors.extend(config_errors)
            
            # Try creating instances (without caching)
            if not errors:
                api_client = self.create_api_client(data_source_name, use_cache=False)
                if not api_client:
                    errors.append("Failed to create API client")
                
                repository = self.create_repository(data_source_name, use_cache=False)
                if not repository:
                    errors.append("Failed to create repository")
                
                service = self.create_service(data_source_name, use_cache=False)
                if not service:
                    errors.append("Failed to create service")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors
    
    def _prepare_config(self, data_source_info: DataSourceInfo, override_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare configuration for component creation.
        
        Args:
            data_source_info: Data source information
            override_config: Optional configuration override
            
        Returns:
            Final configuration dictionary
        """
        # Start with default config
        config = data_source_info.default_config.copy()
        
        # Apply override config
        if override_config:
            config.update(override_config)
        
        return config


# Global data source factory instance
_data_source_factory: Optional[DataSourceFactory] = None


def get_data_source_factory() -> DataSourceFactory:
    """Get the global data source factory instance"""
    global _data_source_factory
    if _data_source_factory is None:
        _data_source_factory = DataSourceFactory()
    return _data_source_factory


def setup_data_source_factory(
    plugin_manager: Optional[PluginManager] = None,
    registry: Optional[DataSourceRegistry] = None,
    di_container: Optional[DIContainer] = None
) -> DataSourceFactory:
    """Setup and return the global data source factory"""
    global _data_source_factory
    _data_source_factory = DataSourceFactory(plugin_manager, registry, di_container)
    return _data_source_factory