"""
Application lifecycle management with graceful shutdown and connection management.

Provides comprehensive startup/shutdown orchestration for all services
with proper resource cleanup and health monitoring.
"""

import asyncio
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Callable, Optional, Any
import threading
from dataclasses import dataclass
from enum import Enum

from .database import db_manager, connect_to_mongo_async, close_mongo_connection_async
from .cache import cache_manager
from .health import health_checker
from .config import settings

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service lifecycle states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """Information about a managed service"""
    name: str
    startup_func: Optional[Callable] = None
    shutdown_func: Optional[Callable] = None
    health_check: Optional[Callable] = None
    state: ServiceState = ServiceState.STOPPED
    last_health_check: Optional[float] = None
    error_message: Optional[str] = None


class LifecycleManager:
    """Manages application lifecycle and service orchestration"""
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.shutdown_event = asyncio.Event()
        self.startup_tasks: List[Callable] = []
        self.shutdown_tasks: List[Callable] = []
        self._shutdown_timeout = 30  # seconds
        self._health_check_interval = 30  # seconds
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._startup_time: Optional[float] = None
        self._signal_handlers_installed = False
    
    def register_service(
        self,
        name: str,
        startup_func: Optional[Callable] = None,
        shutdown_func: Optional[Callable] = None,
        health_check: Optional[Callable] = None
    ) -> None:
        """Register a service for lifecycle management"""
        self.services[name] = ServiceInfo(
            name=name,
            startup_func=startup_func,
            shutdown_func=shutdown_func,
            health_check=health_check
        )
        logger.info(f"Registered service: {name}")
    
    def add_startup_task(self, task: Callable) -> None:
        """Add a startup task to be executed during application startup"""
        self.startup_tasks.append(task)
    
    def add_shutdown_task(self, task: Callable) -> None:
        """Add a shutdown task to be executed during application shutdown"""
        self.shutdown_tasks.append(task)
    
    async def _startup_service(self, service: ServiceInfo) -> bool:
        """Start a single service"""
        if service.startup_func is None:
            logger.info(f"Service {service.name} has no startup function, marking as running")
            service.state = ServiceState.RUNNING
            return True
        
        try:
            logger.info(f"Starting service: {service.name}")
            service.state = ServiceState.STARTING
            
            if asyncio.iscoroutinefunction(service.startup_func):
                await service.startup_func()
            else:
                service.startup_func()
            
            service.state = ServiceState.RUNNING
            service.error_message = None
            logger.info(f"Service {service.name} started successfully")
            return True
            
        except Exception as e:
            service.state = ServiceState.ERROR
            service.error_message = str(e)
            logger.error(f"Failed to start service {service.name}: {e}")
            return False
    
    async def _shutdown_service(self, service: ServiceInfo) -> bool:
        """Shutdown a single service"""
        if service.shutdown_func is None:
            logger.info(f"Service {service.name} has no shutdown function, marking as stopped")
            service.state = ServiceState.STOPPED
            return True
        
        try:
            logger.info(f"Stopping service: {service.name}")
            service.state = ServiceState.STOPPING
            
            if asyncio.iscoroutinefunction(service.shutdown_func):
                await service.shutdown_func()
            else:
                service.shutdown_func()
            
            service.state = ServiceState.STOPPED
            service.error_message = None
            logger.info(f"Service {service.name} stopped successfully")
            return True
            
        except Exception as e:
            service.state = ServiceState.ERROR
            service.error_message = str(e)
            logger.error(f"Failed to stop service {service.name}: {e}")
            return False
    
    async def _check_service_health(self, service: ServiceInfo) -> bool:
        """Check health of a single service"""
        if service.health_check is None or service.state != ServiceState.RUNNING:
            return True
        
        try:
            if asyncio.iscoroutinefunction(service.health_check):
                healthy = await service.health_check()
            else:
                healthy = service.health_check()
            
            service.last_health_check = time.time()
            return bool(healthy)
            
        except Exception as e:
            logger.warning(f"Health check failed for service {service.name}: {e}")
            return False
    
    async def _health_monitor_loop(self):
        """Background task to monitor service health"""
        while not self.shutdown_event.is_set():
            try:
                for service in self.services.values():
                    if service.state == ServiceState.RUNNING:
                        healthy = await self._check_service_health(service)
                        if not healthy:
                            logger.warning(f"Service {service.name} failed health check")
                
                # Wait for next health check
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self._health_check_interval
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Continue health checks
                    
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    def _install_signal_handlers(self):
        """Install signal handlers for graceful shutdown"""
        if self._signal_handlers_installed:
            return
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.shutdown())
        
        # Install handlers for common termination signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # On Unix systems, also handle SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
        
        self._signal_handlers_installed = True
        logger.info("Signal handlers installed for graceful shutdown")
    
    async def startup(self) -> bool:
        """Start all registered services and execute startup tasks"""
        logger.info("Starting application lifecycle...")
        self._startup_time = time.time()
        
        # Install signal handlers
        self._install_signal_handlers()
        
        # Execute startup tasks
        for task in self.startup_tasks:
            try:
                logger.info(f"Executing startup task: {task.__name__}")
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.error(f"Startup task {task.__name__} failed: {e}")
                return False
        
        # Start services in order
        failed_services = []
        for service in self.services.values():
            success = await self._startup_service(service)
            if not success:
                failed_services.append(service.name)
        
        if failed_services:
            logger.error(f"Failed to start services: {failed_services}")
            await self.shutdown()
            return False
        
        # Start health monitoring
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        startup_time = time.time() - self._startup_time
        logger.info(f"Application startup completed in {startup_time:.2f}s")
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown all services and execute cleanup tasks"""
        logger.info("Initiating graceful shutdown...")
        shutdown_start = time.time()
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Stop health monitoring
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await asyncio.wait_for(self._health_monitor_task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        # Shutdown services in reverse order
        failed_services = []
        for service in reversed(list(self.services.values())):
            try:
                success = await asyncio.wait_for(
                    self._shutdown_service(service),
                    timeout=self._shutdown_timeout
                )
                if not success:
                    failed_services.append(service.name)
            except asyncio.TimeoutError:
                logger.error(f"Timeout shutting down service {service.name}")
                failed_services.append(service.name)
        
        # Execute shutdown tasks
        for task in reversed(self.shutdown_tasks):
            try:
                logger.info(f"Executing shutdown task: {task.__name__}")
                if asyncio.iscoroutinefunction(task):
                    await asyncio.wait_for(task(), timeout=10)
                else:
                    task()
            except Exception as e:
                logger.error(f"Shutdown task {task.__name__} failed: {e}")
        
        shutdown_time = time.time() - shutdown_start
        
        if failed_services:
            logger.warning(f"Some services failed to shutdown cleanly: {failed_services}")
            logger.info(f"Shutdown completed with warnings in {shutdown_time:.2f}s")
            return False
        else:
            logger.info(f"Graceful shutdown completed in {shutdown_time:.2f}s")
            return True
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all registered services"""
        return {
            "services": {
                name: {
                    "state": service.state.value,
                    "last_health_check": service.last_health_check,
                    "error_message": service.error_message
                }
                for name, service in self.services.items()
            },
            "uptime_seconds": time.time() - self._startup_time if self._startup_time else 0,
            "health_monitor_running": self._health_monitor_task and not self._health_monitor_task.done(),
            "shutdown_requested": self.shutdown_event.is_set()
        }
    
    def is_healthy(self) -> bool:
        """Check if all services are healthy"""
        return all(
            service.state == ServiceState.RUNNING
            for service in self.services.values()
        )
    
    @asynccontextmanager
    async def lifespan_context(self):
        """Context manager for application lifespan (for FastAPI)"""
        try:
            success = await self.startup()
            if not success:
                raise RuntimeError("Application startup failed")
            yield
        finally:
            await self.shutdown()


