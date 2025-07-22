"""
Plugin System for Korea Public Open API Platform.

This package provides a flexible plugin architecture for dynamically adding
new public data API integrations without modifying the core application.

Key Components:
- Plugin Base Classes: Define contracts for plugins
- Plugin Manager: Handles discovery, loading, and lifecycle
- Plugin Registry: Maintains plugin information and dependencies  
- Plugin Configuration: Manages plugin-specific settings
"""

from .base import BasePlugin, PluginMetadata, PluginState
from .manager import PluginManager
from .registry import PluginRegistry
from .loader import PluginLoader
from .config import PluginConfig

__all__ = [
    "BasePlugin",
    "PluginMetadata", 
    "PluginState",
    "PluginManager",
    "PluginRegistry",
    "PluginLoader",
    "PluginConfig"
]