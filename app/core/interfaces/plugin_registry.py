"""
Plugin system and registry for dynamic component management.

Implements Plugin pattern for flexible extension of API clients, repositories, and services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional, List, Callable, TypeVar, Generic
from enum import Enum
import importlib
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .base_api_client import BaseAPIClient
from .base_repository import BaseRepository
from .base_service import BaseService
from .factories import DataSourceType, DomainType

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PluginType(Enum):
    """Types of plugins that can be registered"""
    API_CLIENT = "api_client"
    REPOSITORY = "repository"
    SERVICE = "service"
    AUTHENTICATION = "authentication"
    DATA_TRANSFORMER = "data_transformer"
    VALIDATOR = "validator"
    MIDDLEWARE = "middleware"


class PluginStatus(Enum):
    """Plugin status"""
    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Metadata for a registered plugin"""
    name: str
    plugin_type: PluginType
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    registration_time: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class PluginInstance:
    """Instance of a registered plugin"""
    metadata: PluginMetadata
    plugin_class: Type[T]
    status: PluginStatus = PluginStatus.REGISTERED
    config: Optional[Dict[str, Any]] = None
    instance: Optional[T] = None
    error_message: Optional[str] = None


class IPlugin(ABC):
    """Base interface for all plugins"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin with configuration"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate plugin configuration. Returns list of errors."""
        return []


class APIClientPlugin(IPlugin):
    """Base class for API client plugins"""
    
    @abstractmethod
    def create_client(self, config: Dict[str, Any]) -> BaseAPIClient:
        """Create API client instance"""
        pass


class RepositoryPlugin(IPlugin):
    """Base class for repository plugins"""
    
    @abstractmethod
    def create_repository(self, config: Dict[str, Any]) -> BaseRepository:
        """Create repository instance"""
        pass


class ServicePlugin(IPlugin):
    """Base class for service plugins"""
    
    @abstractmethod
    def create_service(self, config: Dict[str, Any]) -> BaseService:
        """Create service instance"""
        pass


