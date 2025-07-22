"""
Dependency Injection Configuration.

Sets up all service and repository registrations for the DI container.
"""

from pymongo.database import Database
from .container import DIContainer, Lifetime
from .database import get_database


def configure_dependencies() -> DIContainer:
    """
    Configure and setup the DI container with all dependencies.
    
    Returns:
        Configured DIContainer instance
    """
    container = DIContainer()
    
    # Register database instance as singleton
    db_instance = get_database()
    if db_instance is not None:
        container.register_instance(Database, db_instance)
    
    # Register repositories as singletons (they're stateless)
    from ..domains.announcements.repository import AnnouncementRepository
    from ..domains.businesses.repository import BusinessRepository
    from ..domains.contents.repository import ContentRepository
    from ..domains.statistics.repository import StatisticsRepository
    
    container.register_singleton(AnnouncementRepository)
    container.register_singleton(BusinessRepository)
    container.register_singleton(ContentRepository)
    container.register_singleton(StatisticsRepository)
    
    # Register services as singletons (they're stateless but depend on repositories)
    from ..domains.announcements.service import AnnouncementService
    from ..domains.businesses.service import BusinessService
    from ..domains.contents.service import ContentService
    from ..domains.statistics.service import StatisticsService
    
    container.register_singleton(AnnouncementService)
    container.register_singleton(BusinessService)
    container.register_singleton(ContentService)
    container.register_singleton(StatisticsService)
    
    # Register API clients as singletons
    from ..shared.clients.kstartup_api_client import KStartupAPIClient
    container.register_singleton(KStartupAPIClient)
    
    return container


def validate_container_setup(container: DIContainer) -> dict:
    """
    Validate that all dependencies can be resolved correctly.
    
    Args:
        container: The DI container to validate
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {}
    
    # Test repository resolutions
    repositories = [
        "AnnouncementRepository",
        "BusinessRepository", 
        "ContentRepository",
        "StatisticsRepository"
    ]
    
    for repo_name in repositories:
        try:
            if repo_name == "AnnouncementRepository":
                from ..domains.announcements.repository import AnnouncementRepository
                instance = container.resolve(AnnouncementRepository)
            elif repo_name == "BusinessRepository":
                from ..domains.businesses.repository import BusinessRepository
                instance = container.resolve(BusinessRepository)
            elif repo_name == "ContentRepository":
                from ..domains.contents.repository import ContentRepository
                instance = container.resolve(ContentRepository)
            elif repo_name == "StatisticsRepository":
                from ..domains.statistics.repository import StatisticsRepository
                instance = container.resolve(StatisticsRepository)
            
            validation_results[repo_name] = {
                "status": "success",
                "instance_type": type(instance).__name__,
                "error": None
            }
        except Exception as e:
            validation_results[repo_name] = {
                "status": "error",
                "instance_type": None,
                "error": str(e)
            }
    
    # Test service resolutions
    services = [
        "AnnouncementService",
        "BusinessService",
        "ContentService", 
        "StatisticsService"
    ]
    
    for service_name in services:
        try:
            if service_name == "AnnouncementService":
                from ..domains.announcements.service import AnnouncementService
                instance = container.resolve(AnnouncementService)
            elif service_name == "BusinessService":
                from ..domains.businesses.service import BusinessService
                instance = container.resolve(BusinessService)
            elif service_name == "ContentService":
                from ..domains.contents.service import ContentService
                instance = container.resolve(ContentService)
            elif service_name == "StatisticsService":
                from ..domains.statistics.service import StatisticsService
                instance = container.resolve(StatisticsService)
            
            validation_results[service_name] = {
                "status": "success",
                "instance_type": type(instance).__name__,
                "error": None
            }
        except Exception as e:
            validation_results[service_name] = {
                "status": "error", 
                "instance_type": None,
                "error": str(e)
            }
    
    # Test API client resolution
    try:
        from ..shared.clients.kstartup_api_client import KStartupAPIClient
        instance = container.resolve(KStartupAPIClient)
        validation_results["KStartupAPIClient"] = {
            "status": "success",
            "instance_type": type(instance).__name__,
            "error": None
        }
    except Exception as e:
        validation_results["KStartupAPIClient"] = {
            "status": "error",
            "instance_type": None,
            "error": str(e)
        }
    
    return validation_results


def get_dependency_graph(container: DIContainer) -> dict:
    """
    Get a representation of the dependency graph.
    
    Args:
        container: The DI container
        
    Returns:
        Dictionary representing the dependency graph
    """
    registrations = container.list_registrations()
    dependency_graph = {}
    
    for service_name in registrations:
        info = container.get_registration_info_by_name(service_name)
        if info:
            dependency_graph[service_name] = {
                "lifetime": info.lifetime.value,
                "implementation": info.implementation.__name__ if info.implementation else None,
                "has_factory": info.factory is not None,
                "is_instance": info.instance is not None
            }
    
    return dependency_graph