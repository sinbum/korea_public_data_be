"""
Plugin Configuration System - manages plugin-specific settings and global configuration.

Provides configuration management for the plugin system including:
- Global plugin system settings
- Per-plugin configuration
- Configuration validation
- Environment-based configuration loading
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class PluginDirectoryConfig(BaseModel):
    """Configuration for plugin directory scanning"""
    path: Path = Field(..., description="Directory path to scan for plugins")
    enabled: bool = Field(True, description="Whether this directory is enabled")
    recursive: bool = Field(True, description="Whether to scan subdirectories")
    watch_for_changes: bool = Field(False, description="Whether to watch for file changes")


class PluginSystemConfig(BaseModel):
    """Global plugin system configuration"""
    enabled: bool = Field(True, description="Whether plugin system is enabled")
    auto_discover: bool = Field(True, description="Automatically discover plugins on startup")
    auto_activate: bool = Field(False, description="Automatically activate discovered plugins")
    max_concurrent_loads: int = Field(5, description="Maximum concurrent plugin loads")
    load_timeout_seconds: int = Field(30, description="Plugin load timeout in seconds")
    dependency_timeout_seconds: int = Field(10, description="Dependency resolution timeout")
    
    # Security settings
    allow_external_plugins: bool = Field(False, description="Allow loading plugins from external sources")
    require_signature: bool = Field(False, description="Require plugin signature verification")
    sandbox_plugins: bool = Field(True, description="Run plugins in sandboxed environment")
    
    @validator('max_concurrent_loads')
    def validate_max_concurrent_loads(cls, v):
        if v < 1:
            raise ValueError("max_concurrent_loads must be at least 1")
        return v
    
    @validator('load_timeout_seconds')
    def validate_load_timeout(cls, v):
        if v < 1:
            raise ValueError("load_timeout_seconds must be at least 1")
        return v


class PluginInstanceConfig(BaseModel):
    """Configuration for a specific plugin instance"""
    enabled: bool = Field(True, description="Whether this plugin is enabled")
    auto_activate: bool = Field(True, description="Auto-activate this plugin")
    priority: int = Field(100, description="Plugin priority (lower = higher priority)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin-specific configuration")
    environment_overrides: Dict[str, str] = Field(default_factory=dict, description="Environment variable overrides")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 0:
            raise ValueError("Priority must be non-negative")
        return v


class PluginConfig(BaseModel):
    """Main plugin configuration container"""
    
    # System-wide settings
    system: PluginSystemConfig = Field(default_factory=PluginSystemConfig)
    
    # Plugin directories
    plugin_directories: List[Path] = Field(default_factory=list, description="Directories to search for plugins")
    
    # Per-plugin configurations
    plugins: Dict[str, PluginInstanceConfig] = Field(default_factory=dict, description="Per-plugin configurations")
    
    # Global plugin defaults
    default_plugin_config: Dict[str, Any] = Field(default_factory=dict, description="Default configuration for all plugins")
    
    def __init__(self, **data):
        super().__init__(**data)
        self._setup_default_directories()
    
    def _setup_default_directories(self):
        """Setup default plugin directories if none provided"""
        if not self.plugin_directories:
            # Application plugins directory
            app_plugins_dir = Path(__file__).parent.parent.parent / "plugins"
            self.plugin_directories.append(app_plugins_dir)
            
            # Project root plugins directory
            project_root = Path(__file__).parent.parent.parent.parent
            user_plugins_dir = project_root / "plugins"
            self.plugin_directories.append(user_plugins_dir)
            
            # System plugins directory (if exists)
            system_plugins_dir = Path("/etc/korea-public-api/plugins")
            if system_plugins_dir.exists():
                self.plugin_directories.append(system_plugins_dir)
    
    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin configuration or None if not found
        """
        plugin_config = self.plugins.get(plugin_name)
        if not plugin_config:
            return None
        
        # Merge default config with plugin-specific config
        config = self.default_plugin_config.copy()
        config.update(plugin_config.config)
        
        # Apply environment overrides
        for key, env_var in plugin_config.environment_overrides.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                config[key] = env_value
        
        return config
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """
        Set configuration for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: Configuration dictionary
        """
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = PluginInstanceConfig()
        
        self.plugins[plugin_name].config.update(config)
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin is enabled, False otherwise
        """
        if not self.system.enabled:
            return False
        
        plugin_config = self.plugins.get(plugin_name)
        return plugin_config.enabled if plugin_config else True
    
    def should_auto_activate_plugin(self, plugin_name: str) -> bool:
        """
        Check if a plugin should be auto-activated.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin should be auto-activated
        """
        if not self.system.auto_activate:
            return False
        
        plugin_config = self.plugins.get(plugin_name)
        return plugin_config.auto_activate if plugin_config else True
    
    def get_plugin_priority(self, plugin_name: str) -> int:
        """
        Get plugin priority.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin priority (lower = higher priority)
        """
        plugin_config = self.plugins.get(plugin_name)
        return plugin_config.priority if plugin_config else 100
    
    def add_plugin_directory(self, directory: Union[str, Path]):
        """
        Add a plugin directory.
        
        Args:
            directory: Directory path to add
        """
        dir_path = Path(directory)
        if dir_path not in self.plugin_directories:
            self.plugin_directories.append(dir_path)
    
    def remove_plugin_directory(self, directory: Union[str, Path]):
        """
        Remove a plugin directory.
        
        Args:
            directory: Directory path to remove
        """
        dir_path = Path(directory)
        if dir_path in self.plugin_directories:
            self.plugin_directories.remove(dir_path)
    
    def load_from_file(self, config_file: Union[str, Path]) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file (JSON)
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_path}")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update configuration
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            logger.info(f"Loaded plugin configuration from {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
            return False
    
    def save_to_file(self, config_file: Union[str, Path]) -> bool:
        """
        Save configuration to file.
        
        Args:
            config_file: Path to save configuration file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to JSON-serializable format
            data = self.dict()
            
            # Convert Path objects to strings
            if 'plugin_directories' in data:
                data['plugin_directories'] = [str(d) for d in data['plugin_directories']]
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved plugin configuration to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_file}: {e}")
            return False
    
    def load_from_environment(self, prefix: str = "PLUGIN_") -> bool:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # System configuration
            enabled = os.getenv(f"{prefix}SYSTEM_ENABLED")
            if enabled is not None:
                self.system.enabled = enabled.lower() in ('true', '1', 'yes', 'on')
            
            auto_discover = os.getenv(f"{prefix}AUTO_DISCOVER")
            if auto_discover is not None:
                self.system.auto_discover = auto_discover.lower() in ('true', '1', 'yes', 'on')
            
            auto_activate = os.getenv(f"{prefix}AUTO_ACTIVATE")
            if auto_activate is not None:
                self.system.auto_activate = auto_activate.lower() in ('true', '1', 'yes', 'on')
            
            # Plugin directories
            plugin_dirs = os.getenv(f"{prefix}DIRECTORIES")
            if plugin_dirs:
                self.plugin_directories = [Path(d.strip()) for d in plugin_dirs.split(':') if d.strip()]
            
            logger.info("Loaded plugin configuration from environment variables")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration from environment: {e}")
            return False
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate plugin directories
        for directory in self.plugin_directories:
            if not directory.exists():
                errors.append(f"Plugin directory does not exist: {directory}")
            elif not directory.is_dir():
                errors.append(f"Plugin directory is not a directory: {directory}")
        
        # Validate plugin configurations
        for plugin_name, plugin_config in self.plugins.items():
            if not plugin_name:
                errors.append("Plugin name cannot be empty")
            
            if plugin_config.priority < 0:
                errors.append(f"Plugin {plugin_name} has invalid priority: {plugin_config.priority}")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Configuration summary
        """
        return {
            "system_enabled": self.system.enabled,
            "auto_discover": self.system.auto_discover,
            "auto_activate": self.system.auto_activate,
            "plugin_directories_count": len(self.plugin_directories),
            "plugin_directories": [str(d) for d in self.plugin_directories],
            "configured_plugins_count": len(self.plugins),
            "configured_plugins": list(self.plugins.keys()),
            "default_config_keys": list(self.default_plugin_config.keys())
        }


class PluginConfigManager:
    """
    Plugin configuration manager utility.
    
    Provides high-level configuration management operations.
    """
    
    def __init__(self, config: Optional[PluginConfig] = None):
        self.config = config or PluginConfig()
        self._config_file: Optional[Path] = None
    
    def load_config(
        self, 
        config_file: Optional[Union[str, Path]] = None,
        load_from_env: bool = True,
        env_prefix: str = "PLUGIN_"
    ) -> bool:
        """
        Load configuration from multiple sources.
        
        Args:
            config_file: Configuration file path (optional)
            load_from_env: Whether to load from environment variables
            env_prefix: Environment variable prefix
            
        Returns:
            True if any configuration was loaded successfully
        """
        success = False
        
        # Load from environment first (lowest priority)
        if load_from_env:
            if self.config.load_from_environment(env_prefix):
                success = True
        
        # Load from file (higher priority)
        if config_file:
            config_path = Path(config_file)
            self._config_file = config_path
            if self.config.load_from_file(config_path):
                success = True
        else:
            # Try default config file locations
            default_locations = [
                Path("plugins.json"),
                Path("config/plugins.json"),
                Path(".config/plugins.json"),
                Path.home() / ".korea-public-api" / "plugins.json"
            ]
            
            for location in default_locations:
                if location.exists():
                    self._config_file = location
                    if self.config.load_from_file(location):
                        success = True
                        break
        
        return success
    
    def save_config(self, config_file: Optional[Union[str, Path]] = None) -> bool:
        """
        Save current configuration to file.
        
        Args:
            config_file: Configuration file path (uses loaded file if not specified)
            
        Returns:
            True if saved successfully
        """
        target_file = config_file or self._config_file
        if not target_file:
            target_file = Path("plugins.json")
        
        return self.config.save_to_file(target_file)
    
    def create_plugin_config(
        self,
        plugin_name: str,
        enabled: bool = True,
        auto_activate: bool = True,
        priority: int = 100,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create configuration for a new plugin.
        
        Args:
            plugin_name: Name of the plugin
            enabled: Whether plugin is enabled
            auto_activate: Whether to auto-activate plugin
            priority: Plugin priority
            config: Plugin-specific configuration
            
        Returns:
            True if created successfully
        """
        try:
            plugin_config = PluginInstanceConfig(
                enabled=enabled,
                auto_activate=auto_activate,
                priority=priority,
                config=config or {}
            )
            
            self.config.plugins[plugin_name] = plugin_config
            logger.info(f"Created configuration for plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create plugin configuration for {plugin_name}: {e}")
            return False
    
    def update_plugin_config(
        self,
        plugin_name: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update configuration for an existing plugin.
        
        Args:
            plugin_name: Name of the plugin
            updates: Configuration updates
            
        Returns:
            True if updated successfully
        """
        try:
            if plugin_name not in self.config.plugins:
                self.config.plugins[plugin_name] = PluginInstanceConfig()
            
            plugin_config = self.config.plugins[plugin_name]
            
            # Update configuration fields
            for key, value in updates.items():
                if key == 'config':
                    plugin_config.config.update(value)
                elif hasattr(plugin_config, key):
                    setattr(plugin_config, key, value)
            
            logger.info(f"Updated configuration for plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update plugin configuration for {plugin_name}: {e}")
            return False
    
    def remove_plugin_config(self, plugin_name: str) -> bool:
        """
        Remove configuration for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if removed successfully
        """
        try:
            if plugin_name in self.config.plugins:
                del self.config.plugins[plugin_name]
                logger.info(f"Removed configuration for plugin: {plugin_name}")
                return True
            else:
                logger.warning(f"Plugin configuration not found: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove plugin configuration for {plugin_name}: {e}")
            return False
    
    def validate_all(self) -> bool:
        """
        Validate all configuration.
        
        Returns:
            True if configuration is valid
        """
        errors = self.config.validate_configuration()
        if errors:
            logger.error(f"Configuration validation errors: {errors}")
            return False
        
        logger.info("Plugin configuration validation passed")
        return True


# Global plugin config instance
_plugin_config: Optional[PluginConfig] = None


def get_plugin_config() -> PluginConfig:
    """Get the global plugin configuration instance"""
    global _plugin_config
    if _plugin_config is None:
        _plugin_config = PluginConfig()
    return _plugin_config


def setup_plugin_config(config: Optional[PluginConfig] = None) -> PluginConfig:
    """Setup and return the global plugin configuration"""
    global _plugin_config
    _plugin_config = config or PluginConfig()
    return _plugin_config