"""
CQRS (Command Query Responsibility Segregation) pattern implementation.

Provides clear separation between read (Query) and write (Command) operations.
"""

from .commands import Command, CommandHandler, ICommandBus
from .queries import Query, QueryHandler, IQueryBus
from .bus import CommandBus, QueryBus
from .decorators import command_handler, query_handler

__all__ = [
    # Base interfaces
    'Command',
    'Query',
    'CommandHandler',
    'QueryHandler',
    'ICommandBus',
    'IQueryBus',
    
    # Implementations
    'CommandBus',
    'QueryBus',
    
    # Decorators
    'command_handler',
    'query_handler'
]