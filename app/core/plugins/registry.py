"""
Plugin Registry - manages plugin information and dependencies.

The registry maintains a catalog of all discovered and loaded plugins,
handles dependency resolution, and provides query capabilities.
"""

from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, deque
import logging

from .base import (
    BasePlugin, PluginMetadata, PluginState, PluginType, 
    PluginDependency, PluginError, PluginDependencyError
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for plugin management.
    
    Maintains plugin metadata, handles dependency resolution,
    and provides query capabilities.
    """
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._dependencies: Dict[str, List[PluginDependency]] = {}
        self._dependents: Dict[str, Set[str]] = defaultdict(set)  # reverse dependency map
        self._state_listeners: List[callable] = []
    
    def register(self, plugin: BasePlugin) -> bool:
        """
        Register a plugin with the registry.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            metadata = plugin.get_metadata()
            plugin_name = metadata.name
            
            if plugin_name in self._plugins:
                logger.warning(f"Plugin {plugin_name} is already registered")
                return False
            
            # Validate plugin metadata
            self._validate_plugin_metadata(metadata)
            
            # Register the plugin
            self._plugins[plugin_name] = plugin
            self._metadata[plugin_name] = metadata
            self._dependencies[plugin_name] = metadata.dependencies
            
            # Update reverse dependency mapping
            for dep in metadata.dependencies:
                self._dependents[dep.name].add(plugin_name)
            
            logger.info(f"Registered plugin: {plugin_name} v{metadata.version}")
            self._notify_state_change(plugin_name, PluginState.LOADED)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False
    
    def unregister(self, plugin_name: str) -> bool:
        """
        Unregister a plugin from the registry.
        
        Args:
            plugin_name: Name of plugin to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if plugin_name not in self._plugins:
                logger.warning(f"Plugin {plugin_name} is not registered")
                return False
            
            # Check if other plugins depend on this one
            dependents = self._dependents.get(plugin_name, set())
            active_dependents = [
                name for name in dependents 
                if self._metadata.get(name, {}).get('state') == PluginState.ACTIVE
            ]
            
            if active_dependents:
                logger.error(f"Cannot unregister plugin {plugin_name}: active dependents {active_dependents}")
                return False
            
            # Remove from registry
            plugin = self._plugins.pop(plugin_name)
            metadata = self._metadata.pop(plugin_name)
            dependencies = self._dependencies.pop(plugin_name, [])
            
            # Update reverse dependency mapping
            for dep in dependencies:
                self._dependents[dep.name].discard(plugin_name)
            self._dependents.pop(plugin_name, None)
            
            logger.info(f"Unregistered plugin: {plugin_name}")
            self._notify_state_change(plugin_name, PluginState.UNLOADED)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get plugin instance by name"""
        return self._plugins.get(plugin_name)
    
    def get_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name"""
        return self._metadata.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all registered plugins"""
        return self._plugins.copy()
    
    def get_all_metadata(self) -> Dict[str, PluginMetadata]:
        """Get all plugin metadata"""
        return self._metadata.copy()
    
    def list_plugins(
        self, 
        plugin_type: Optional[PluginType] = None,
        state: Optional[PluginState] = None
    ) -> List[str]:
        """
        List plugin names with optional filtering.
        
        Args:
            plugin_type: Filter by plugin type
            state: Filter by plugin state
            
        Returns:
            List of plugin names matching criteria
        """
        plugins = []
        
        for name, metadata in self._metadata.items():
            if plugin_type and metadata.plugin_type != plugin_type:
                continue
            if state and metadata.state != state:
                continue
            plugins.append(name)
        
        return plugins
    
    def get_dependencies(self, plugin_name: str) -> List[PluginDependency]:
        """Get dependencies for a plugin"""
        return self._dependencies.get(plugin_name, [])
    
    def get_dependents(self, plugin_name: str) -> Set[str]:
        """Get plugins that depend on the given plugin"""
        return self._dependents.get(plugin_name, set()).copy()
    
    def resolve_dependencies(self, plugin_name: str) -> List[str]:
        """
        Resolve plugin dependencies in load order.
        
        Args:
            plugin_name: Plugin to resolve dependencies for
            
        Returns:
            List of plugin names in dependency order
            
        Raises:
            PluginDependencyError: If dependencies cannot be resolved
        """
        try:
            return self._topological_sort([plugin_name])
        except Exception as e:
            raise PluginDependencyError(f"Failed to resolve dependencies for {plugin_name}: {e}")
    
    def resolve_all_dependencies(self, plugin_names: List[str]) -> List[str]:
        """
        Resolve dependencies for multiple plugins.
        
        Args:
            plugin_names: List of plugin names
            
        Returns:
            List of plugin names in dependency order
            
        Raises:
            PluginDependencyError: If dependencies cannot be resolved
        """
        try:
            return self._topological_sort(plugin_names)
        except Exception as e:
            raise PluginDependencyError(f"Failed to resolve dependencies: {e}")
    
    def validate_dependencies(self, plugin_name: str) -> List[str]:
        """
        Validate that all dependencies are satisfied.
        
        Args:
            plugin_name: Plugin to validate
            
        Returns:
            List of missing dependency names (empty if all satisfied)
        """
        missing_deps = []
        dependencies = self._dependencies.get(plugin_name, [])
        
        for dep in dependencies:
            if dep.name not in self._plugins:
                if not dep.optional:
                    missing_deps.append(dep.name)
            else:
                # Check version compatibility if specified
                if dep.version:
                    dep_metadata = self._metadata.get(dep.name)
                    if dep_metadata and not self._is_version_compatible(dep_metadata.version, dep.version):
                        missing_deps.append(f"{dep.name} (version {dep.version} required, got {dep_metadata.version})")
        
        return missing_deps
    
    def update_plugin_state(self, plugin_name: str, state: PluginState, error_message: Optional[str] = None):
        """Update plugin state"""
        if plugin_name in self._metadata:
            self._metadata[plugin_name].state = state
            if error_message:
                self._metadata[plugin_name].error_message = error_message
            self._notify_state_change(plugin_name, state)
    
    def add_state_listener(self, listener: callable):
        """Add a listener for plugin state changes"""
        self._state_listeners.append(listener)
    
    def remove_state_listener(self, listener: callable):
        """Remove a state change listener"""
        if listener in self._state_listeners:
            self._state_listeners.remove(listener)
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            "total_plugins": len(self._plugins),
            "by_type": defaultdict(int),
            "by_state": defaultdict(int),
            "total_dependencies": 0
        }
        
        for metadata in self._metadata.values():
            stats["by_type"][metadata.plugin_type] += 1
            stats["by_state"][metadata.state] += 1
            stats["total_dependencies"] += len(metadata.dependencies)
        
        return dict(stats)
    
    def search_plugins(self, query: str) -> List[str]:
        """
        Search plugins by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching plugin names
        """
        query = query.lower()
        matches = []
        
        for name, metadata in self._metadata.items():
            # Search in name and display name
            if query in name.lower() or query in metadata.display_name.lower():
                matches.append(name)
                continue
            
            # Search in description
            if query in metadata.description.lower():
                matches.append(name)
                continue
            
            # Search in tags if available
            plugin = self._plugins.get(name)
            if plugin:
                capabilities = plugin.get_capabilities()
                if any(query in tag.lower() for tag in capabilities.tags):
                    matches.append(name)
        
        return matches
    
    def _validate_plugin_metadata(self, metadata: PluginMetadata):
        """Validate plugin metadata"""
        if not metadata.name:
            raise PluginError("Plugin name is required")
        
        if not metadata.version:
            raise PluginError("Plugin version is required")
        
        # Additional validation can be added here
    
    def _topological_sort(self, target_plugins: List[str]) -> List[str]:
        """
        Perform topological sort to resolve dependencies.
        
        Args:
            target_plugins: Plugins to include in sort
            
        Returns:
            List of plugins in dependency order
        """
        # Build graph of dependencies
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        all_plugins = set()
        
        # Add target plugins and their dependencies recursively
        queue = deque(target_plugins)
        visited = set()
        
        while queue:
            plugin_name = queue.popleft()
            if plugin_name in visited:
                continue
            visited.add(plugin_name)
            
            if plugin_name not in self._plugins:
                # Check if it's an optional dependency
                continue
            
            all_plugins.add(plugin_name)
            dependencies = self._dependencies.get(plugin_name, [])
            
            for dep in dependencies:
                if dep.name in self._plugins:
                    graph[dep.name].append(plugin_name)
                    in_degree[plugin_name] += 1
                    queue.append(dep.name)
                    all_plugins.add(dep.name)
                elif not dep.optional:
                    raise PluginDependencyError(f"Required dependency {dep.name} not found for plugin {plugin_name}")
        
        # Initialize in-degree for all plugins
        for plugin in all_plugins:
            if plugin not in in_degree:
                in_degree[plugin] = 0
        
        # Kahn's algorithm for topological sorting
        queue = deque([plugin for plugin in all_plugins if in_degree[plugin] == 0])
        result = []
        
        while queue:
            plugin = queue.popleft()
            result.append(plugin)
            
            for dependent in graph[plugin]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(all_plugins):
            remaining = all_plugins - set(result)
            raise PluginDependencyError(f"Circular dependency detected among plugins: {remaining}")
        
        return result
    
    def _is_version_compatible(self, available_version: str, required_version: str) -> bool:
        """
        Check if available version satisfies requirement.
        
        Simple version comparison - can be enhanced with proper semver parsing.
        """
        # Simplified version comparison
        # In production, use proper semver library
        try:
            available_parts = [int(x) for x in available_version.split('.')]
            required_parts = [int(x) for x in required_version.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(available_parts), len(required_parts))
            available_parts.extend([0] * (max_len - len(available_parts)))
            required_parts.extend([0] * (max_len - len(required_parts)))
            
            return available_parts >= required_parts
        except (ValueError, AttributeError):
            # If version parsing fails, assume compatible
            return True
    
    def _notify_state_change(self, plugin_name: str, state: PluginState):
        """Notify listeners about plugin state changes"""
        for listener in self._state_listeners:
            try:
                listener(plugin_name, state)
            except Exception as e:
                logger.error(f"Error in state change listener: {e}")


# Global plugin registry instance
registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance"""
    return registry