class PluginRegistry:
    """
    Central registry for managing plugins.
    
    Provides discovery, registration, activation, and lifecycle management.
    """
    
    def __init__(self):
        self._plugins: Dict[str, PluginInstance] = {}
        self._plugins_by_type: Dict[PluginType, List[str]] = {
            plugin_type: [] for plugin_type in PluginType
        }
        self._plugin_dependencies: Dict[str, List[str]] = {}
        self._discovery_paths: List[str] = []
    
    def register_plugin(
        self,
        plugin_class: Type[IPlugin],
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        auto_activate: bool = True
    ) -> bool:
        """
        Register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
            name: Plugin name (defaults to class name)
            config: Initial configuration
            auto_activate: Whether to activate immediately
            
        Returns:
            True if registration successful
        """
        try:
            # Create plugin instance to get metadata
            temp_instance = plugin_class()
            metadata = temp_instance.get_metadata()
            
            # Use provided name or default to metadata name
            plugin_name = name or metadata.name
            
            # Check if already registered
            if plugin_name in self._plugins:
                logger.warning(f"Plugin '{plugin_name}' already registered")
                return False
            
            # Validate configuration if provided
            if config:
                validation_errors = temp_instance.validate_config(config)
                if validation_errors:
                    logger.error(f"Plugin '{plugin_name}' config validation failed: {validation_errors}")
                    return False
            
            # Create plugin instance
            plugin_instance = PluginInstance(
                metadata=metadata,
                plugin_class=plugin_class,
                config=config
            )
            
            # Register plugin
            self._plugins[plugin_name] = plugin_instance
            self._plugins_by_type[metadata.plugin_type].append(plugin_name)
            
            # Register dependencies
            if metadata.dependencies:
                self._plugin_dependencies[plugin_name] = metadata.dependencies
            
            logger.info(f"Plugin '{plugin_name}' registered successfully")
            
            # Auto-activate if requested
            if auto_activate:
                return self.activate_plugin(plugin_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False
    
    def activate_plugin(self, name: str) -> bool:
        """
        Activate a registered plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            True if activation successful
        """
        try:
            if name not in self._plugins:
                logger.error(f"Plugin '{name}' not registered")
                return False
            
            plugin_instance = self._plugins[name]
            
            # Check if already active
            if plugin_instance.status == PluginStatus.ACTIVE:
                logger.warning(f"Plugin '{name}' already active")
                return True
            
            # Check dependencies
            if not self._check_dependencies(name):
                return False
            
            # Create and initialize plugin instance
            plugin_obj = plugin_instance.plugin_class()
            plugin_obj.initialize(plugin_instance.config)
            
            # Update plugin instance
            plugin_instance.instance = plugin_obj
            plugin_instance.status = PluginStatus.ACTIVE
            plugin_instance.error_message = None
            
            logger.info(f"Plugin '{name}' activated successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to activate plugin '{name}': {e}"
            logger.error(error_msg)
            
            if name in self._plugins:
                self._plugins[name].status = PluginStatus.ERROR
                self._plugins[name].error_message = str(e)
            
            return False
    
    def deactivate_plugin(self, name: str) -> bool:
        """
        Deactivate an active plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            True if deactivation successful
        """
        try:
            if name not in self._plugins:
                logger.error(f"Plugin '{name}' not registered")
                return False
            
            plugin_instance = self._plugins[name]
            
            if plugin_instance.status != PluginStatus.ACTIVE:
                logger.warning(f"Plugin '{name}' not active")
                return True
            
            # Cleanup plugin
            if plugin_instance.instance:
                plugin_instance.instance.cleanup()
                plugin_instance.instance = None
            
            plugin_instance.status = PluginStatus.INACTIVE
            
            logger.info(f"Plugin '{name}' deactivated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate plugin '{name}': {e}")
            return False
    
    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin completely.
        
        Args:
            name: Plugin name
            
        Returns:
            True if unregistration successful
        """
        try:
            if name not in self._plugins:
                logger.warning(f"Plugin '{name}' not registered")
                return True
            
            # Deactivate first
            self.deactivate_plugin(name)
            
            # Remove from registry
            plugin_instance = self._plugins[name]
            plugin_type = plugin_instance.metadata.plugin_type
            
            del self._plugins[name]
            if name in self._plugins_by_type[plugin_type]:
                self._plugins_by_type[plugin_type].remove(name)
            if name in self._plugin_dependencies:
                del self._plugin_dependencies[name]
            
            logger.info(f"Plugin '{name}' unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister plugin '{name}': {e}")
            return False
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """
        Get active plugin instance.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance if active, None otherwise
        """
        if name not in self._plugins:
            return None
        
        plugin_instance = self._plugins[name]
        
        if plugin_instance.status == PluginStatus.ACTIVE:
            # Update usage statistics
            plugin_instance.metadata.usage_count += 1
            plugin_instance.metadata.last_used = datetime.utcnow()
            return plugin_instance.instance
        
        return None
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """
        Get list of plugin names by type.
        
        Args:
            plugin_type: Type of plugins to retrieve
            
        Returns:
            List of plugin names
        """
        return self._plugins_by_type.get(plugin_type, []).copy()
    
    def get_active_plugins(self) -> List[str]:
        """Get list of active plugin names"""
        return [
            name for name, instance in self._plugins.items()
            if instance.status == PluginStatus.ACTIVE
        ]
    
    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed plugin information.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin information dictionary
        """
        if name not in self._plugins:
            return None
        
        plugin_instance = self._plugins[name]
        
        return {
            "name": name,
            "metadata": {
                "name": plugin_instance.metadata.name,
                "type": plugin_instance.metadata.plugin_type.value,
                "version": plugin_instance.metadata.version,
                "description": plugin_instance.metadata.description,
                "author": plugin_instance.metadata.author,
                "dependencies": plugin_instance.metadata.dependencies,
                "tags": plugin_instance.metadata.tags,
                "registration_time": plugin_instance.metadata.registration_time.isoformat(),
                "last_used": plugin_instance.metadata.last_used.isoformat() if plugin_instance.metadata.last_used else None,
                "usage_count": plugin_instance.metadata.usage_count
            },
            "status": plugin_instance.status.value,
            "config": plugin_instance.config,
            "error_message": plugin_instance.error_message
        }
    
    def discover_plugins(self, path: str) -> List[str]:
        """
        Discover plugins in a given path.
        
        Args:
            path: Python module path to search
            
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        try:
            module = importlib.import_module(path)
            
            # Look for classes that implement IPlugin
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, IPlugin) and 
                    obj != IPlugin and 
                    not inspect.isabstract(obj)):
                    
                    # Auto-register discovered plugin
                    if self.register_plugin(obj, auto_activate=False):
                        discovered.append(name)
            
            if path not in self._discovery_paths:
                self._discovery_paths.append(path)
                
        except Exception as e:
            logger.error(f"Plugin discovery failed for path '{path}': {e}")
        
        return discovered
    
    def _check_dependencies(self, name: str) -> bool:
        """Check if plugin dependencies are satisfied"""
        if name not in self._plugin_dependencies:
            return True
        
        dependencies = self._plugin_dependencies[name]
        
        for dep in dependencies:
            if dep not in self._plugins:
                logger.error(f"Plugin '{name}' dependency '{dep}' not registered")
                return False
            
            if self._plugins[dep].status != PluginStatus.ACTIVE:
                logger.error(f"Plugin '{name}' dependency '{dep}' not active")
                return False
        
        return True
    
    def reload_plugin(self, name: str) -> bool:
        """
        Reload a plugin by deactivating and reactivating.
        
        Args:
            name: Plugin name
            
        Returns:
            True if reload successful
        """
        if name not in self._plugins:
            logger.error(f"Plugin '{name}' not registered")
            return False
        
        # Store current config
        current_config = self._plugins[name].config
        
        # Deactivate and reactivate
        if self.deactivate_plugin(name):
            return self.activate_plugin(name)
        
        return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_plugins = len(self._plugins)
        active_plugins = len([p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE])
        error_plugins = len([p for p in self._plugins.values() if p.status == PluginStatus.ERROR])
        
        type_stats = {}
        for plugin_type in PluginType:
            type_stats[plugin_type.value] = len(self._plugins_by_type[plugin_type])
        
        return {
            "total_plugins": total_plugins,
            "active_plugins": active_plugins,
            "error_plugins": error_plugins,
            "discovery_paths": self._discovery_paths.copy(),
            "type_statistics": type_stats
        }


# Global registry instance
_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry instance"""
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry


def register_plugin(plugin_class: Type[IPlugin], **kwargs) -> bool:
    """Convenience function to register plugin"""
    return get_plugin_registry().register_plugin(plugin_class, **kwargs)


def get_plugin(name: str) -> Optional[Any]:
    """Convenience function to get plugin"""
    return get_plugin_registry().get_plugin(name)


def discover_plugins(path: str) -> List[str]:
    """Convenience function to discover plugins"""
    return get_plugin_registry().discover_plugins(path)