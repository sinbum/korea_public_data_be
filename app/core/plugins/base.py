"""
Base plugin classes and interfaces.

Defines the core contracts that all plugins must implement to integrate
with the Korea Public Open API platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from ..interfaces.base_api_client import BaseAPIClient
from ..interfaces.base_repository import BaseRepository
from ..interfaces.base_service import BaseService

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    """Plugin lifecycle states"""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class PluginType(str, Enum):
    """Types of plugins supported by the platform"""
    DATA_SOURCE = "data_source"  # New public data API integration
    PROCESSOR = "processor"      # Data processing and transformation
    EXPORTER = "exporter"        # Data export functionality
    MIDDLEWARE = "middleware"    # Request/response middleware
    EXTENSION = "extension"      # General platform extensions


class PluginDependency(BaseModel):
    """Represents a plugin dependency"""
    name: str = Field(..., description="Dependency plugin name")
    version: Optional[str] = Field(None, description="Required version constraint")
    optional: bool = Field(False, description="Whether dependency is optional")
    
    def __str__(self) -> str:
        version_str = f">={self.version}" if self.version else "*"
        optional_str = " (optional)" if self.optional else ""
        return f"{self.name} {version_str}{optional_str}"


class PluginMetadata(BaseModel):
    """Plugin metadata and configuration"""
    name: str = Field(..., description="Unique plugin identifier")
    display_name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version (semver)")
    description: str = Field("", description="Plugin description")
    author: str = Field("", description="Plugin author")
    license: str = Field("", description="Plugin license")
    homepage: Optional[str] = Field(None, description="Plugin homepage URL")
    
    # Plugin type and capabilities
    plugin_type: PluginType = Field(..., description="Type of plugin")
    api_version: str = Field("1.0.0", description="Required platform API version")
    
    # Dependencies
    dependencies: List[PluginDependency] = Field(default_factory=list, description="Plugin dependencies")
    platform_dependencies: List[str] = Field(default_factory=list, description="Required platform features")
    
    # Configuration
    config_schema: Optional[Dict[str, Any]] = Field(None, description="Configuration schema (JSON Schema)")
    default_config: Dict[str, Any] = Field(default_factory=dict, description="Default configuration values")
    
    # Runtime information (set by plugin system)
    loaded_at: Optional[datetime] = Field(None, description="When plugin was loaded")
    state: PluginState = Field(PluginState.DISCOVERED, description="Current plugin state")
    error_message: Optional[str] = Field(None, description="Last error message")
    
    class Config:
        use_enum_values = True


class PluginCapabilities(BaseModel):
    """Defines what capabilities a plugin provides"""
    provides_api_client: bool = Field(False, description="Provides API client implementation")
    provides_models: bool = Field(False, description="Provides data models")
    provides_repository: bool = Field(False, description="Provides repository implementation")
    provides_service: bool = Field(False, description="Provides service implementation")
    provides_router: bool = Field(False, description="Provides REST API endpoints")
    provides_middleware: bool = Field(False, description="Provides middleware")
    provides_jobs: bool = Field(False, description="Provides background jobs")
    
    # Data source specific capabilities
    supports_pagination: bool = Field(False, description="Supports paginated data fetching")
    supports_filtering: bool = Field(False, description="Supports data filtering")
    supports_search: bool = Field(False, description="Supports text search")
    supports_real_time: bool = Field(False, description="Supports real-time data")
    
    # Export capabilities
    export_formats: List[str] = Field(default_factory=list, description="Supported export formats")
    
    # Additional metadata
    supported_data_types: List[str] = Field(default_factory=list, description="Types of data handled")
    tags: List[str] = Field(default_factory=list, description="Plugin tags for categorization")


class PluginInterface(ABC):
    """Base interface that all plugins must implement"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> PluginCapabilities:
        """Return plugin capabilities"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin with given configuration.
        
        Args:
            config: Plugin-specific configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """
        Cleanup plugin resources.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform plugin health check.
        
        Returns:
            Health status information
        """
        pass


class BasePlugin(PluginInterface):
    """
    Base implementation of a plugin.
    
    Provides common functionality that most plugins will need.
    """
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.config: Dict[str, Any] = {}
        self.is_initialized = False
        self.logger = logging.getLogger(f"plugin.{metadata.name}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return self.metadata
    
    def get_capabilities(self) -> PluginCapabilities:
        """Return plugin capabilities (override in subclasses)"""
        return PluginCapabilities()
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        try:
            self.config = config
            await self._initialize_impl()
            self.is_initialized = True
            self.logger.info(f"Plugin {self.metadata.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {self.metadata.name}: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Cleanup plugin resources"""
        try:
            await self._cleanup_impl()
            self.is_initialized = False
            self.logger.info(f"Plugin {self.metadata.name} cleaned up successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup plugin {self.metadata.name}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Perform basic health check"""
        return {
            "plugin": self.metadata.name,
            "version": self.metadata.version,
            "state": self.metadata.state,
            "initialized": self.is_initialized,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _initialize_impl(self):
        """Override this method for plugin-specific initialization"""
        pass
    
    async def _cleanup_impl(self):
        """Override this method for plugin-specific cleanup"""
        pass


class DataSourcePlugin(BasePlugin):
    """
    Base class for data source plugins.
    
    Data source plugins integrate new public data APIs into the platform.
    """
    
    @abstractmethod
    def get_api_client_class(self) -> Type[BaseAPIClient]:
        """Return the API client class provided by this plugin"""
        pass
    
    @abstractmethod  
    def get_model_classes(self) -> Dict[str, Type]:
        """Return domain model classes provided by this plugin"""
        pass
    
    @abstractmethod
    def get_repository_class(self) -> Type[BaseRepository]:
        """Return repository class provided by this plugin"""
        pass
    
    @abstractmethod
    def get_service_class(self) -> Type[BaseService]:
        """Return service class provided by this plugin"""
        pass
    
    def get_router_module(self) -> Optional[str]:
        """Return router module path (optional)"""
        return None
    
    def get_capabilities(self) -> PluginCapabilities:
        """Return data source plugin capabilities"""
        return PluginCapabilities(
            provides_api_client=True,
            provides_models=True,
            provides_repository=True,
            provides_service=True,
            provides_router=True,
            supports_pagination=True,
            supports_filtering=True
        )


class ProcessorPlugin(BasePlugin):
    """
    Base class for data processor plugins.
    
    Processor plugins transform, enrich, or validate data.
    """
    
    @abstractmethod
    async def process_data(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        Process incoming data.
        
        Args:
            data: Input data to process
            context: Processing context
            
        Returns:
            Processed data
        """
        pass
    
    def get_capabilities(self) -> PluginCapabilities:
        """Return processor plugin capabilities"""
        return PluginCapabilities(
            provides_middleware=True
        )


class ExporterPlugin(BasePlugin):
    """
    Base class for data exporter plugins.
    
    Exporter plugins provide data export functionality in various formats.
    """
    
    @abstractmethod
    async def export_data(self, data: Any, format: str, options: Dict[str, Any]) -> bytes:
        """
        Export data in specified format.
        
        Args:
            data: Data to export
            format: Export format
            options: Export options
            
        Returns:
            Exported data as bytes
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported export formats"""
        pass
    
    def get_capabilities(self) -> PluginCapabilities:
        """Return exporter plugin capabilities"""
        formats = self.get_supported_formats()
        return PluginCapabilities(
            export_formats=formats
        )


class PluginError(Exception):
    """Base exception for plugin-related errors"""
    
    def __init__(self, message: str, plugin_name: Optional[str] = None):
        super().__init__(message)
        self.plugin_name = plugin_name


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load"""
    pass


class PluginInitializationError(PluginError):
    """Raised when a plugin fails to initialize"""
    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are not satisfied"""
    pass


class PluginConfigurationError(PluginError):
    """Raised when plugin configuration is invalid"""
    pass