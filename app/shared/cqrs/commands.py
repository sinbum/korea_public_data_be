"""
Command pattern implementation for CQRS.

Commands represent write operations that change system state.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Any, Dict, Protocol
from pydantic import BaseModel
from datetime import datetime
import uuid

# Type variables
TResult = TypeVar('TResult')
TCommand = TypeVar('TCommand', bound='Command')


class Command(BaseModel, ABC):
    """
    Base command class.
    
    Commands represent operations that change system state.
    They should be immutable and contain all necessary data.
    """
    
    # Command metadata
    command_id: str = None
    timestamp: datetime = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __init__(self, **data):
        if not data.get('command_id'):
            data['command_id'] = str(uuid.uuid4())
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)
    
    class Config:
        # Commands should be immutable
        frozen = True
        # Allow arbitrary types for flexibility
        arbitrary_types_allowed = True


class CommandHandler(ABC, Generic[TCommand, TResult]):
    """
    Abstract base class for command handlers.
    
    Each command should have exactly one handler that processes it.
    """
    
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """
        Handle the command and return result.
        
        Args:
            command: The command to handle
            
        Returns:
            Command execution result
            
        Raises:
            Any business logic or validation exceptions
        """
        pass
    
    async def can_handle(self, command: Command) -> bool:
        """
        Check if this handler can process the given command.
        
        Default implementation checks command type.
        Can be overridden for more complex logic.
        """
        return isinstance(command, self._get_command_type())
    
    def _get_command_type(self) -> type:
        """Get the command type this handler processes."""
        # Extract from Generic type arguments
        import typing
        orig_bases = getattr(self.__class__, '__orig_bases__', ())
        for base in orig_bases:
            if hasattr(base, '__args__') and len(base.__args__) >= 1:
                return base.__args__[0]
        return Command


class ICommandBus(Protocol):
    """
    Command bus interface.
    
    Responsible for routing commands to appropriate handlers.
    """
    
    async def execute(self, command: Command) -> Any:
        """Execute a command and return the result."""
        ...
    
    def register_handler(self, command_type: type, handler: CommandHandler) -> None:
        """Register a command handler for a specific command type."""
        ...
    
    def unregister_handler(self, command_type: type) -> None:
        """Unregister a command handler."""
        ...


# Domain-specific command base classes

class AnnouncementCommand(Command):
    """Base class for announcement-related commands."""
    pass


class BusinessCommand(Command):
    """Base class for business-related commands."""
    pass


class ContentCommand(Command):
    """Base class for content-related commands.""" 
    pass


class StatisticsCommand(Command):
    """Base class for statistics-related commands."""
    pass


# Specific command implementations

class CreateAnnouncementCommand(AnnouncementCommand):
    """Command to create a new announcement."""
    
    title: str
    organization_name: str
    start_date: str
    end_date: str
    business_category_code: Optional[str] = None
    total_amount: Optional[str] = None
    detail_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class UpdateAnnouncementCommand(AnnouncementCommand):
    """Command to update an existing announcement."""
    
    announcement_id: str
    title: Optional[str] = None
    organization_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    business_category_code: Optional[str] = None
    total_amount: Optional[str] = None
    detail_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeleteAnnouncementCommand(AnnouncementCommand):
    """Command to delete an announcement."""
    
    announcement_id: str
    reason: Optional[str] = None


class FetchAnnouncementDataCommand(AnnouncementCommand):
    """Command to fetch announcement data from external API."""
    
    page_no: int = 1
    num_of_rows: int = 10
    business_name: Optional[str] = None
    business_type: Optional[str] = None


class CreateBusinessCommand(BusinessCommand):
    """Command to create a new business."""
    
    business_name: str
    business_category: str
    host_organization: Optional[str] = None
    supervision_organization: Optional[str] = None
    business_period: Optional[str] = None
    total_amount: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class UpdateBusinessCommand(BusinessCommand):
    """Command to update an existing business."""
    
    business_id: str
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    host_organization: Optional[str] = None
    supervision_organization: Optional[str] = None
    business_period: Optional[str] = None
    total_amount: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeleteBusinessCommand(BusinessCommand):
    """Command to delete a business."""
    
    business_id: str
    reason: Optional[str] = None


class FetchBusinessDataCommand(BusinessCommand):
    """Command to fetch business data from external API."""
    
    page_no: int = 1
    num_of_rows: int = 10


class CreateContentCommand(ContentCommand):
    """Command to create new content."""
    
    title: str
    content_type_code: str
    summary: Optional[str] = None
    organization_name: Optional[str] = None
    attachment_url: Optional[str] = None
    detail_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class UpdateContentCommand(ContentCommand):
    """Command to update existing content."""
    
    content_id: str
    title: Optional[str] = None
    content_type_code: Optional[str] = None
    summary: Optional[str] = None
    organization_name: Optional[str] = None
    attachment_url: Optional[str] = None
    detail_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeleteContentCommand(ContentCommand):
    """Command to delete content."""
    
    content_id: str
    reason: Optional[str] = None


class LikeContentCommand(ContentCommand):
    """Command to like content."""
    
    content_id: str


class FetchContentDataCommand(ContentCommand):
    """Command to fetch content data from external API."""
    
    page_no: int = 1
    num_of_rows: int = 10


class CreateStatisticsCommand(StatisticsCommand):
    """Command to create new statistics."""
    
    category: str
    year: int
    month: int
    value: float
    unit: str
    additional_data: Optional[Dict[str, Any]] = None


class UpdateStatisticsCommand(StatisticsCommand):
    """Command to update existing statistics."""
    
    statistics_id: str
    category: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeleteStatisticsCommand(StatisticsCommand):
    """Command to delete statistics."""
    
    statistics_id: str
    reason: Optional[str] = None


class FetchStatisticsDataCommand(StatisticsCommand):
    """Command to fetch statistics data from external API."""
    
    page_no: int = 1
    num_of_rows: int = 10