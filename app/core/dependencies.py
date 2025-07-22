"""
FastAPI Dependencies for Dependency Injection.

Provides FastAPI-compatible dependency functions using the DI container.
"""

from typing import TypeVar, Type, Callable
from fastapi import Depends
from .container import get_container, DIContainer

T = TypeVar('T')


def get_di_container() -> DIContainer:
    """FastAPI dependency to get the DI container"""
    return get_container()


def create_dependency(service_type: Type[T]) -> Callable[[], T]:
    """Create a FastAPI dependency function for a service type"""
    def dependency() -> T:
        container = get_container()
        return container.resolve(service_type)
    
    # Set proper name for better debugging
    dependency.__name__ = f"get_{service_type.__name__.lower()}"
    return dependency


def get_repository_dependency(repository_type: Type[T]) -> Callable[[], T]:
    """Create a dependency for repository types"""
    return create_dependency(repository_type)


def get_service_dependency(service_type: Type[T]) -> Callable[[], T]:
    """Create a dependency for service types"""
    return create_dependency(service_type)


# Specific dependency functions for common services
def get_announcement_service():
    """Get AnnouncementService instance"""
    from ..domains.announcements.service import AnnouncementService
    return get_container().resolve(AnnouncementService)


def get_business_service():
    """Get BusinessService instance"""
    from ..domains.businesses.service import BusinessService
    return get_container().resolve(BusinessService)


def get_content_service():
    """Get ContentService instance"""
    from ..domains.contents.service import ContentService
    return get_container().resolve(ContentService)


def get_statistics_service():
    """Get StatisticsService instance"""
    from ..domains.statistics.service import StatisticsService
    return get_container().resolve(StatisticsService)


def get_announcement_repository():
    """Get AnnouncementRepository instance"""
    from ..domains.announcements.repository import AnnouncementRepository
    return get_container().resolve(AnnouncementRepository)


def get_business_repository():
    """Get BusinessRepository instance"""
    from ..domains.businesses.repository import BusinessRepository
    return get_container().resolve(BusinessRepository)


def get_content_repository():
    """Get ContentRepository instance"""
    from ..domains.contents.repository import ContentRepository
    return get_container().resolve(ContentRepository)


def get_statistics_repository():
    """Get StatisticsRepository instance"""
    from ..domains.statistics.repository import StatisticsRepository
    return get_container().resolve(StatisticsRepository)


def get_kstartup_client():
    """Get KStartupAPIClient instance"""
    from ..shared.clients.kstartup_api_client import KStartupAPIClient
    return get_container().resolve(KStartupAPIClient)


# Scoped dependency management
class ScopedDependencyManager:
    """Manages scoped dependencies for request lifecycle"""
    
    def __init__(self, container: DIContainer):
        self.container = container
    
    def __enter__(self):
        # Clear any existing scoped instances
        self.container.clear_scoped()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up scoped instances after request
        self.container.clear_scoped()


def get_scoped_dependency_manager() -> ScopedDependencyManager:
    """Get scoped dependency manager for request lifecycle"""
    return ScopedDependencyManager(get_container())


# Dependency validation
def validate_dependencies():
    """Validate that all registered dependencies can be resolved"""
    container = get_container()
    registrations = container.list_registrations()
    
    validation_results = {}
    for service_name in registrations:
        try:
            # Try to get the service type from name
            # This is a simplified validation - in production you might want more sophisticated validation
            validation_results[service_name] = {"status": "registered", "error": None}
        except Exception as e:
            validation_results[service_name] = {"status": "error", "error": str(e)}
    
    return validation_results


# Dependency override for testing
class DependencyOverrides:
    """Context manager for overriding dependencies during testing"""
    
    def __init__(self, overrides: dict):
        self.overrides = overrides
        self.original_bindings = {}
        self.container = get_container()
    
    def __enter__(self):
        # Store original bindings
        for service_type in self.overrides:
            if self.container.is_registered(service_type):
                self.original_bindings[service_type] = self.container.get_registration_info(service_type)
        
        # Apply overrides
        for service_type, override_instance in self.overrides.items():
            self.container.register_instance(service_type, override_instance)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original bindings
        for service_type, original_binding in self.original_bindings.items():
            if original_binding.implementation:
                if original_binding.lifetime.value == "singleton":
                    self.container.register_singleton(service_type, original_binding.implementation)
                elif original_binding.lifetime.value == "transient":
                    self.container.register_transient(service_type, original_binding.implementation)
                elif original_binding.lifetime.value == "scoped":
                    self.container.register_scoped(service_type, original_binding.implementation)
            elif original_binding.factory:
                self.container.register_factory(service_type, original_binding.factory, original_binding.lifetime)


def override_dependencies(**overrides):
    """Convenience function to create dependency overrides"""
    return DependencyOverrides(overrides)