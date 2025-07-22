"""
Dependency Injection Container implementation.

Provides a flexible dependency injection system supporting:
- Singleton and transient lifetimes
- Interface binding
- Factory methods
- Circular dependency detection
"""

import inspect
from typing import TypeVar, Type, Any, Dict, Callable, Optional, get_type_hints
from enum import Enum
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Lifetime(Enum):
    """Service lifetime enumeration"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class CircularDependencyError(Exception):
    """Raised when circular dependency is detected"""
    pass


class ServiceNotFoundError(Exception):
    """Raised when requested service is not registered"""
    pass


class ServiceBinding:
    """Represents a service binding configuration"""
    
    def __init__(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        instance: Optional[T] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        # Validate that exactly one of implementation, factory, or instance is provided
        provided_count = sum(x is not None for x in [implementation, factory, instance])
        if provided_count != 1:
            raise ValueError(f"Exactly one of implementation, factory, or instance must be provided. Got {provided_count}: implementation={implementation is not None}, factory={factory is not None}, instance={instance is not None}")


class DIContainer:
    """Dependency Injection Container"""
    
    def __init__(self):
        self._bindings: Dict[Type, ServiceBinding] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._resolution_stack: list = []
    
    def register_singleton(self, service_type: Type[T], implementation: Type[T] = None) -> 'DIContainer':
        """Register a service as singleton"""
        impl = implementation or service_type
        self._bindings[service_type] = ServiceBinding(
            service_type=service_type,
            implementation=impl,
            lifetime=Lifetime.SINGLETON
        )
        logger.debug(f"Registered singleton: {service_type.__name__} -> {impl.__name__}")
        return self
    
    def register_transient(self, service_type: Type[T], implementation: Type[T] = None) -> 'DIContainer':
        """Register a service as transient"""
        impl = implementation or service_type
        self._bindings[service_type] = ServiceBinding(
            service_type=service_type,
            implementation=impl,
            lifetime=Lifetime.TRANSIENT
        )
        logger.debug(f"Registered transient: {service_type.__name__} -> {impl.__name__}")
        return self
    
    def register_scoped(self, service_type: Type[T], implementation: Type[T] = None) -> 'DIContainer':
        """Register a service as scoped"""
        impl = implementation or service_type
        self._bindings[service_type] = ServiceBinding(
            service_type=service_type,
            implementation=impl,
            lifetime=Lifetime.SCOPED
        )
        logger.debug(f"Registered scoped: {service_type.__name__} -> {impl.__name__}")
        return self
    
    def register_factory(self, service_type: Type[T], factory: Callable[..., T], lifetime: Lifetime = Lifetime.TRANSIENT) -> 'DIContainer':
        """Register a service with factory method"""
        self._bindings[service_type] = ServiceBinding(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        logger.debug(f"Registered factory: {service_type.__name__} -> {factory.__name__}")
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'DIContainer':
        """Register a specific instance"""
        self._bindings[service_type] = ServiceBinding(
            service_type=service_type,
            instance=instance,
            lifetime=Lifetime.SINGLETON
        )
        self._singletons[service_type] = instance
        logger.debug(f"Registered instance: {service_type.__name__}")
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance"""
        # Check for circular dependencies
        if service_type in self._resolution_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolution_stack]) + f" -> {service_type.__name__}"
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
        
        try:
            self._resolution_stack.append(service_type)
            return self._resolve_internal(service_type)
        finally:
            self._resolution_stack.remove(service_type)
    
    def _resolve_internal(self, service_type: Type[T]) -> T:
        """Internal resolve implementation"""
        # Check if service is registered
        if service_type not in self._bindings:
            raise ServiceNotFoundError(f"Service {service_type.__name__} is not registered")
        
        binding = self._bindings[service_type]
        
        # Handle singleton lifetime
        if binding.lifetime == Lifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = self._create_instance(binding)
            self._singletons[service_type] = instance
            return instance
        
        # Handle scoped lifetime
        elif binding.lifetime == Lifetime.SCOPED:
            if service_type in self._scoped_instances:
                return self._scoped_instances[service_type]
            
            instance = self._create_instance(binding)
            self._scoped_instances[service_type] = instance
            return instance
        
        # Handle transient lifetime
        else:
            return self._create_instance(binding)
    
    def _create_instance(self, binding: ServiceBinding) -> Any:
        """Create an instance based on binding configuration"""
        # Use existing instance
        if binding.instance is not None:
            return binding.instance
        
        # Use factory method
        if binding.factory is not None:
            return self._invoke_factory(binding.factory)
        
        # Use implementation class
        if binding.implementation is not None:
            return self._create_from_class(binding.implementation)
        
        raise ValueError(f"Invalid binding configuration for {binding.service_type.__name__}")
    
    def _invoke_factory(self, factory: Callable) -> Any:
        """Invoke factory method with dependency injection"""
        signature = inspect.signature(factory)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                dependency = self.resolve(param.annotation)
                kwargs[param_name] = dependency
        
        return factory(**kwargs)
    
    def _create_from_class(self, implementation: Type) -> Any:
        """Create instance from class with constructor injection"""
        signature = inspect.signature(implementation.__init__)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation != inspect.Parameter.empty:
                # Try to resolve the dependency
                try:
                    dependency = self.resolve(param.annotation)
                    kwargs[param_name] = dependency
                except ServiceNotFoundError:
                    # If dependency is not registered and has default value, use default
                    if param.default != inspect.Parameter.empty:
                        continue
                    # If no default and Optional, pass None
                    if hasattr(param.annotation, '__origin__') and param.annotation.__origin__ is type(Optional[int].__origin__):
                        kwargs[param_name] = None
                        continue
                    raise
        
        return implementation(**kwargs)
    
    def clear_scoped(self):
        """Clear scoped instances (for request scope management)"""
        self._scoped_instances.clear()
        logger.debug("Cleared scoped instances")
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered"""
        return service_type in self._bindings
    
    def get_registration_info(self, service_type: Type) -> Optional[ServiceBinding]:
        """Get registration information for a service type"""
        return self._bindings.get(service_type)
    
    def list_registrations(self) -> Dict[str, Dict[str, Any]]:
        """List all registered services"""
        result = {}
        for service_type, binding in self._bindings.items():
            info = {
                "lifetime": binding.lifetime.value,
                "has_implementation": binding.implementation is not None,
                "has_factory": binding.factory is not None,
                "has_instance": binding.instance is not None
            }
            
            if binding.implementation:
                info["implementation"] = binding.implementation.__name__
            if binding.factory:
                info["factory"] = binding.factory.__name__
            
            result[service_type.__name__] = info
        
        return result


# Global container instance
container = DIContainer()


def inject(func):
    """Decorator for automatic dependency injection in functions"""
    signature = inspect.signature(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get type hints for the function
        type_hints = get_type_hints(func)
        
        # Inject dependencies for parameters not provided
        for param_name, param in signature.parameters.items():
            if param_name not in kwargs and param_name in type_hints:
                param_type = type_hints[param_name]
                if container.is_registered(param_type):
                    kwargs[param_name] = container.resolve(param_type)
        
        return func(*args, **kwargs)
    
    return wrapper


def get_service(service_type: Type[T]) -> T:
    """Convenience function to resolve service from global container"""
    return container.resolve(service_type)


def configure_container():
    """Configure the dependency injection container"""
    # This will be called during application startup
    from ..domains.announcements.repository import AnnouncementRepository
    from ..domains.announcements.service import AnnouncementService
    from ..domains.businesses.repository import BusinessRepository
    from ..domains.businesses.service import BusinessService
    from ..domains.contents.repository import ContentRepository
    from ..domains.contents.service import ContentService
    from ..domains.statistics.repository import StatisticsRepository
    from ..domains.statistics.service import StatisticsService
    from ..shared.clients.kstartup_api_client import KStartupAPIClient
    from ..core.database import get_database
    
    # Register database as singleton
    container.register_instance(type(get_database()), get_database())
    
    # Register repositories as singletons
    container.register_singleton(AnnouncementRepository)
    container.register_singleton(BusinessRepository)
    container.register_singleton(ContentRepository)
    container.register_singleton(StatisticsRepository)
    
    # Register services as singletons
    container.register_singleton(AnnouncementService)
    container.register_singleton(BusinessService)
    container.register_singleton(ContentService)
    container.register_singleton(StatisticsService)
    
    # Register API client as transient (new instance per request)
    container.register_transient(KStartupAPIClient)
    
    logger.info("Dependency injection container configured successfully")
    logger.debug(f"Registered services: {list(container.list_registrations().keys())}")


def get_container() -> DIContainer:
    """Get the global container instance"""
    return container


def setup_container(new_container: DIContainer):
    """Set up the global container with a new instance"""
    global container
    container = new_container
    logger.info("Global DI container updated")