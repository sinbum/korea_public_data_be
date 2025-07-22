"""
Plugin Manager - orchestrates plugin lifecycle and management.

The manager coordinates plugin discovery, loading, initialization,
and provides the main interface for plugin operations.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import logging

from .base import (
    BasePlugin, PluginMetadata, PluginState, PluginType,
    DataSourcePlugin, ProcessorPlugin, ExporterPlugin,
    PluginError, PluginInitializationError, PluginDependencyError
)
from .registry import PluginRegistry
from .loader import PluginLoader
from .config import PluginConfig

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Central plugin management system.
    
    Orchestrates plugin lifecycle from discovery through cleanup,
    manages dependencies, and provides operational interface.
    """
    
    def __init__(self, config: Optional[PluginConfig] = None):
        self.config = config or PluginConfig()
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False
        self._startup_hooks: List[callable] = []
        self._shutdown_hooks: List[callable] = []
        
        # Plugin event handlers
        self._event_handlers: Dict[str, List[callable]] = {
            'plugin_loaded': [],
            'plugin_activated': [],
            'plugin_deactivated': [],
            'plugin_error': []
        }
        
        # Setup registry state listener
        self.registry.add_state_listener(self._on_plugin_state_change)
    
    async def initialize(self) -> bool:
        """
        Initialize the plugin manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.warning("Plugin manager already initialized")
                return True
            
            try:
                logger.info("Initializing plugin manager...")
                
                # Setup plugin directories from config
                for directory in self.config.plugin_directories:
                    self.loader.add_plugin_directory(directory)
                
                # Auto-discover and load plugins if enabled
                if self.config.auto_discover:
                    await self._auto_discover_and_load()
                
                # Run startup hooks
                await self._run_startup_hooks()
                
                self._is_initialized = True
                logger.info("Plugin manager initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize plugin manager: {e}")
                return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the plugin manager and cleanup resources.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            logger.info("Shutting down plugin manager...")
            
            # Run shutdown hooks
            await self._run_shutdown_hooks()
            
            # Deactivate and cleanup all active plugins
            active_plugins = self.registry.list_plugins(state=PluginState.ACTIVE)
            for plugin_name in active_plugins:
                await self.deactivate_plugin(plugin_name)
            
            self._is_initialized = False
            logger.info("Plugin manager shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during plugin manager shutdown: {e}")
            return False
    
    async def discover_plugins(self) -> Dict[str, Any]:
        """
        Discover available plugins.
        
        Returns:
            Discovery results with statistics
        """
        logger.info("Discovering plugins...")
        result = self.loader.discover_plugins()
        
        return {
            "discovered": result.discovered,
            "failed": result.failed,
            "errors": result.errors,
            "total_discovered": result.total_discovered,
            "total_failed": result.total_failed
        }
    
    async def load_plugin(self, plugin_path: str) -> bool:
        """
        Load a plugin from path.
        
        Args:
            plugin_path: Path to plugin file or directory
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            plugin = await self.loader.load_plugin(plugin_path)
            if plugin:
                if self.registry.register(plugin):
                    await self._emit_event('plugin_loaded', plugin.get_metadata().name, plugin)
                    logger.info(f"Plugin loaded: {plugin.get_metadata().name}")
                    return True
                else:
                    logger.error(f"Failed to register plugin from {plugin_path}")
                    return False
            else:
                logger.error(f"Failed to load plugin from {plugin_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_path}: {e}")
            await self._emit_event('plugin_error', plugin_path, str(e))
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            # Deactivate first if active
            metadata = self.registry.get_metadata(plugin_name)
            if metadata and metadata.state == PluginState.ACTIVE:
                if not await self.deactivate_plugin(plugin_name):
                    logger.error(f"Failed to deactivate plugin {plugin_name} before unloading")
                    return False
            
            # Unload plugin
            if self.loader.unload_plugin(plugin_name):
                logger.info(f"Plugin unloaded: {plugin_name}")
                return True
            else:
                logger.error(f"Failed to unload plugin: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    async def activate_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Activate a plugin with optional configuration.
        
        Args:
            plugin_name: Name of plugin to activate
            config: Plugin-specific configuration
            
        Returns:
            True if activated successfully, False otherwise
        """
        try:
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                logger.error(f"Plugin not found: {plugin_name}")
                return False
            
            metadata = plugin.get_metadata()
            if metadata.state == PluginState.ACTIVE:
                logger.warning(f"Plugin {plugin_name} is already active")
                return True
            
            # Update state to initializing
            self.registry.update_plugin_state(plugin_name, PluginState.INITIALIZING)
            
            # Validate dependencies
            missing_deps = self.registry.validate_dependencies(plugin_name)
            if missing_deps:
                error_msg = f"Missing dependencies: {missing_deps}"
                self.registry.update_plugin_state(plugin_name, PluginState.ERROR, error_msg)
                raise PluginDependencyError(error_msg)
            
            # Activate dependencies first
            deps_order = self.registry.resolve_dependencies(plugin_name)
            for dep_name in deps_order[:-1]:  # Exclude the plugin itself
                dep_metadata = self.registry.get_metadata(dep_name)
                if dep_metadata and dep_metadata.state != PluginState.ACTIVE:
                    if not await self.activate_plugin(dep_name):
                        error_msg = f"Failed to activate dependency: {dep_name}"
                        self.registry.update_plugin_state(plugin_name, PluginState.ERROR, error_msg)
                        raise PluginDependencyError(error_msg)
            
            # Prepare configuration
            plugin_config = self._prepare_plugin_config(plugin_name, config)
            
            # Initialize plugin
            if await plugin.initialize(plugin_config):
                self.registry.update_plugin_state(plugin_name, PluginState.ACTIVE)
                metadata.loaded_at = datetime.utcnow()
                
                # Register plugin components with DI container if it's a data source plugin
                if isinstance(plugin, DataSourcePlugin):
                    await self._register_data_source_plugin(plugin)
                
                await self._emit_event('plugin_activated', plugin_name, plugin)
                logger.info(f"Plugin activated: {plugin_name}")
                return True
            else:
                error_msg = "Plugin initialization failed"
                self.registry.update_plugin_state(plugin_name, PluginState.ERROR, error_msg)
                logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            self.registry.update_plugin_state(plugin_name, PluginState.ERROR, error_msg)
            logger.error(f"Error activating plugin {plugin_name}: {e}")
            await self._emit_event('plugin_error', plugin_name, error_msg)
            return False
    
    async def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        Deactivate a plugin.
        
        Args:
            plugin_name: Name of plugin to deactivate
            
        Returns:
            True if deactivated successfully, False otherwise
        """
        try:
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                logger.error(f"Plugin not found: {plugin_name}")
                return False
            
            metadata = plugin.get_metadata()
            if metadata.state != PluginState.ACTIVE:
                logger.warning(f"Plugin {plugin_name} is not active")
                return True
            
            # Check for active dependents
            dependents = self.registry.get_dependents(plugin_name)
            active_dependents = [
                name for name in dependents 
                if self.registry.get_metadata(name).state == PluginState.ACTIVE
            ]
            
            if active_dependents:
                logger.error(f"Cannot deactivate plugin {plugin_name}: active dependents {active_dependents}")
                return False
            
            # Update state
            self.registry.update_plugin_state(plugin_name, PluginState.INACTIVE)
            
            # Cleanup plugin
            if await plugin.cleanup():
                await self._emit_event('plugin_deactivated', plugin_name, plugin)
                logger.info(f"Plugin deactivated: {plugin_name}")
                return True
            else:
                logger.error(f"Plugin cleanup failed: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_name}: {e}")
            return False
    
    async def reload_plugin(self, plugin_name: str, plugin_path: str) -> bool:
        """
        Reload a plugin from disk.
        
        Args:
            plugin_name: Name of plugin to reload
            plugin_path: Path to plugin file/directory
            
        Returns:
            True if reloaded successfully, False otherwise
        """
        try:
            # Get current state and config
            metadata = self.registry.get_metadata(plugin_name)
            was_active = metadata and metadata.state == PluginState.ACTIVE
            
            # Deactivate if active
            if was_active:
                if not await self.deactivate_plugin(plugin_name):
                    return False
            
            # Reload plugin
            plugin = self.loader.reload_plugin(plugin_name, plugin_path)
            if plugin:
                # Reactivate if it was active before
                if was_active:
                    return await self.activate_plugin(plugin_name)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get plugin instance by name"""
        return self.registry.get_plugin(plugin_name)
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name"""
        return self.registry.get_metadata(plugin_name)
    
    def list_plugins(
        self, 
        plugin_type: Optional[PluginType] = None,
        state: Optional[PluginState] = None
    ) -> List[str]:
        """List plugins with optional filtering"""
        return self.registry.list_plugins(plugin_type, state)
    
    def get_data_source_plugins(self) -> List[DataSourcePlugin]:
        """Get all active data source plugins"""
        plugins = []
        data_source_names = self.list_plugins(PluginType.DATA_SOURCE, PluginState.ACTIVE)
        
        for name in data_source_names:
            plugin = self.registry.get_plugin(name)
            if isinstance(plugin, DataSourcePlugin):
                plugins.append(plugin)
        
        return plugins
    
    def get_processor_plugins(self) -> List[ProcessorPlugin]:
        """Get all active processor plugins"""
        plugins = []
        processor_names = self.list_plugins(PluginType.PROCESSOR, PluginState.ACTIVE)
        
        for name in processor_names:
            plugin = self.registry.get_plugin(name)
            if isinstance(plugin, ProcessorPlugin):
                plugins.append(plugin)
        
        return plugins
    
    def get_exporter_plugins(self) -> List[ExporterPlugin]:
        """Get all active exporter plugins"""
        plugins = []
        exporter_names = self.list_plugins(PluginType.EXPORTER, PluginState.ACTIVE)
        
        for name in exporter_names:
            plugin = self.registry.get_plugin(name)
            if isinstance(plugin, ExporterPlugin):
                plugins.append(plugin)
        
        return plugins
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all active plugins"""
        results = {}
        active_plugins = self.list_plugins(state=PluginState.ACTIVE)
        
        for plugin_name in active_plugins:
            plugin = self.registry.get_plugin(plugin_name)
            if plugin:
                try:
                    results[plugin_name] = plugin.health_check()
                except Exception as e:
                    results[plugin_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return results
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics"""
        registry_stats = self.registry.get_plugin_stats()
        loader_stats = self.loader.get_loader_stats()
        
        return {
            "is_initialized": self._is_initialized,
            "registry": registry_stats,
            "loader": loader_stats,
            "event_handlers": {
                event: len(handlers) for event, handlers in self._event_handlers.items()
            }
        }
    
    # Event system
    def add_event_handler(self, event: str, handler: callable):
        """Add an event handler"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler: callable):
        """Remove an event handler"""
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
    
    async def _emit_event(self, event: str, *args, **kwargs):
        """Emit an event to all handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")
    
    # Lifecycle hooks
    def add_startup_hook(self, hook: callable):
        """Add a startup hook"""
        self._startup_hooks.append(hook)
    
    def add_shutdown_hook(self, hook: callable):
        """Add a shutdown hook"""
        self._shutdown_hooks.append(hook)
    
    async def _run_startup_hooks(self):
        """Run all startup hooks"""
        for hook in self._startup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in startup hook: {e}")
    
    async def _run_shutdown_hooks(self):
        """Run all shutdown hooks"""
        for hook in self._shutdown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Error in shutdown hook: {e}")
    
    async def _auto_discover_and_load(self):
        """Automatically discover and load plugins"""
        try:
            discovery_result = await self.discover_plugins()
            logger.info(f"Auto-discovery found {discovery_result['total_discovered']} plugins")
            
            for plugin_path in discovery_result['discovered']:
                await self.load_plugin(plugin_path)
            
            # Auto-activate plugins if configured
            if self.config.auto_activate:
                loaded_plugins = self.list_plugins(state=PluginState.LOADED)
                for plugin_name in loaded_plugins:
                    await self.activate_plugin(plugin_name)
                    
        except Exception as e:
            logger.error(f"Error in auto-discovery: {e}")
    
    def _prepare_plugin_config(self, plugin_name: str, custom_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare configuration for plugin initialization"""
        metadata = self.registry.get_metadata(plugin_name)
        if not metadata:
            return custom_config or {}
        
        # Start with default config
        config = metadata.default_config.copy()
        
        # Add global plugin config
        global_config = self.config.get_plugin_config(plugin_name)
        if global_config:
            config.update(global_config)
        
        # Override with custom config
        if custom_config:
            config.update(custom_config)
        
        return config
    
    async def _register_data_source_plugin(self, plugin: DataSourcePlugin):
        """Register data source plugin components with DI container"""
        try:
            # This would integrate with the DI container to register
            # the plugin's API client, repository, and service classes
            # Implementation depends on how we want to integrate with the existing DI system
            logger.info(f"Registered data source plugin components: {plugin.get_metadata().name}")
        except Exception as e:
            logger.error(f"Failed to register data source plugin components: {e}")
    
    def _on_plugin_state_change(self, plugin_name: str, state: PluginState):
        """Handle plugin state changes"""
        logger.debug(f"Plugin {plugin_name} state changed to {state}")
        
        # Emit appropriate events
        if state == PluginState.ACTIVE:
            asyncio.create_task(self._emit_event('plugin_activated', plugin_name))
        elif state == PluginState.INACTIVE:
            asyncio.create_task(self._emit_event('plugin_deactivated', plugin_name))
        elif state == PluginState.ERROR:
            asyncio.create_task(self._emit_event('plugin_error', plugin_name))


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> Optional[PluginManager]:
    """Get the global plugin manager instance"""
    return _plugin_manager


def setup_plugin_manager(config: Optional[PluginConfig] = None) -> PluginManager:
    """Setup and return the global plugin manager"""
    global _plugin_manager
    _plugin_manager = PluginManager(config)
    return _plugin_manager