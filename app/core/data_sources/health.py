"""
Data Source Health Monitor - monitors health and performance of data sources.

Provides health checking, performance monitoring, and alerting capabilities
for registered data sources.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging

from .registry import DataSourceRegistry, DataSourceStatus
from .factory import DataSourceFactory

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class HealthCheckResult(BaseModel):
    """Result of a health check"""
    status: HealthStatus = Field(..., description="Overall health status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    last_check_time: datetime = Field(default_factory=datetime.utcnow, description="Last check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")
    
    # Performance metrics
    success_rate: float = Field(0.0, description="Success rate percentage")
    average_response_time: float = Field(0.0, description="Average response time in milliseconds")
    error_count: int = Field(0, description="Number of errors in monitoring period")
    uptime_percentage: float = Field(100.0, description="Uptime percentage")


class HealthThresholds(BaseModel):
    """Health check thresholds for determining status"""
    response_time_warning_ms: float = Field(5000, description="Response time warning threshold")
    response_time_critical_ms: float = Field(10000, description="Response time critical threshold")
    success_rate_warning: float = Field(95.0, description="Success rate warning threshold")
    success_rate_critical: float = Field(90.0, description="Success rate critical threshold")
    error_rate_warning: float = Field(5.0, description="Error rate warning threshold")
    error_rate_critical: float = Field(10.0, description="Error rate critical threshold")
    uptime_warning: float = Field(99.0, description="Uptime warning threshold")
    uptime_critical: float = Field(95.0, description="Uptime critical threshold")


class DataSourceHealthMonitor:
    """
    Health monitor for data sources.
    
    Monitors health, performance, and availability of registered data sources.
    """
    
    def __init__(
        self,
        registry: Optional[DataSourceRegistry] = None,
        factory: Optional[DataSourceFactory] = None
    ):
        self.registry = registry
        self.factory = factory
        
        # Health check results
        self._health_results: Dict[str, HealthCheckResult] = {}
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._thresholds = HealthThresholds()
        
        # Monitoring configuration
        self._monitored_sources: Set[str] = set()
        self._check_interval = 60  # seconds
        self._history_retention_hours = 24
        self._max_history_entries = 1440  # 24 hours worth of 1-minute checks
        
        # Performance tracking
        self._performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring statistics
        self._stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "warning_checks": 0,
            "critical_checks": 0,
            "error_checks": 0,
            "last_check_time": None,
            "monitoring_start_time": datetime.utcnow()
        }
        
        # Alert handlers
        self._alert_handlers: List[callable] = []
    
    async def start_monitoring(self, data_source_name: str) -> bool:
        """
        Start monitoring a data source.
        
        Args:
            data_source_name: Name of the data source to monitor
            
        Returns:
            True if monitoring started successfully
        """
        try:
            if not self.registry or not self.registry.get_data_source(data_source_name):
                logger.error(f"Data source not found: {data_source_name}")
                return False
            
            self._monitored_sources.add(data_source_name)
            
            # Initialize health history
            if data_source_name not in self._health_history:
                self._health_history[data_source_name] = []
            
            # Initialize performance metrics
            if data_source_name not in self._performance_metrics:
                self._performance_metrics[data_source_name] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_response_time": 0.0,
                    "min_response_time": float('inf'),
                    "max_response_time": 0.0,
                    "last_request_time": None
                }
            
            # Perform initial health check
            await self.check_health(data_source_name)
            
            logger.info(f"Started monitoring data source: {data_source_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring {data_source_name}: {e}")
            return False
    
    async def stop_monitoring(self, data_source_name: str) -> bool:
        """
        Stop monitoring a data source.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            True if monitoring stopped successfully
        """
        try:
            self._monitored_sources.discard(data_source_name)
            logger.info(f"Stopped monitoring data source: {data_source_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring {data_source_name}: {e}")
            return False
    
    async def check_health(self, data_source_name: str) -> Optional[HealthCheckResult]:
        """
        Perform health check for a specific data source.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            Health check result or None if failed
        """
        try:
            start_time = datetime.utcnow()
            
            # Get data source info
            if not self.registry:
                return None
            
            data_source_info = self.registry.get_data_source(data_source_name)
            if not data_source_info:
                logger.error(f"Data source not found: {data_source_name}")
                return None
            
            # Perform health check based on data source status
            if data_source_info.status != DataSourceStatus.ACTIVE:
                result = HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    error_message=f"Data source not active: {data_source_info.status}",
                    details={"data_source_status": data_source_info.status}
                )
            else:
                result = await self._perform_active_health_check(data_source_name, start_time)
            
            # Update health results
            self._health_results[data_source_name] = result
            
            # Add to history
            self._add_to_history(data_source_name, result)
            
            # Update statistics
            self._update_health_stats(result.status)
            
            # Check for alerts
            await self._check_alerts(data_source_name, result)
            
            logger.debug(f"Health check completed for {data_source_name}: {result.status}")
            return result
            
        except Exception as e:
            logger.error(f"Health check failed for {data_source_name}: {e}")
            
            # Create error result
            result = HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                error_message=str(e)
            )
            
            self._health_results[data_source_name] = result
            self._add_to_history(data_source_name, result)
            self._stats["error_checks"] += 1
            
            return result
    
    async def _perform_active_health_check(self, data_source_name: str, start_time: datetime) -> HealthCheckResult:
        """
        Perform health check for an active data source.
        
        Args:
            data_source_name: Name of the data source
            start_time: Check start time
            
        Returns:
            Health check result
        """
        try:
            # Try to create API client (basic connectivity test)
            if self.factory:
                api_client = self.factory.create_api_client(data_source_name, use_cache=False)
                if not api_client:
                    return HealthCheckResult(
                        status=HealthStatus.CRITICAL,
                        error_message="Failed to create API client"
                    )
                
                # Perform basic health check if client supports it
                if hasattr(api_client, 'health_check'):
                    try:
                        check_start = datetime.utcnow()
                        health_data = await api_client.health_check()
                        response_time = (datetime.utcnow() - check_start).total_seconds() * 1000
                        
                        # Determine status based on response time and thresholds
                        status = self._determine_health_status(response_time, health_data)
                        
                        return HealthCheckResult(
                            status=status,
                            response_time_ms=response_time,
                            details=health_data or {}
                        )
                    except Exception as e:
                        return HealthCheckResult(
                            status=HealthStatus.CRITICAL,
                            error_message=f"Health check call failed: {e}"
                        )
                else:
                    # Basic connectivity test
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        response_time_ms=response_time,
                        details={"check_type": "basic_connectivity"}
                    )
            else:
                return HealthCheckResult(
                    status=HealthStatus.WARNING,
                    error_message="Factory not available for health check"
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                error_message=f"Active health check failed: {e}"
            )
    
    def _determine_health_status(self, response_time_ms: float, health_data: Optional[Dict[str, Any]]) -> HealthStatus:
        """
        Determine health status based on response time and health data.
        
        Args:
            response_time_ms: Response time in milliseconds
            health_data: Additional health data
            
        Returns:
            Health status
        """
        # Check response time thresholds
        if response_time_ms >= self._thresholds.response_time_critical_ms:
            return HealthStatus.CRITICAL
        elif response_time_ms >= self._thresholds.response_time_warning_ms:
            return HealthStatus.WARNING
        
        # Check health data if available
        if health_data:
            if health_data.get('status') == 'error':
                return HealthStatus.CRITICAL
            elif health_data.get('status') == 'warning':
                return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def check_all_health(self) -> Dict[str, HealthCheckResult]:
        """
        Perform health check for all monitored data sources.
        
        Returns:
            Dictionary of health check results
        """
        results = {}
        
        # Check all monitored sources
        for data_source_name in self._monitored_sources.copy():
            result = await self.check_health(data_source_name)
            if result:
                results[data_source_name] = result
        
        self._stats["last_check_time"] = datetime.utcnow()
        return results
    
    async def get_health_status(self, data_source_name: str) -> Optional[HealthCheckResult]:
        """
        Get current health status for a data source.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            Current health status or None if not monitored
        """
        return self._health_results.get(data_source_name)
    
    async def get_all_health_status(self) -> Dict[str, HealthCheckResult]:
        """
        Get health status for all monitored data sources.
        
        Returns:
            Dictionary of health statuses
        """
        return self._health_results.copy()
    
    def get_health_history(self, data_source_name: str, hours: int = 24) -> List[HealthCheckResult]:
        """
        Get health history for a data source.
        
        Args:
            data_source_name: Name of the data source
            hours: Number of hours of history to return
            
        Returns:
            List of health check results
        """
        if data_source_name not in self._health_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            result for result in self._health_history[data_source_name]
            if result.last_check_time >= cutoff_time
        ]
    
    def get_performance_metrics(self, data_source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a data source.
        
        Args:
            data_source_name: Name of the data source
            
        Returns:
            Performance metrics or None if not available
        """
        if data_source_name not in self._performance_metrics:
            return None
        
        metrics = self._performance_metrics[data_source_name].copy()
        
        # Calculate derived metrics
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = (metrics["successful_requests"] / metrics["total_requests"]) * 100
            metrics["error_rate"] = (metrics["failed_requests"] / metrics["total_requests"]) * 100
            metrics["average_response_time"] = metrics["total_response_time"] / metrics["total_requests"]
        else:
            metrics["success_rate"] = 0.0
            metrics["error_rate"] = 0.0
            metrics["average_response_time"] = 0.0
        
        return metrics
    
    def record_request_metrics(
        self,
        data_source_name: str,
        success: bool,
        response_time_ms: float
    ):
        """
        Record request metrics for a data source.
        
        Args:
            data_source_name: Name of the data source
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
        """
        if data_source_name not in self._performance_metrics:
            return
        
        metrics = self._performance_metrics[data_source_name]
        
        metrics["total_requests"] += 1
        metrics["total_response_time"] += response_time_ms
        metrics["last_request_time"] = datetime.utcnow()
        
        if success:
            metrics["successful_requests"] += 1
        else:
            metrics["failed_requests"] += 1
        
        # Update min/max response times
        if response_time_ms < metrics["min_response_time"]:
            metrics["min_response_time"] = response_time_ms
        
        if response_time_ms > metrics["max_response_time"]:
            metrics["max_response_time"] = response_time_ms
    
    def set_thresholds(self, thresholds: HealthThresholds):
        """
        Set health check thresholds.
        
        Args:
            thresholds: New health check thresholds
        """
        self._thresholds = thresholds
        logger.info("Updated health check thresholds")
    
    def add_alert_handler(self, handler: callable):
        """
        Add an alert handler.
        
        Args:
            handler: Callable that receives (data_source_name, health_result)
        """
        self._alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: callable):
        """
        Remove an alert handler.
        
        Args:
            handler: Handler to remove
        """
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.
        
        Returns:
            Monitoring statistics
        """
        uptime = datetime.utcnow() - self._stats["monitoring_start_time"]
        
        return {
            **self._stats,
            "monitored_sources": len(self._monitored_sources),
            "monitored_source_names": list(self._monitored_sources),
            "monitoring_uptime_seconds": uptime.total_seconds(),
            "health_results_count": len(self._health_results),
            "history_entries": sum(len(history) for history in self._health_history.values())
        }
    
    def _add_to_history(self, data_source_name: str, result: HealthCheckResult):
        """Add health check result to history"""
        if data_source_name not in self._health_history:
            self._health_history[data_source_name] = []
        
        history = self._health_history[data_source_name]
        history.append(result)
        
        # Trim history if too long
        if len(history) > self._max_history_entries:
            history[:] = history[-self._max_history_entries:]
        
        # Remove old entries
        cutoff_time = datetime.utcnow() - timedelta(hours=self._history_retention_hours)
        history[:] = [r for r in history if r.last_check_time >= cutoff_time]
    
    def _update_health_stats(self, status: HealthStatus):
        """Update health statistics"""
        self._stats["total_checks"] += 1
        
        if status == HealthStatus.HEALTHY:
            self._stats["healthy_checks"] += 1
        elif status == HealthStatus.WARNING:
            self._stats["warning_checks"] += 1
        elif status == HealthStatus.CRITICAL:
            self._stats["critical_checks"] += 1
        else:
            self._stats["error_checks"] += 1
    
    async def _check_alerts(self, data_source_name: str, result: HealthCheckResult):
        """Check if alerts should be triggered"""
        if result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            for handler in self._alert_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data_source_name, result)
                    else:
                        handler(data_source_name, result)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")


# Global health monitor instance
_health_monitor: Optional[DataSourceHealthMonitor] = None


def get_health_monitor() -> DataSourceHealthMonitor:
    """Get the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DataSourceHealthMonitor()
    return _health_monitor


def setup_health_monitor(
    registry: Optional[DataSourceRegistry] = None,
    factory: Optional[DataSourceFactory] = None
) -> DataSourceHealthMonitor:
    """Setup and return the global health monitor"""
    global _health_monitor
    _health_monitor = DataSourceHealthMonitor(registry, factory)
    return _health_monitor