"""
Plugin Loader - handles plugin discovery and loading.

Discovers plugins from various sources (directories, packages, URLs)
and loads them into the plugin system.
"""

import os
import sys
import importlib
import importlib.util
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any, Type
import logging

from .base import (
    BasePlugin, PluginMetadata, PluginState, PluginType,
    PluginError, PluginLoadError, PluginConfigurationError
)
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginDiscoveryResult:
    """Result of plugin discovery operation"""
    
    def __init__(self):
        self.discovered: List[str] = []
        self.failed: List[str] = []
        self.errors: Dict[str, str] = {}
    
    def add_success(self, plugin_path: str):
        """Add successfully discovered plugin"""
        self.discovered.append(plugin_path)
    
    def add_failure(self, plugin_path: str, error: str):
        """Add failed plugin discovery"""
        self.failed.append(plugin_path)
        self.errors[plugin_path] = error
    
    @property
    def total_discovered(self) -> int:
        return len(self.discovered)
    
    @property
    def total_failed(self) -> int:
        return len(self.failed)


class PluginLoader:
    """
    Plugin loader and discovery system.
    
    Handles discovery, loading, and registration of plugins from various sources.
    """
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self.plugin_directories: List[Path] = []
        self.loaded_modules: Dict[str, Any] = {}
        
        # Default plugin directories
        self._setup_default_directories()
    
    def _setup_default_directories(self):
        """Setup default plugin discovery directories"""
        # Core application plugins directory
        app_plugins_dir = Path(__file__).parent.parent.parent / "plugins"
        if app_plugins_dir.exists():
            self.add_plugin_directory(app_plugins_dir)
        
        # User plugins directory (in project root)
        project_root = Path(__file__).parent.parent.parent.parent
        user_plugins_dir = project_root / "plugins"
        if user_plugins_dir.exists():
            self.add_plugin_directory(user_plugins_dir)
        
        # System plugins directory
        system_plugins_dir = Path("/etc/korea-public-api/plugins")
        if system_plugins_dir.exists():
            self.add_plugin_directory(system_plugins_dir)
    
    def add_plugin_directory(self, directory: Path):
        """Add a directory to search for plugins"""
        if directory.exists() and directory.is_dir():
            self.plugin_directories.append(directory)
            logger.info(f"Added plugin directory: {directory}")
        else:
            logger.warning(f"Plugin directory does not exist: {directory}")
    
    def discover_plugins(self) -> PluginDiscoveryResult:
        """
        Discover plugins from all configured directories.
        
        Returns:
            Discovery result with found and failed plugins
        """
        result = PluginDiscoveryResult()
        
        for directory in self.plugin_directories:
            logger.info(f"Discovering plugins in: {directory}")
            
            try:
                self._discover_in_directory(directory, result)
            except Exception as e:
                logger.error(f"Error discovering plugins in {directory}: {e}")
                result.add_failure(str(directory), str(e))
        
        logger.info(f"Plugin discovery completed: {result.total_discovered} found, {result.total_failed} failed")
        return result
    
    def _discover_in_directory(self, directory: Path, result: PluginDiscoveryResult):
        """Discover plugins in a specific directory"""
        for item in directory.iterdir():
            if item.is_dir():
                # Check for plugin directory
                plugin_file = item / "plugin.py"
                manifest_file = item / "manifest.json"
                
                if plugin_file.exists() and manifest_file.exists():
                    try:
                        self._validate_plugin_manifest(manifest_file)
                        result.add_success(str(item))
                    except Exception as e:
                        result.add_failure(str(item), str(e))
            
            elif item.suffix == ".py" and not item.name.startswith("_"):
                # Check for single-file plugin
                try:
                    if self._is_plugin_module(item):
                        result.add_success(str(item))
                except Exception as e:
                    result.add_failure(str(item), str(e))
    
    def _validate_plugin_manifest(self, manifest_file: Path):
        """Validate plugin manifest file"""
        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Required fields
            required_fields = ["name", "version", "plugin_type", "main_class"]
            for field in required_fields:
                if field not in manifest:
                    raise PluginConfigurationError(f"Missing required field: {field}")
            
            # Validate plugin type
            if manifest["plugin_type"] not in [t.value for t in PluginType]:
                raise PluginConfigurationError(f"Invalid plugin type: {manifest['plugin_type']}")
            
        except json.JSONDecodeError as e:
            raise PluginConfigurationError(f"Invalid JSON in manifest: {e}")
        except FileNotFoundError:
            raise PluginConfigurationError("Manifest file not found")
    
    def _is_plugin_module(self, file_path: Path) -> bool:
        """Check if a Python file is a plugin module"""
        try:
            spec = importlib.util.spec_from_file_location("temp_plugin", file_path)
            if spec is None:
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for plugin class that inherits from BasePlugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    return True
            
            return False
        except Exception:
            return False
    
    async def load_plugin(self, plugin_path: str) -> Optional[BasePlugin]:
        """
        Load a single plugin from path.
        
        Args:
            plugin_path: Path to plugin file or directory
            
        Returns:
            Loaded plugin instance or None if failed
        """
        path = Path(plugin_path)
        
        try:
            if path.is_dir():
                return await self._load_plugin_directory(path)
            elif path.is_file() and path.suffix == ".py":
                return await self._load_plugin_file(path)
            else:
                raise PluginLoadError(f"Invalid plugin path: {plugin_path}")
        
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return None
    
    async def _load_plugin_directory(self, plugin_dir: Path) -> BasePlugin:
        """Load plugin from directory with manifest"""
        manifest_file = plugin_dir / "manifest.json"
        plugin_file = plugin_dir / "plugin.py"
        
        if not manifest_file.exists():
            raise PluginLoadError("manifest.json not found")
        
        if not plugin_file.exists():
            raise PluginLoadError("plugin.py not found")
        
        # Load manifest
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        # Create metadata from manifest
        metadata = self._create_metadata_from_manifest(manifest)
        
        # Load plugin module
        module_name = f"plugin_{metadata.name}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules to support relative imports
        sys.modules[module_name] = module
        self.loaded_modules[metadata.name] = module
        
        spec.loader.exec_module(module)
        
        # Find and instantiate plugin class
        plugin_class_name = manifest.get("main_class")
        if not hasattr(module, plugin_class_name):
            raise PluginLoadError(f"Plugin class {plugin_class_name} not found")
        
        plugin_class = getattr(module, plugin_class_name)
        if not issubclass(plugin_class, BasePlugin):
            raise PluginLoadError(f"Plugin class {plugin_class_name} must inherit from BasePlugin")
        
        # Create plugin instance
        plugin = plugin_class(metadata)
        
        logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
        return plugin
    
    async def _load_plugin_file(self, plugin_file: Path) -> BasePlugin:
        """Load plugin from single Python file"""
        module_name = f"plugin_{plugin_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find plugin class
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, BasePlugin) and 
                attr != BasePlugin):
                plugin_class = attr
                break
        
        if plugin_class is None:
            raise PluginLoadError("No plugin class found")
        
        # Create instance with auto-generated metadata
        metadata = self._create_default_metadata(plugin_file.stem, plugin_class)
        plugin = plugin_class(metadata)
        
        self.loaded_modules[metadata.name] = module
        
        logger.info(f"Loaded plugin: {metadata.name}")
        return plugin
    
    def _create_metadata_from_manifest(self, manifest: Dict[str, Any]) -> PluginMetadata:
        """Create plugin metadata from manifest"""
        return PluginMetadata(
            name=manifest["name"],
            display_name=manifest.get("display_name", manifest["name"]),
            version=manifest["version"],
            description=manifest.get("description", ""),
            author=manifest.get("author", ""),
            license=manifest.get("license", ""),
            homepage=manifest.get("homepage"),
            plugin_type=PluginType(manifest["plugin_type"]),
            api_version=manifest.get("api_version", "1.0.0"),
            dependencies=[
                self._parse_dependency(dep) for dep in manifest.get("dependencies", [])
            ],
            platform_dependencies=manifest.get("platform_dependencies", []),
            config_schema=manifest.get("config_schema"),
            default_config=manifest.get("default_config", {})
        )
    
    def _create_default_metadata(self, name: str, plugin_class: Type[BasePlugin]) -> PluginMetadata:
        """Create default metadata for single-file plugins"""
        return PluginMetadata(
            name=name,
            display_name=name.replace("_", " ").title(),
            version="1.0.0",
            description=plugin_class.__doc__ or "",
            plugin_type=PluginType.EXTENSION,  # Default type
            api_version="1.0.0"
        )
    
    def _parse_dependency(self, dep_spec: Any) -> "PluginDependency":
        """Parse dependency specification from manifest"""
        from .base import PluginDependency
        
        if isinstance(dep_spec, str):
            return PluginDependency(name=dep_spec)
        elif isinstance(dep_spec, dict):
            return PluginDependency(**dep_spec)
        else:
            raise PluginConfigurationError(f"Invalid dependency specification: {dep_spec}")
    
    async def load_all_discovered_plugins(self, discovery_result: PluginDiscoveryResult) -> Dict[str, BasePlugin]:
        """
        Load all discovered plugins.
        
        Args:
            discovery_result: Result from discover_plugins()
            
        Returns:
            Dictionary of successfully loaded plugins
        """
        loaded_plugins = {}
        
        for plugin_path in discovery_result.discovered:
            try:
                plugin = await self.load_plugin(plugin_path)
                if plugin:
                    loaded_plugins[plugin.get_metadata().name] = plugin
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_path}: {e}")
        
        return loaded_plugins
    
    async def load_and_register_plugins(self) -> Dict[str, BasePlugin]:
        """
        Discover, load, and register all plugins.
        
        Returns:
            Dictionary of successfully loaded and registered plugins
        """
        # Discover plugins
        discovery_result = self.discover_plugins()
        
        # Load plugins
        loaded_plugins = await self.load_all_discovered_plugins(discovery_result)
        
        # Register plugins with registry
        registered_plugins = {}
        for plugin_name, plugin in loaded_plugins.items():
            if self.registry.register(plugin):
                registered_plugins[plugin_name] = plugin
            else:
                logger.error(f"Failed to register plugin: {plugin_name}")
        
        logger.info(f"Loaded and registered {len(registered_plugins)} plugins")
        return registered_plugins
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and remove from memory.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            # Unregister from registry first
            if not self.registry.unregister(plugin_name):
                return False
            
            # Remove from loaded modules
            if plugin_name in self.loaded_modules:
                module = self.loaded_modules.pop(plugin_name)
                module_name = getattr(module, '__name__', None)
                if module_name and module_name in sys.modules:
                    del sys.modules[module_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str, plugin_path: str) -> Optional[BasePlugin]:
        """
        Reload a plugin from disk.
        
        Args:
            plugin_name: Name of plugin to reload
            plugin_path: Path to plugin file/directory
            
        Returns:
            Reloaded plugin instance or None if failed
        """
        try:
            # Unload existing plugin
            if plugin_name in self.registry.get_all_plugins():
                if not self.unload_plugin(plugin_name):
                    logger.error(f"Failed to unload plugin {plugin_name} for reload")
                    return None
            
            # Load fresh instance
            plugin = asyncio.run(self.load_plugin(plugin_path))
            if plugin and self.registry.register(plugin):
                logger.info(f"Reloaded plugin: {plugin_name}")
                return plugin
            else:
                logger.error(f"Failed to register reloaded plugin: {plugin_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return None
    
    def get_plugin_module(self, plugin_name: str) -> Optional[Any]:
        """Get the loaded module for a plugin"""
        return self.loaded_modules.get(plugin_name)
    
    def get_loader_stats(self) -> Dict[str, Any]:
        """Get plugin loader statistics"""
        return {
            "plugin_directories": [str(d) for d in self.plugin_directories],
            "loaded_modules": list(self.loaded_modules.keys()),
            "total_directories": len(self.plugin_directories),
            "total_loaded_modules": len(self.loaded_modules)
        }