"""
Data Source Registry - central registry for managing data sources.

Provides registration, discovery, and lifecycle management for data sources
that are loaded from plugins or configured statically.
"""

from typing import Dict, List, Optional, Set, Any, Type
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from ..interfaces.base_api_client import BaseAPIClient
from ..interfaces.base_repository import BaseRepository
from ..interfaces.base_service import BaseService
from ..plugins.base import DataSourcePlugin

logger = logging.getLogger(__name__)


class DataSourceStatus(str, Enum):
    """Data source status enumeration"""
    UNKNOWN = "unknown"
    REGISTERING = "registering"
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class DataSourceType(str, Enum):
    """Types of data sources"""
    GOVERNMENT_API = "government_api"     # Government public data APIs
    PRIVATE_API = "private_api"           # Private/commercial APIs
    DATABASE = "database"                 # Direct database connections
    FILE_SYSTEM = "file_system"           # File-based data sources
    WEB_SCRAPER = "web_scraper"          # Web scraping sources
    RSS_FEED = "rss_feed"                # RSS/Atom feeds
    WEBHOOK = "webhook"                   # Webhook-based sources
    PLUGIN = "plugin"                     # Plugin-provided sources


class DataSourceCapabilities(BaseModel):
    """Capabilities provided by a data source"""
    supports_pagination: bool = Field(False, description="Supports paginated data retrieval")
    supports_filtering: bool = Field(False, description="Supports data filtering")
    supports_sorting: bool = Field(False, description="Supports data sorting")
    supports_search: bool = Field(False, description="Supports text search")
    supports_real_time: bool = Field(False, description="Supports real-time data")
    supports_streaming: bool = Field(False, description="Supports data streaming")
    supports_webhooks: bool = Field(False, description="Supports webhook notifications")
    supports_caching: bool = Field(True, description="Supports data caching")
    
    # Data format capabilities
    input_formats: List[str] = Field(default_factory=list, description="Supported input data formats")
    output_formats: List[str] = Field(default_factory=list, description="Supported output data formats")
    
    # Rate limiting information
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit per minute")
    rate_limit_per_hour: Optional[int] = Field(None, description="Rate limit per hour")
    rate_limit_per_day: Optional[int] = Field(None, description="Rate limit per day")
    
    # Data categories supported
    data_categories: List[str] = Field(default_factory=list, description="Categories of data provided")


class DataSourceMetrics(BaseModel):
    """Metrics and statistics for a data source"""
    total_requests: int = Field(0, description="Total API requests made")
    successful_requests: int = Field(0, description="Successful API requests")
    failed_requests: int = Field(0, description="Failed API requests")
    average_response_time: float = Field(0.0, description="Average response time in seconds")
    last_request_time: Optional[datetime] = Field(None, description="Last request timestamp")
    last_success_time: Optional[datetime] = Field(None, description="Last successful request timestamp")
    last_error_time: Optional[datetime] = Field(None, description="Last error timestamp")
    last_error_message: Optional[str] = Field(None, description="Last error message")
    uptime_percentage: float = Field(100.0, description="Uptime percentage")
    
    # Data metrics
    total_records_fetched: int = Field(0, description="Total records fetched")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate percentage")
    data_freshness_hours: Optional[float] = Field(None, description="Data freshness in hours")


class DataSourceInfo(BaseModel):
    """Information about a registered data source"""
    # Basic information
    name: str = Field(..., description="Unique data source name")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field("", description="Data source description")
    version: str = Field("1.0.0", description="Data source version")
    
    # Classification
    source_type: DataSourceType = Field(..., description="Type of data source")
    provider: str = Field("", description="Data provider organization")
    category: str = Field("", description="Data category (e.g., business, statistics)")
    
    # Technical details
    base_url: Optional[str] = Field(None, description="Base API URL")
    api_key_required: bool = Field(False, description="Whether API key is required")
    authentication_type: Optional[str] = Field(None, description="Authentication method")
    
    # Plugin information
    plugin_name: Optional[str] = Field(None, description="Source plugin name")
    plugin_version: Optional[str] = Field(None, description="Source plugin version")
    
    # Capabilities and configuration
    capabilities: DataSourceCapabilities = Field(default_factory=DataSourceCapabilities)
    default_config: Dict[str, Any] = Field(default_factory=dict, description="Default configuration")
    required_config_keys: List[str] = Field(default_factory=list, description="Required configuration keys")
    
    # Runtime information
    status: DataSourceStatus = Field(DataSourceStatus.UNKNOWN, description="Current status")
    registered_at: datetime = Field(default_factory=datetime.utcnow, description="Registration timestamp")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Service class references
    api_client_class: Optional[Type[BaseAPIClient]] = Field(None, description="API client class")
    repository_class: Optional[Type[BaseRepository]] = Field(None, description="Repository class")
    service_class: Optional[Type[BaseService]] = Field(None, description="Service class")
    
    # Metrics
    metrics: DataSourceMetrics = Field(default_factory=DataSourceMetrics)
    
    class Config:
        arbitrary_types_allowed = True


