"""
Data Source Manager - manages data source discovery, lifecycle, and operations.

Coordinates between plugins, registry, factory, and health monitoring to provide
a unified interface for data source management.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import logging

from ..plugins.manager import PluginManager, get_plugin_manager
from ..plugins.base import DataSourcePlugin, PluginState
from .registry import DataSourceRegistry, DataSourceInfo, DataSourceStatus, get_data_source_registry
from .factory import DataSourceFactory, get_data_source_factory
from .health import DataSourceHealthMonitor

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    Central manager for data source operations.
    
    Coordinates plugin discovery, data source registration, health monitoring,
    and provides unified interface for data source management.
    """
    
    def __init__(
        self,
        plugin_manager: Optional[PluginManager] = None,
        registry: Optional[DataSourceRegistry] = None,
        factory: Optional[DataSourceFactory] = None,
        health_monitor: Optional[DataSourceHealthMonitor] = None
    ):
        self.plugin_manager = plugin_manager or get_plugin_manager()
        self.registry = registry or get_data_source_registry()
        self.factory = factory or get_data_source_factory()
        self.health_monitor = health_monitor or DataSourceHealthMonitor(self.registry)
        
        self._is_initialized = False
        self._auto_discovery_enabled = True
        self._health_monitoring_enabled = True
        self._discovery_interval = 300  # 5 minutes
        self._health_check_interval = 60  # 1 minute
        
        # Background tasks
        self._discovery_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self._event_handlers: Dict[str, List[callable]] = {
            'data_source_discovered': [],
            'data_source_registered': [],
            'data_source_activated': [],
            'data_source_deactivated': [],
            'data_source_error': [],
            'health_status_changed': []
        }
        
        # Manager statistics
        self._stats = {
            "discovery_runs": 0,
            "health_checks": 0,
            "total_data_sources_managed": 0,
            "last_discovery_time": None,
            "last_health_check_time": None,
            "errors": 0
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the data source manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self._is_initialized:
                logger.warning("Data source manager already initialized")
                return True
            
            logger.info("Initializing data source manager...")
            
            # Initialize plugin manager if needed
            if self.plugin_manager and not self.plugin_manager._is_initialized:
                if not await self.plugin_manager.initialize():
                    logger.error("Failed to initialize plugin manager")
                    return False
            
            # Perform initial discovery
            await self.discover_data_sources()
            
            # Start background tasks
            if self._auto_discovery_enabled:
                self._discovery_task = asyncio.create_task(self._auto_discovery_loop())
            
            if self._health_monitoring_enabled:
                self._health_check_task = asyncio.create_task(self._health_monitoring_loop())
            
            self._is_initialized = True
            logger.info("Data source manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data source manager: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the data source manager.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            logger.info("Shutting down data source manager...")
            
            # Cancel background tasks
            if self._discovery_task:
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass
            
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Deactivate all data sources
            active_sources = self.registry.list_data_sources(status=DataSourceStatus.ACTIVE)
            for source_name in active_sources:
                await self.deactivate_data_source(source_name)
            
            self._is_initialized = False
            logger.info("Data source manager shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during data source manager shutdown: {e}")
            return False
    
    async def discover_data_sources(self) -> Dict[str, Any]:
        """
        Discover available data sources from plugins.
        
        Returns:
            Discovery results with statistics
        """
        try:
            logger.info("Discovering data sources...")
            start_time = datetime.utcnow()
            
            discovered = 0
            registered = 0
            errors = []
            
            if not self.plugin_manager:
                logger.warning("Plugin manager not available for discovery")
                return {"discovered": 0, "registered": 0, "errors": ["Plugin manager not available"]}
            
            # Get all data source plugins
            data_source_plugins = self.plugin_manager.get_data_source_plugins()
            
            for plugin in data_source_plugins:
                try:
                    discovered += 1
                    
                    # Check if already registered
                    plugin_name = plugin.get_metadata().name
                    existing_sources = self.registry.get_data_sources_by_plugin(plugin_name)
                    
                    if existing_sources:
                        logger.debug(f"Data source from plugin {plugin_name} already registered")
                        continue
                    
                    # Register data source from plugin
                    if self.factory.register_data_source_from_plugin(plugin):
                        registered += 1
                        await self._emit_event('data_source_discovered', plugin_name)
                        await self._emit_event('data_source_registered', plugin_name)
                        logger.info(f"Registered data source from plugin: {plugin_name}")
                    else:
                        errors.append(f"Failed to register data source from plugin: {plugin_name}")
                
                except Exception as e:
                    logger.error(f"Error processing plugin {plugin.get_metadata().name}: {e}")
                    errors.append(f"Plugin {plugin.get_metadata().name}: {e}")
                    self._stats["errors"] += 1
            
            # Update statistics
            self._stats["discovery_runs"] += 1
            self._stats["last_discovery_time"] = start_time
            self._stats["total_data_sources_managed"] = len(self.registry._data_sources)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                "discovered": discovered,
                "registered": registered,
                "errors": errors,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
            logger.info(f"Discovery completed: {registered}/{discovered} data sources registered")
            return result
            
        except Exception as e:
            logger.error(f"Error during data source discovery: {e}")
            self._stats["errors"] += 1
            return {"discovered": 0, "registered": 0, "errors": [str(e)]}
    
    async def activate_data_source(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Activate a data source.
        
        Args:
            name: Data source name
            config: Optional configuration override
            
        Returns:
            True if activation successful, False otherwise
        """
        try:
            data_source_info = self.registry.get_data_source(name)
            if not data_source_info:
                logger.error(f"Data source not found: {name}")
                return False
            
            if data_source_info.status == DataSourceStatus.ACTIVE:
                logger.warning(f"Data source {name} is already active")
                return True
            
            # Update status to initializing
            self.registry.update_data_source_status(name, DataSourceStatus.INITIALIZING)
            
            # Validate configuration
            config_errors = self.registry.validate_data_source_config(name, config or {})
            if config_errors:
                error_msg = f"Configuration errors: {config_errors}"
                self.registry.update_data_source_status(name, DataSourceStatus.ERROR, error_msg)
                logger.error(f"Failed to activate {name}: {error_msg}")
                return False
            
            # Create service stack
            stack = self.factory.create_full_stack(name, config)
            if not stack:
                error_msg = "Failed to create service stack"
                self.registry.update_data_source_status(name, DataSourceStatus.ERROR, error_msg)
                logger.error(f"Failed to activate {name}: {error_msg}")
                return False
            
            # Update status to active
            self.registry.update_data_source_status(name, DataSourceStatus.ACTIVE)
            
            # Start health monitoring for this data source
            await self.health_monitor.start_monitoring(name)
            
            await self._emit_event('data_source_activated', name)
            logger.info(f"Data source activated: {name}")
            return True
            
        except Exception as e:
            error_msg = f"Activation error: {e}"
            self.registry.update_data_source_status(name, DataSourceStatus.ERROR, error_msg)
            logger.error(f"Failed to activate data source {name}: {e}")
            await self._emit_event('data_source_error', name, error_msg)
            self._stats["errors"] += 1
            return False
    
    async def deactivate_data_source(self, name: str) -> bool:
        """
        Deactivate a data source.
        
        Args:
            name: Data source name
            
        Returns:
            True if deactivation successful, False otherwise
        """
        try:
            data_source_info = self.registry.get_data_source(name)
            if not data_source_info:
                logger.error(f"Data source not found: {name}")
                return False
            
            if data_source_info.status != DataSourceStatus.ACTIVE:
                logger.warning(f"Data source {name} is not active")
                return True
            
            # Stop health monitoring
            await self.health_monitor.stop_monitoring(name)
            
            # Clear cached instances
            self.factory.clear_cache(name)
            
            # Update status
            self.registry.update_data_source_status(name, DataSourceStatus.INACTIVE)
            
            await self._emit_event('data_source_deactivated', name)
            logger.info(f"Data source deactivated: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate data source {name}: {e}")
            self._stats["errors"] += 1
            return False
    
    async def reload_data_source(self, name: str) -> bool:
        """
        Reload a data source (deactivate and reactivate).
        
        Args:
            name: Data source name
            
        Returns:
            True if reload successful, False otherwise
        """
        try:
            logger.info(f"Reloading data source: {name}")
            
            # Get current config before deactivation
            data_source_info = self.registry.get_data_source(name)
            if not data_source_info:
                return False
            
            config = data_source_info.default_config
            
            # Deactivate
            if not await self.deactivate_data_source(name):
                return False
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Reactivate
            return await self.activate_data_source(name, config)
            
        except Exception as e:
            logger.error(f"Failed to reload data source {name}: {e}")
            return False
    
    async def get_data_source_health(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get health status for a data source.
        
        Args:
            name: Data source name
            
        Returns:
            Health status or None if not found
        """
        return await self.health_monitor.get_health_status(name)
    
    async def get_all_health_status(self) -> Dict[str, Any]:
        """
        Get health status for all data sources.
        
        Returns:
            Health status for all data sources
        """
        return await self.health_monitor.get_all_health_status()
    
    def list_data_sources(
        self,
        status: Optional[DataSourceStatus] = None,
        include_health: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List data sources with optional filtering.
        
        Args:
            status: Filter by status
            include_health: Include health information
            
        Returns:
            List of data source information
        """
        try:
            source_names = self.registry.list_data_sources(status=status)
            result = []
            
            for name in source_names:
                info = self.registry.get_data_source(name)
                if info:
                    source_data = {
                        "name": name,
                        "display_name": info.display_name,
                        "description": info.description,
                        "type": info.source_type,
                        "status": info.status,
                        "provider": info.provider,
                        "category": info.category,
                        "registered_at": info.registered_at,
                        "plugin_name": info.plugin_name
                    }
                    
                    if include_health:
                        health = asyncio.create_task(self.get_data_source_health(name))
                        # Note: This would need to be handled differently in a real async context
                        source_data["health"] = "pending"  # Placeholder
                    
                    result.append(source_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing data sources: {e}")
            return []
    
    def search_data_sources(self, query: str) -> List[str]:
        """
        Search data sources by query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching data source names
        """
        return self.registry.search_data_sources(query)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get manager statistics.
        
        Returns:
            Manager statistics
        """
        registry_stats = self.registry.get_registry_stats()
        factory_stats = self.factory.get_factory_stats()
        health_stats = self.health_monitor.get_monitoring_stats()
        
        return {
            "manager": self._stats,
            "registry": registry_stats,
            "factory": factory_stats,
            "health": health_stats,
            "is_initialized": self._is_initialized,
            "auto_discovery_enabled": self._auto_discovery_enabled,
            "health_monitoring_enabled": self._health_monitoring_enabled
        }
    
    def configure_auto_discovery(self, enabled: bool, interval_seconds: int = 300):
        """
        Configure automatic discovery.
        
        Args:
            enabled: Whether to enable auto discovery
            interval_seconds: Discovery interval in seconds
        """
        self._auto_discovery_enabled = enabled
        self._discovery_interval = interval_seconds
        logger.info(f"Auto discovery configured: enabled={enabled}, interval={interval_seconds}s")
    
    def configure_health_monitoring(self, enabled: bool, interval_seconds: int = 60):
        """
        Configure health monitoring.
        
        Args:
            enabled: Whether to enable health monitoring
            interval_seconds: Health check interval in seconds
        """
        self._health_monitoring_enabled = enabled
        self._health_check_interval = interval_seconds
        logger.info(f"Health monitoring configured: enabled={enabled}, interval={interval_seconds}s")
    
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
    
    async def _auto_discovery_loop(self):
        """Background task for automatic discovery"""
        while True:
            try:
                await asyncio.sleep(self._discovery_interval)
                if self._auto_discovery_enabled:
                    await self.discover_data_sources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto discovery loop: {e}")
    
    async def _health_monitoring_loop(self):
        """Background task for health monitoring"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                if self._health_monitoring_enabled:
                    await self.health_monitor.check_all_health()
                    self._stats["health_checks"] += 1
                    self._stats["last_health_check_time"] = datetime.utcnow()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")


# Global data source manager instance
_data_source_manager: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    """Get the global data source manager instance"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager


def setup_data_source_manager(
    plugin_manager: Optional[PluginManager] = None,
    registry: Optional[DataSourceRegistry] = None,
    factory: Optional[DataSourceFactory] = None,
    health_monitor: Optional[DataSourceHealthMonitor] = None
) -> DataSourceManager:
    """Setup and return the global data source manager"""
    global _data_source_manager
    _data_source_manager = DataSourceManager(plugin_manager, registry, factory, health_monitor)
    return _data_source_manager