# Global lifecycle manager
lifecycle_manager = LifecycleManager()


# Register core services
async def startup_database():
    """Startup function for database service"""
    try:
        # Initialize both sync and async connections
        db_manager.connect_sync()
        await db_manager.connect_async()
        logger.info("Database connections established")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise

async def shutdown_database():
    """Shutdown function for database service"""
    try:
        db_manager.close_sync_connection()
        await db_manager.close_async_connection()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Database shutdown failed: {e}")

def check_database_health():
    """Health check for database service"""
    return db_manager.is_healthy()

async def startup_cache():
    """Startup function for cache service"""
    try:
        cache_manager.connect_sync()
        await cache_manager.connect_async()
        logger.info("Cache connections established")
    except Exception as e:
        logger.error(f"Cache startup failed: {e}")
        raise

async def shutdown_cache():
    """Shutdown function for cache service"""
    try:
        cache_manager.close_sync()
        await cache_manager.close_async()
        logger.info("Cache connections closed")
    except Exception as e:
        logger.error(f"Cache shutdown failed: {e}")

def check_cache_health():
    """Health check for cache service"""
    return cache_manager.is_healthy()

# Register services
lifecycle_manager.register_service(
    "database",
    startup_func=startup_database,
    shutdown_func=shutdown_database,
    health_check=check_database_health
)

lifecycle_manager.register_service(
    "cache",
    startup_func=startup_cache,
    shutdown_func=shutdown_cache,
    health_check=check_cache_health
)

# Additional startup/shutdown tasks
def log_startup_info():
    """Log startup information"""
    logger.info(f"Starting Korea Public Data API Server")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"MongoDB URL: {settings.mongodb_url}")
    logger.info(f"Redis URL: {settings.redis_url}")

def log_shutdown_info():
    """Log shutdown information"""
    logger.info("Korea Public Data API Server shutdown complete")

lifecycle_manager.add_startup_task(log_startup_info)
lifecycle_manager.add_shutdown_task(log_shutdown_info)


# Convenience functions
async def startup_application() -> bool:
    """Start the application"""
    return await lifecycle_manager.startup()

async def shutdown_application() -> bool:
    """Shutdown the application"""
    return await lifecycle_manager.shutdown()

def get_application_status() -> Dict[str, Any]:
    """Get application status"""
    return lifecycle_manager.get_service_status()

def is_application_healthy() -> bool:
    """Check if application is healthy"""
    return lifecycle_manager.is_healthy()

@asynccontextmanager
async def lifespan_context():
    """Application lifespan context manager"""
    async with lifecycle_manager.lifespan_context():
        yield


# FastAPI lifespan event handlers
async def startup_event():
    """FastAPI startup event handler"""
    success = await startup_application()
    if not success:
        logger.error("Application startup failed, exiting")
        sys.exit(1)

async def shutdown_event():
    """FastAPI shutdown event handler"""
    await shutdown_application()