class DataSourceRegistry:
    """
    Central registry for managing data sources.
    
    Handles registration, discovery, and metadata management for all
    data sources in the platform.
    """
    
    def __init__(self):
        self._data_sources: Dict[str, DataSourceInfo] = {}
        self._data_sources_by_type: Dict[DataSourceType, Set[str]] = {}
        self._data_sources_by_category: Dict[str, Set[str]] = {}
        self._data_sources_by_provider: Dict[str, Set[str]] = {}
        self._plugin_sources: Dict[str, str] = {}  # plugin_name -> data_source_name
        
        # Initialize category mappings
        for ds_type in DataSourceType:
            self._data_sources_by_type[ds_type] = set()
    
    def register_data_source(self, data_source_info: DataSourceInfo) -> bool:
        """
        Register a new data source.
        
        Args:
            data_source_info: Data source information
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            name = data_source_info.name
            
            if name in self._data_sources:
                logger.warning(f"Data source {name} is already registered")
                return False
            
            # Validate data source info
            self._validate_data_source_info(data_source_info)
            
            # Register in main registry
            self._data_sources[name] = data_source_info
            
            # Update category mappings
            self._data_sources_by_type[data_source_info.source_type].add(name)
            
            if data_source_info.category:
                if data_source_info.category not in self._data_sources_by_category:
                    self._data_sources_by_category[data_source_info.category] = set()
                self._data_sources_by_category[data_source_info.category].add(name)
            
            if data_source_info.provider:
                if data_source_info.provider not in self._data_sources_by_provider:
                    self._data_sources_by_provider[data_source_info.provider] = set()
                self._data_sources_by_provider[data_source_info.provider].add(name)
            
            # Track plugin sources
            if data_source_info.plugin_name:
                self._plugin_sources[data_source_info.plugin_name] = name
            
            data_source_info.status = DataSourceStatus.REGISTERED
            data_source_info.last_updated = datetime.utcnow()
            
            logger.info(f"Registered data source: {name} ({data_source_info.source_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register data source {data_source_info.name}: {e}")
            return False
    
    def register_from_plugin(self, plugin: DataSourcePlugin) -> bool:
        """
        Register a data source from a plugin.
        
        Args:
            plugin: Data source plugin instance
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            metadata = plugin.get_metadata()
            capabilities = plugin.get_capabilities()
            
            # Create data source info from plugin
            data_source_info = DataSourceInfo(
                name=metadata.name,
                display_name=metadata.display_name,
                description=metadata.description,
                version=metadata.version,
                source_type=DataSourceType.PLUGIN,
                plugin_name=metadata.name,
                plugin_version=metadata.version,
                api_client_class=plugin.get_api_client_class(),
                repository_class=plugin.get_repository_class(),
                service_class=plugin.get_service_class(),
                capabilities=DataSourceCapabilities(
                    supports_pagination=capabilities.supports_pagination,
                    supports_filtering=capabilities.supports_filtering,
                    supports_search=capabilities.supports_search,
                    supports_real_time=capabilities.supports_real_time,
                    data_categories=capabilities.supported_data_types
                ),
                default_config=metadata.default_config
            )
            
            return self.register_data_source(data_source_info)
            
        except Exception as e:
            logger.error(f"Failed to register data source from plugin {plugin.get_metadata().name}: {e}")
            return False
    
    def unregister_data_source(self, name: str) -> bool:
        """
        Unregister a data source.
        
        Args:
            name: Data source name
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if name not in self._data_sources:
                logger.warning(f"Data source {name} is not registered")
                return False
            
            data_source_info = self._data_sources[name]
            
            # Remove from category mappings
            self._data_sources_by_type[data_source_info.source_type].discard(name)
            
            if data_source_info.category:
                self._data_sources_by_category.get(data_source_info.category, set()).discard(name)
            
            if data_source_info.provider:
                self._data_sources_by_provider.get(data_source_info.provider, set()).discard(name)
            
            # Remove from plugin tracking
            if data_source_info.plugin_name:
                self._plugin_sources.pop(data_source_info.plugin_name, None)
            
            # Remove from main registry
            del self._data_sources[name]
            
            logger.info(f"Unregistered data source: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister data source {name}: {e}")
            return False
    
    def get_data_source(self, name: str) -> Optional[DataSourceInfo]:
        """
        Get data source information by name.
        
        Args:
            name: Data source name
            
        Returns:
            Data source information or None if not found
        """
        return self._data_sources.get(name)
    
    def list_data_sources(
        self,
        source_type: Optional[DataSourceType] = None,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[DataSourceStatus] = None
    ) -> List[str]:
        """
        List data sources with optional filtering.
        
        Args:
            source_type: Filter by source type
            category: Filter by category
            provider: Filter by provider
            status: Filter by status
            
        Returns:
            List of data source names matching criteria
        """
        candidates = set(self._data_sources.keys())
        
        # Apply filters
        if source_type:
            candidates &= self._data_sources_by_type.get(source_type, set())
        
        if category:
            candidates &= self._data_sources_by_category.get(category, set())
        
        if provider:
            candidates &= self._data_sources_by_provider.get(provider, set())
        
        if status:
            candidates = {
                name for name in candidates
                if self._data_sources[name].status == status
            }
        
        return sorted(list(candidates))
    
    def get_data_sources_by_plugin(self, plugin_name: str) -> List[str]:
        """
        Get data sources provided by a specific plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            List of data source names from the plugin
        """
        return [
            name for name, info in self._data_sources.items()
            if info.plugin_name == plugin_name
        ]
    
    def update_data_source_status(self, name: str, status: DataSourceStatus, message: Optional[str] = None):
        """
        Update data source status.
        
        Args:
            name: Data source name
            status: New status
            message: Optional status message
        """
        if name in self._data_sources:
            self._data_sources[name].status = status
            self._data_sources[name].last_updated = datetime.utcnow()
            
            if message and status == DataSourceStatus.ERROR:
                self._data_sources[name].metrics.last_error_message = message
                self._data_sources[name].metrics.last_error_time = datetime.utcnow()
    
    def update_data_source_metrics(self, name: str, metrics: DataSourceMetrics):
        """
        Update data source metrics.
        
        Args:
            name: Data source name
            metrics: Updated metrics
        """
        if name in self._data_sources:
            self._data_sources[name].metrics = metrics
            self._data_sources[name].last_updated = datetime.utcnow()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Registry statistics
        """
        stats = {
            "total_data_sources": len(self._data_sources),
            "by_type": {ds_type.value: len(sources) for ds_type, sources in self._data_sources_by_type.items()},
            "by_status": {},
            "by_category": {cat: len(sources) for cat, sources in self._data_sources_by_category.items()},
            "by_provider": {prov: len(sources) for prov, sources in self._data_sources_by_provider.items()},
            "plugin_sources": len(self._plugin_sources)
        }
        
        # Count by status
        for info in self._data_sources.values():
            status = info.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        return stats
    
    def search_data_sources(self, query: str) -> List[str]:
        """
        Search data sources by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching data source names
        """
        query = query.lower()
        matches = []
        
        for name, info in self._data_sources.items():
            # Search in name and display name
            if (query in name.lower() or 
                query in info.display_name.lower() or
                query in info.description.lower() or
                query in info.provider.lower() or
                query in info.category.lower()):
                matches.append(name)
                continue
            
            # Search in data categories
            if any(query in cat.lower() for cat in info.capabilities.data_categories):
                matches.append(name)
        
        return matches
    
    def get_data_sources_requiring_config(self) -> List[str]:
        """
        Get data sources that require configuration.
        
        Returns:
            List of data source names requiring configuration
        """
        return [
            name for name, info in self._data_sources.items()
            if info.required_config_keys or info.api_key_required
        ]
    
    def validate_data_source_config(self, name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration for a data source.
        
        Args:
            name: Data source name
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if name not in self._data_sources:
            errors.append(f"Data source {name} not found")
            return errors
        
        info = self._data_sources[name]
        
        # Check required config keys
        for required_key in info.required_config_keys:
            if required_key not in config:
                errors.append(f"Missing required configuration key: {required_key}")
        
        # Check API key if required
        if info.api_key_required and not config.get("api_key"):
            errors.append("API key is required but not provided")
        
        return errors
    
    def _validate_data_source_info(self, info: DataSourceInfo):
        """
        Validate data source information.
        
        Args:
            info: Data source information to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not info.name:
            raise ValueError("Data source name is required")
        
        if not info.display_name:
            raise ValueError("Data source display name is required")
        
        if not info.version:
            raise ValueError("Data source version is required")
        
        # Additional validation can be added here


# Global data source registry instance
_data_source_registry: Optional[DataSourceRegistry] = None


def get_data_source_registry() -> DataSourceRegistry:
    """Get the global data source registry instance"""
    global _data_source_registry
    if _data_source_registry is None:
        _data_source_registry = DataSourceRegistry()
    return _data_source_registry


def setup_data_source_registry(registry: Optional[DataSourceRegistry] = None) -> DataSourceRegistry:
    """Setup and return the global data source registry"""
    global _data_source_registry
    _data_source_registry = registry or DataSourceRegistry()
    return _data_source_registry