"""
Command and Query bus implementations.

Provides centralized routing of commands and queries to their handlers.
"""

import logging
from typing import Dict, Type, Any, Optional
from .commands import Command, CommandHandler, ICommandBus
from .queries import Query, QueryHandler, IQueryBus
from ..exceptions import KoreanPublicAPIError

logger = logging.getLogger(__name__)


class CommandBusError(KoreanPublicAPIError):
    """Command bus specific error."""
    pass


class QueryBusError(KoreanPublicAPIError):
    """Query bus specific error."""
    pass


class CommandBus(ICommandBus):
    """
    Command bus implementation.
    
    Routes commands to their registered handlers and manages execution.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}
        self._middleware: list = []
    
    async def execute(self, command: Command) -> Any:
        """
        Execute a command using its registered handler.
        
        Args:
            command: Command to execute
            
        Returns:
            Command execution result
            
        Raises:
            CommandBusError: If no handler is registered for the command
        """
        command_type = type(command)
        handler = self._handlers.get(command_type)
        
        if not handler:
            raise CommandBusError(
                f"No handler registered for command type: {command_type.__name__}",
                error_code="COMMAND_HANDLER_NOT_FOUND"
            )
        
        logger.info(
            f"Executing command: {command_type.__name__} "
            f"(ID: {command.command_id})"
        )
        
        try:
            # Apply middleware (pre-execution)
            for middleware in self._middleware:
                if hasattr(middleware, 'before_execute'):
                    await middleware.before_execute(command)
            
            # Execute command
            result = await handler.handle(command)
            
            # Apply middleware (post-execution)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, 'after_execute'):
                    await middleware.after_execute(command, result)
            
            logger.info(
                f"Command executed successfully: {command_type.__name__} "
                f"(ID: {command.command_id})"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Command execution failed: {command_type.__name__} "
                f"(ID: {command.command_id}) - Error: {str(e)}"
            )
            
            # Apply middleware (error handling)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, 'on_error'):
                    await middleware.on_error(command, e)
            
            raise
    
    def register_handler(self, command_type: Type[Command], handler: CommandHandler) -> None:
        """
        Register a command handler.
        
        Args:
            command_type: Type of command to handle
            handler: Handler instance
        """
        if command_type in self._handlers:
            logger.warning(
                f"Overriding existing handler for command: {command_type.__name__}"
            )
        
        self._handlers[command_type] = handler
        logger.info(f"Registered handler for command: {command_type.__name__}")
    
    def unregister_handler(self, command_type: Type[Command]) -> None:
        """
        Unregister a command handler.
        
        Args:
            command_type: Type of command to unregister
        """
        if command_type in self._handlers:
            del self._handlers[command_type]
            logger.info(f"Unregistered handler for command: {command_type.__name__}")
    
    def add_middleware(self, middleware) -> None:
        """Add middleware to the command bus."""
        self._middleware.append(middleware)
    
    def get_registered_commands(self) -> list:
        """Get list of registered command types."""
        return list(self._handlers.keys())


class QueryBus(IQueryBus):
    """
    Query bus implementation.
    
    Routes queries to their registered handlers and manages execution.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[Query], QueryHandler] = {}
        self._middleware: list = []
        self._cache: Optional[Any] = None  # Can be configured with Redis or in-memory cache
    
    async def execute(self, query: Query) -> Any:
        """
        Execute a query using its registered handler.
        
        Args:
            query: Query to execute
            
        Returns:
            Query execution result
            
        Raises:
            QueryBusError: If no handler is registered for the query
        """
        query_type = type(query)
        handler = self._handlers.get(query_type)
        
        if not handler:
            raise QueryBusError(
                f"No handler registered for query type: {query_type.__name__}",
                error_code="QUERY_HANDLER_NOT_FOUND"
            )
        
        logger.debug(
            f"Executing query: {query_type.__name__} "
            f"(ID: {query.query_id})"
        )
        
        try:
            # Check cache first (for cacheable queries)
            cache_key = self._generate_cache_key(query)
            if self._cache and cache_key:
                cached_result = await self._get_from_cache(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for query: {query_type.__name__}")
                    return cached_result
            
            # Apply middleware (pre-execution)
            for middleware in self._middleware:
                if hasattr(middleware, 'before_execute'):
                    await middleware.before_execute(query)
            
            # Execute query
            result = await handler.handle(query)
            
            # Cache result (for cacheable queries)
            if self._cache and cache_key and result is not None:
                await self._store_in_cache(cache_key, result)
            
            # Apply middleware (post-execution)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, 'after_execute'):
                    await middleware.after_execute(query, result)
            
            logger.debug(
                f"Query executed successfully: {query_type.__name__} "
                f"(ID: {query.query_id})"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Query execution failed: {query_type.__name__} "
                f"(ID: {query.query_id}) - Error: {str(e)}"
            )
            
            # Apply middleware (error handling)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, 'on_error'):
                    await middleware.on_error(query, e)
            
            raise
    
    def register_handler(self, query_type: Type[Query], handler: QueryHandler) -> None:
        """
        Register a query handler.
        
        Args:
            query_type: Type of query to handle
            handler: Handler instance
        """
        if query_type in self._handlers:
            logger.warning(
                f"Overriding existing handler for query: {query_type.__name__}"
            )
        
        self._handlers[query_type] = handler
        logger.info(f"Registered handler for query: {query_type.__name__}")
    
    def unregister_handler(self, query_type: Type[Query]) -> None:
        """
        Unregister a query handler.
        
        Args:
            query_type: Type of query to unregister
        """
        if query_type in self._handlers:
            del self._handlers[query_type]
            logger.info(f"Unregistered handler for query: {query_type.__name__}")
    
    def add_middleware(self, middleware) -> None:
        """Add middleware to the query bus."""
        self._middleware.append(middleware)
    
    def set_cache(self, cache) -> None:
        """Set cache implementation for query results."""
        self._cache = cache
    
    def get_registered_queries(self) -> list:
        """Get list of registered query types."""
        return list(self._handlers.keys())
    
    def _generate_cache_key(self, query: Query) -> Optional[str]:
        """
        Generate cache key for query.
        
        Override in subclasses for custom cache key generation.
        """
        # Simple implementation - can be enhanced
        if hasattr(query, '__dict__'):
            import hashlib
            import json
            
            # Create stable hash from query data
            query_data = query.model_dump(exclude={'query_id', 'timestamp'})
            query_str = json.dumps(query_data, sort_keys=True)
            cache_key = f"{type(query).__name__}:{hashlib.md5(query_str.encode()).hexdigest()}"
            return cache_key
        
        return None
    
    async def _get_from_cache(self, cache_key: str) -> Any:
        """Get result from cache."""
        if hasattr(self._cache, 'get'):
            return await self._cache.get(cache_key)
        return None
    
    async def _store_in_cache(self, cache_key: str, result: Any) -> None:
        """Store result in cache."""
        if hasattr(self._cache, 'set'):
            # Default TTL of 5 minutes for query results
            await self._cache.set(cache_key, result, ttl=300)


# Middleware base classes

class CommandMiddleware:
    """Base class for command middleware."""
    
    async def before_execute(self, command: Command) -> None:
        """Called before command execution."""
        pass
    
    async def after_execute(self, command: Command, result: Any) -> None:
        """Called after successful command execution."""
        pass
    
    async def on_error(self, command: Command, error: Exception) -> None:
        """Called when command execution fails."""
        pass


class QueryMiddleware:
    """Base class for query middleware."""
    
    async def before_execute(self, query: Query) -> None:
        """Called before query execution."""
        pass
    
    async def after_execute(self, query: Query, result: Any) -> None:
        """Called after successful query execution."""
        pass
    
    async def on_error(self, query: Query, error: Exception) -> None:
        """Called when query execution fails."""
        pass


# Built-in middleware implementations

class LoggingMiddleware(CommandMiddleware, QueryMiddleware):
    """Middleware that logs command/query execution."""
    
    async def before_execute(self, operation) -> None:
        logger.info(f"Starting execution: {type(operation).__name__}")
    
    async def after_execute(self, operation, result) -> None:
        logger.info(f"Completed execution: {type(operation).__name__}")
    
    async def on_error(self, operation, error) -> None:
        logger.error(f"Execution failed: {type(operation).__name__} - {str(error)}")


class ValidationMiddleware(CommandMiddleware, QueryMiddleware):
    """Middleware that validates commands/queries before execution."""
    
    async def before_execute(self, operation) -> None:
        # Pydantic models are automatically validated
        # Additional business rule validation can be added here
        pass


class MetricsMiddleware(CommandMiddleware, QueryMiddleware):
    """Middleware that collects execution metrics."""
    
    def __init__(self):
        self.metrics = {
            'command_count': 0,
            'query_count': 0,
            'error_count': 0
        }
    
    async def before_execute(self, operation) -> None:
        if isinstance(operation, Command):
            self.metrics['command_count'] += 1
        elif isinstance(operation, Query):
            self.metrics['query_count'] += 1
    
    async def on_error(self, operation, error) -> None:
        self.metrics['error_count'] += 1
    
    def get_metrics(self) -> dict:
        """Get collected metrics."""
        return self.metrics.copy()