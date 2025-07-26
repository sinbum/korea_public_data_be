"""
Decorators for CQRS pattern implementation.

Provides convenient decorators for registering command and query handlers.
"""

import functools
import logging
from typing import Type, Callable, Any, Optional
from .commands import Command, CommandHandler
from .queries import Query, QueryHandler

logger = logging.getLogger(__name__)


def command_handler(command_type: Type[Command], bus: Optional[Any] = None):
    """
    Decorator to register a command handler.
    
    Args:
        command_type: Type of command this handler processes
        bus: Command bus to register with (optional, can be set later)
    
    Usage:
        @command_handler(CreateAnnouncementCommand)
        class CreateAnnouncementHandler(CommandHandler):
            async def handle(self, command: CreateAnnouncementCommand):
                # Handle command
                pass
    """
    def decorator(handler_class):
        # Add metadata to the handler class
        handler_class._command_type = command_type
        handler_class._is_command_handler = True
        
        # Register with bus if provided
        if bus:
            handler_instance = handler_class()
            bus.register_handler(command_type, handler_instance)
            logger.info(f"Auto-registered command handler: {handler_class.__name__} for {command_type.__name__}")
        
        return handler_class
    
    return decorator


def query_handler(query_type: Type[Query], bus: Optional[Any] = None):
    """
    Decorator to register a query handler.
    
    Args:
        query_type: Type of query this handler processes
        bus: Query bus to register with (optional, can be set later)
    
    Usage:
        @query_handler(GetAnnouncementByIdQuery)
        class GetAnnouncementByIdHandler(QueryHandler):
            async def handle(self, query: GetAnnouncementByIdQuery):
                # Handle query
                pass
    """
    def decorator(handler_class):
        # Add metadata to the handler class
        handler_class._query_type = query_type
        handler_class._is_query_handler = True
        
        # Register with bus if provided
        if bus:
            handler_instance = handler_class()
            bus.register_handler(query_type, handler_instance)
            logger.info(f"Auto-registered query handler: {handler_class.__name__} for {query_type.__name__}")
        
        return handler_class
    
    return decorator


def transactional(func: Callable) -> Callable:
    """
    Decorator to mark command handlers as transactional.
    
    This is a placeholder for future transaction management implementation.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Future: Begin transaction
        try:
            result = await func(*args, **kwargs)
            # Future: Commit transaction
            return result
        except Exception:
            # Future: Rollback transaction
            raise
    
    wrapper._is_transactional = True
    return wrapper


def cached(ttl: int = 300):
    """
    Decorator to mark query handlers as cacheable.
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # The actual caching logic is handled by the QueryBus
            # This decorator just marks the handler as cacheable
            return await func(*args, **kwargs)
        
        wrapper._is_cacheable = True
        wrapper._cache_ttl = ttl
        return wrapper
    
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to add retry logic to handlers.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Handler {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {delay}s: {str(e)}"
                        )
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(
                            f"Handler {func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
            
            raise last_exception
        
        wrapper._has_retry = True
        wrapper._max_attempts = max_attempts
        wrapper._retry_delay = delay
        return wrapper
    
    return decorator


def validate_input(validator: Callable[[Any], bool], error_message: str = "Invalid input"):
    """
    Decorator to add custom input validation to handlers.
    
    Args:
        validator: Function that takes the command/query and returns bool
        error_message: Error message if validation fails
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract command/query from arguments
            operation = None
            if len(args) > 1:
                operation = args[1]  # Assume second argument is command/query
            
            if operation and not validator(operation):
                from ..exceptions import DataValidationError
                raise DataValidationError(error_message)
            
            return await func(*args, **kwargs)
        
        wrapper._has_custom_validation = True
        return wrapper
    
    return decorator


def audit_log(action: str):
    """
    Decorator to add audit logging to handlers.
    
    Args:
        action: Action description for audit log
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract handler instance and operation
            handler_instance = args[0] if args else None
            operation = args[1] if len(args) > 1 else None
            
            # Log start
            logger.info(f"AUDIT: Starting {action} - Operation: {type(operation).__name__ if operation else 'Unknown'}")
            
            try:
                result = await func(*args, **kwargs)
                
                # Log success
                logger.info(f"AUDIT: Completed {action} successfully")
                
                return result
            except Exception as e:
                # Log failure
                logger.error(f"AUDIT: Failed {action} - Error: {str(e)}")
                raise
        
        wrapper._has_audit_log = True
        wrapper._audit_action = action
        return wrapper
    
    return decorator


def performance_monitor(func: Callable) -> Callable:
    """
    Decorator to monitor handler performance.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import time
        
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"PERF: {func.__name__} executed in {execution_time:.3f}s")
            
            # Store metrics (future enhancement)
            if hasattr(func, '_performance_metrics'):
                func._performance_metrics.append(execution_time)
            else:
                func._performance_metrics = [execution_time]
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"PERF: {func.__name__} failed after {execution_time:.3f}s - {str(e)}")
            raise
    
    wrapper._has_performance_monitor = True
    return wrapper


# Utility functions for working with decorated handlers

def get_command_handlers_from_module(module) -> dict:
    """
    Extract all command handlers from a module.
    
    Args:
        module: Python module to scan
        
    Returns:
        Dict mapping command types to handler classes
    """
    handlers = {}
    
    for name in dir(module):
        obj = getattr(module, name)
        if (hasattr(obj, '_is_command_handler') and 
            hasattr(obj, '_command_type')):
            handlers[obj._command_type] = obj
    
    return handlers


def get_query_handlers_from_module(module) -> dict:
    """
    Extract all query handlers from a module.
    
    Args:
        module: Python module to scan
        
    Returns:
        Dict mapping query types to handler classes
    """
    handlers = {}
    
    for name in dir(module):
        obj = getattr(module, name)
        if (hasattr(obj, '_is_query_handler') and 
            hasattr(obj, '_query_type')):
            handlers[obj._query_type] = obj
    
    return handlers


def auto_register_handlers(module, command_bus, query_bus) -> None:
    """
    Automatically register all handlers from a module with the buses.
    
    Args:
        module: Python module to scan
        command_bus: Command bus instance
        query_bus: Query bus instance
    """
    # Register command handlers
    command_handlers = get_command_handlers_from_module(module)
    for command_type, handler_class in command_handlers.items():
        handler_instance = handler_class()
        command_bus.register_handler(command_type, handler_instance)
        logger.info(f"Auto-registered command handler: {handler_class.__name__}")
    
    # Register query handlers
    query_handlers = get_query_handlers_from_module(module)
    for query_type, handler_class in query_handlers.items():
        handler_instance = handler_class()
        query_bus.register_handler(query_type, handler_instance)
        logger.info(f"Auto-registered query handler: {handler_class.__name__}")
    
    logger.info(
        f"Auto-registration complete: {len(command_handlers)} command handlers, "
        f"{len(query_handlers)} query handlers"
    )