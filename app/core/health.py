"""
Comprehensive health check and monitoring system.

Provides health checks for all system components, metrics collection,
and monitoring endpoints for improved observability.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import psutil
import platform

from .database import db_manager, is_database_healthy, is_database_healthy_async
from .cache import cache_manager
from .config import settings

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["status"] = self.status.value
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class SystemHealth:
    """Overall system health summary"""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime
    version: str = "1.0.0"
    environment: str = "development"
    uptime_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "environment": self.environment,
            "uptime_seconds": self.uptime_seconds,
            "summary": {
                "total_checks": len(self.checks),
                "healthy": len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
                "degraded": len([c for c in self.checks if c.status == HealthStatus.DEGRADED]),
                "unhealthy": len([c for c in self.checks if c.status == HealthStatus.UNHEALTHY])
            }
        }


class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks: Dict[str, Callable] = {}
        self.async_checks: Dict[str, Callable] = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check("database", self._check_database)
        self.register_check("cache", self._check_cache)
        self.register_check("system_resources", self._check_system_resources)
        self.register_check("disk_space", self._check_disk_space)
        
        self.register_async_check("database_async", self._check_database_async)
        self.register_async_check("cache_async", self._check_cache_async)
    
    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """Register a synchronous health check"""
        self.checks[name] = check_func
    
    def register_async_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """Register an asynchronous health check"""
        self.async_checks[name] = check_func
    
    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity and health"""
        start_time = time.time()
        
        try:
            is_healthy = is_database_healthy()
            response_time = (time.time() - start_time) * 1000
            
            if is_healthy:
                stats = db_manager.get_connection_stats()
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection is healthy",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc),
                    details=stats
                )
            else:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database connection failed",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_database_async(self) -> HealthCheckResult:
        """Async version of database health check"""
        start_time = time.time()
        
        try:
            is_healthy = await is_database_healthy_async()
            response_time = (time.time() - start_time) * 1000
            
            if is_healthy:
                stats = db_manager.get_connection_stats()
                return HealthCheckResult(
                    name="database_async",
                    status=HealthStatus.HEALTHY,
                    message="Async database connection is healthy",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc),
                    details=stats
                )
            else:
                return HealthCheckResult(
                    name="database_async",
                    status=HealthStatus.UNHEALTHY,
                    message="Async database connection failed",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_async",
                status=HealthStatus.UNHEALTHY,
                message=f"Async database check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_cache(self) -> HealthCheckResult:
        """Check Redis cache health"""
        start_time = time.time()
        
        try:
            is_healthy = cache_manager.is_healthy()
            response_time = (time.time() - start_time) * 1000
            stats = cache_manager.get_stats()
            
            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "Cache is healthy"
            elif stats["circuit_breaker_state"] == "open":
                status = HealthStatus.DEGRADED
                message = "Cache circuit breaker is open, using memory fallback"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Cache is not responding"
            
            return HealthCheckResult(
                name="cache",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc),
                details=stats
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                message=f"Cache check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_cache_async(self) -> HealthCheckResult:
        """Async version of cache health check"""
        start_time = time.time()
        
        try:
            # Test async cache operations
            test_key = f"health_check_{int(time.time())}"
            await cache_manager.aset(test_key, "test_value", 60)
            cached_value = await cache_manager.aget(test_key)
            await cache_manager.adelete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            stats = cache_manager.get_stats()
            
            if cached_value == "test_value":
                return HealthCheckResult(
                    name="cache_async",
                    status=HealthStatus.HEALTHY,
                    message="Async cache operations successful",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc),
                    details=stats
                )
            else:
                return HealthCheckResult(
                    name="cache_async",
                    status=HealthStatus.DEGRADED,
                    message="Cache operations partially working",
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc),
                    details=stats
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="cache_async",
                status=HealthStatus.UNHEALTHY,
                message=f"Async cache check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource utilization"""
        start_time = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            response_time = (time.time() - start_time) * 1000
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // 1024 // 1024,
                "memory_total_mb": memory.total // 1024 // 1024,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            }
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High resource usage: CPU {cpu_percent}%, Memory {memory.percent}%"
            elif cpu_percent > 70 or memory.percent > 70:
                status = HealthStatus.DEGRADED
                message = f"Moderate resource usage: CPU {cpu_percent}%, Memory {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal resource usage: CPU {cpu_percent}%, Memory {memory.percent}%"
            
            return HealthCheckResult(
                name="system_resources",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc),
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"System resource check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage('/')
            response_time = (time.time() - start_time) * 1000
            
            details = {
                "total_gb": disk.total // 1024 // 1024 // 1024,
                "used_gb": disk.used // 1024 // 1024 // 1024,
                "free_gb": disk.free // 1024 // 1024 // 1024,
                "used_percent": (disk.used / disk.total) * 100
            }
            
            used_percent = details["used_percent"]
            
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critically low disk space: {used_percent:.1f}% used"
            elif used_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Low disk space: {used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Adequate disk space: {used_percent:.1f}% used"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc),
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Disk space check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now(timezone.utc)
            )
    
    def run_all_checks(self) -> SystemHealth:
        """Run all registered synchronous health checks"""
        results = []
        
        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                logger.error(f"Health check '{name}' failed with exception: {e}")
                results.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed with exception: {str(e)}",
                    response_time_ms=0,
                    timestamp=datetime.now(timezone.utc)
                ))
        
        # Determine overall status
        if all(r.status == HealthStatus.HEALTHY for r in results):
            overall_status = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall_status,
            checks=results,
            timestamp=datetime.now(timezone.utc),
            environment=settings.environment,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def run_all_checks_async(self) -> SystemHealth:
        """Run all registered health checks (both sync and async)"""
        results = []
        
        # Run sync checks
        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                logger.error(f"Health check '{name}' failed with exception: {e}")
                results.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed with exception: {str(e)}",
                    response_time_ms=0,
                    timestamp=datetime.now(timezone.utc)
                ))
        
        # Run async checks
        async_tasks = []
        for name, check_func in self.async_checks.items():
            async_tasks.append(self._run_async_check(name, check_func))
        
        if async_tasks:
            async_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for result in async_results:
                if isinstance(result, Exception):
                    logger.error(f"Async health check failed with exception: {result}")
                else:
                    results.append(result)
        
        # Determine overall status
        if all(r.status == HealthStatus.HEALTHY for r in results):
            overall_status = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall_status,
            checks=results,
            timestamp=datetime.now(timezone.utc),
            environment=settings.environment,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def _run_async_check(self, name: str, check_func: Callable) -> HealthCheckResult:
        """Run an async health check with error handling"""
        try:
            return await check_func()
        except Exception as e:
            logger.error(f"Async health check '{name}' failed with exception: {e}")
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Async check failed with exception: {str(e)}",
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc)
            )
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            return {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version()
                },
                "process": {
                    "pid": psutil.Process().pid,
                    "cpu_percent": psutil.Process().cpu_percent(),
                    "memory_percent": psutil.Process().memory_percent(),
                    "create_time": psutil.Process().create_time(),
                    "num_threads": psutil.Process().num_threads()
                },
                "uptime_seconds": time.time() - self.start_time,
                "environment": settings.environment
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions
def get_health() -> SystemHealth:
    """Get current system health (sync)"""
    return health_checker.run_all_checks()

async def get_health_async() -> SystemHealth:
    """Get current system health (async)"""
    return await health_checker.run_all_checks_async()

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    return health_checker.get_system_info()

def is_healthy() -> bool:
    """Quick health check - returns True if all systems are healthy"""
    health = get_health()
    return health.status == HealthStatus.HEALTHY

async def is_healthy_async() -> bool:
    """Async quick health check"""
    health = await get_health_async()
    return health.status == HealthStatus.HEALTHY