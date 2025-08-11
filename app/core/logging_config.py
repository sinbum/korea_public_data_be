"""
Comprehensive logging and metrics collection with structured logging.

Provides advanced logging configuration with structured output, metrics collection,
performance monitoring, and correlation tracking for improved observability.
"""

import logging
import logging.handlers
import json
import sys
import time
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from functools import wraps
import traceback
import uuid

from .config import settings

class LogLevel(Enum):
    """Extended log levels"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 35  # Custom security level


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Remove None values to reduce log size
        return {k: v for k, v in result.items() if v is not None}


class CorrelationContext:
    """Thread-local correlation context"""
    
    def __init__(self):
        self._storage = threading.local()
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current thread"""
        self._storage.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread"""
        return getattr(self._storage, 'correlation_id', None)
    
    def set_request_context(self, request_id: str, user_id: str = None, 
                           session_id: str = None, client_ip: str = None,
                           user_agent: str = None):
        """Set request context for current thread"""
        self._storage.request_id = request_id
        self._storage.user_id = user_id
        self._storage.session_id = session_id
        self._storage.client_ip = client_ip
        self._storage.user_agent = user_agent
    
    def get_request_context(self) -> Dict[str, Optional[str]]:
        """Get request context for current thread"""
        return {
            'request_id': getattr(self._storage, 'request_id', None),
            'user_id': getattr(self._storage, 'user_id', None),
            'session_id': getattr(self._storage, 'session_id', None),
            'client_ip': getattr(self._storage, 'client_ip', None),
            'user_agent': getattr(self._storage, 'user_agent', None)
        }
    
    def clear(self):
        """Clear all context for current thread"""
        for attr in ['correlation_id', 'request_id', 'user_id', 'session_id', 
                     'client_ip', 'user_agent']:
            if hasattr(self._storage, attr):
                delattr(self._storage, attr)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.correlation_context = correlation_context
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Get correlation context
        correlation_id = self.correlation_context.get_correlation_id()
        request_context = self.correlation_context.get_request_context()
        
        # Extract extra fields
        extra = {}
        if self.include_extra:
            extra = {
                key: value for key, value in record.__dict__.items()
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'message'
                }
            }
        
        # Handle exception info
        if record.exc_info:
            extra['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Create structured log entry
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            correlation_id=correlation_id,
            request_id=request_context.get('request_id'),
            user_id=request_context.get('user_id'),
            session_id=request_context.get('session_id'),
            client_ip=request_context.get('client_ip'),
            user_agent=request_context.get('user_agent'),
            component=extra.pop('component', None),
            operation=extra.pop('operation', None),
            duration_ms=extra.pop('duration_ms', None),
            status_code=extra.pop('status_code', None),
            extra=extra if extra else None
        )
        
        return json.dumps(log_entry.to_dict(), ensure_ascii=False, default=str)


class MetricsCollector:
    """Collect and aggregate application metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {
            'requests': {'total': 0, 'by_status': {}, 'by_endpoint': {}},
            'response_times': {'total_ms': 0, 'count': 0, 'by_endpoint': {}},
            'errors': {'total': 0, 'by_type': {}, 'by_component': {}},
            'database': {'queries': 0, 'query_time_ms': 0, 'connections': 0},
            'cache': {'hits': 0, 'misses': 0, 'errors': 0},
            'security': {'blocked_requests': 0, 'suspicious_ips': set(), 'threats_detected': 0}
        }
        self._lock = threading.Lock()
    
    def record_request(self, endpoint: str, status_code: int, response_time_ms: float):
        """Record request metrics"""
        with self._lock:
            # Total requests
            self.metrics['requests']['total'] += 1
            
            # By status code
            status_key = str(status_code)
            self.metrics['requests']['by_status'][status_key] = \
                self.metrics['requests']['by_status'].get(status_key, 0) + 1
            
            # By endpoint
            self.metrics['requests']['by_endpoint'][endpoint] = \
                self.metrics['requests']['by_endpoint'].get(endpoint, 0) + 1
            
            # Response times
            self.metrics['response_times']['total_ms'] += response_time_ms
            self.metrics['response_times']['count'] += 1
            
            if endpoint not in self.metrics['response_times']['by_endpoint']:
                self.metrics['response_times']['by_endpoint'][endpoint] = {
                    'total_ms': 0, 'count': 0, 'avg_ms': 0
                }
            
            endpoint_times = self.metrics['response_times']['by_endpoint'][endpoint]
            endpoint_times['total_ms'] += response_time_ms
            endpoint_times['count'] += 1
            endpoint_times['avg_ms'] = endpoint_times['total_ms'] / endpoint_times['count']
    
    def record_error(self, error_type: str, component: str):
        """Record error metrics"""
        with self._lock:
            self.metrics['errors']['total'] += 1
            
            self.metrics['errors']['by_type'][error_type] = \
                self.metrics['errors']['by_type'].get(error_type, 0) + 1
            
            self.metrics['errors']['by_component'][component] = \
                self.metrics['errors']['by_component'].get(component, 0) + 1
    
    def record_database_query(self, query_time_ms: float):
        """Record database query metrics"""
        with self._lock:
            self.metrics['database']['queries'] += 1
            self.metrics['database']['query_time_ms'] += query_time_ms
    
    def record_database_connection(self):
        """Record database connection"""
        with self._lock:
            self.metrics['database']['connections'] += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        with self._lock:
            self.metrics['cache']['hits'] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        with self._lock:
            self.metrics['cache']['misses'] += 1
    
    def record_cache_error(self):
        """Record cache error"""
        with self._lock:
            self.metrics['cache']['errors'] += 1
    
    def record_security_event(self, event_type: str, client_ip: str = None):
        """Record security event"""
        with self._lock:
            if event_type == 'blocked_request':
                self.metrics['security']['blocked_requests'] += 1
            elif event_type == 'suspicious_ip' and client_ip:
                self.metrics['security']['suspicious_ips'].add(client_ip)
            elif event_type == 'threat_detected':
                self.metrics['security']['threats_detected'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        with self._lock:
            # Create a deep copy to avoid race conditions
            metrics_copy = {}
            for category, data in self.metrics.items():
                if category == 'security':
                    # Convert set to count for JSON serialization
                    metrics_copy[category] = {
                        k: (len(v) if isinstance(v, set) else v)
                        for k, v in data.items()
                    }
                else:
                    metrics_copy[category] = dict(data)
            
            # Calculate derived metrics
            if metrics_copy['response_times']['count'] > 0:
                metrics_copy['response_times']['avg_ms'] = \
                    metrics_copy['response_times']['total_ms'] / metrics_copy['response_times']['count']
            
            if metrics_copy['database']['queries'] > 0:
                metrics_copy['database']['avg_query_time_ms'] = \
                    metrics_copy['database']['query_time_ms'] / metrics_copy['database']['queries']
            
            # Cache hit rate
            total_cache_ops = metrics_copy['cache']['hits'] + metrics_copy['cache']['misses']
            if total_cache_ops > 0:
                metrics_copy['cache']['hit_rate'] = metrics_copy['cache']['hits'] / total_cache_ops
            
            return metrics_copy
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self.metrics = {
                'requests': {'total': 0, 'by_status': {}, 'by_endpoint': {}},
                'response_times': {'total_ms': 0, 'count': 0, 'by_endpoint': {}},
                'errors': {'total': 0, 'by_type': {}, 'by_component': {}},
                'database': {'queries': 0, 'query_time_ms': 0, 'connections': 0},
                'cache': {'hits': 0, 'misses': 0, 'errors': 0},
                'security': {'blocked_requests': 0, 'suspicious_ips': set(), 'threats_detected': 0}
            }


class LoggingManager:
    """Centralized logging management"""
    
    def __init__(self):
        self.configured = False
        self.log_dir = Path("logs")
        self.metrics_collector = MetricsCollector()
        self.handlers: List[logging.Handler] = []
    
    def setup_logging(self, 
                     log_level: str = "INFO",
                     log_dir: str = "logs",
                     max_file_size: int = 10 * 1024 * 1024,  # 10MB
                     backup_count: int = 5,
                     enable_console: bool = True,
                     enable_file: bool = True,
                     enable_json: bool = True) -> None:
        """Setup comprehensive logging configuration"""
        
        if self.configured:
            return
        
        # Create log directory
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            if enable_json:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                )
            root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        
        # File handlers
        if enable_file:
            # Main application log
            app_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "app.log",
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            app_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(app_handler)
            self.handlers.append(app_handler)
            
            # Error log
            error_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "error.log",
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(error_handler)
            self.handlers.append(error_handler)
            
            # Security log
            security_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "security.log",
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            security_handler.addFilter(lambda record: record.levelname == 'SECURITY')
            security_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(security_handler)
            self.handlers.append(security_handler)
            
            # Access log (for HTTP requests)
            access_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "access.log",
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            access_handler.addFilter(lambda record: hasattr(record, 'request_id'))
            access_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(access_handler)
            self.handlers.append(access_handler)
        
        # Add custom security level
        logging.addLevelName(LogLevel.SECURITY.value, 'SECURITY')
        
        self.configured = True
        logging.info("Logging system initialized")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with proper configuration"""
        return logging.getLogger(name)
    
    def log_security_event(self, message: str, **kwargs):
        """Log security event with special handling"""
        logger = logging.getLogger('security')
        logger.log(LogLevel.SECURITY.value, message, extra=kwargs)
        
        # Also record in metrics
        self.metrics_collector.record_security_event('threat_detected')
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics_collector.get_metrics()
    
    def close(self):
        """Close all handlers"""
        for handler in self.handlers:
            handler.close()
        self.handlers.clear()


# Global instances
correlation_context = CorrelationContext()
logging_manager = LoggingManager()
metrics_collector = logging_manager.metrics_collector


# Performance monitoring decorators
def log_performance(component: str = None, operation: str = None, 
                   log_args: bool = False, log_result: bool = False):
    """Decorator to log function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(func.__module__)
            
            operation_name = operation or func.__name__
            component_name = component or func.__module__.split('.')[-1]
            
            # Generate correlation ID if not exists
            if not correlation_context.get_correlation_id():
                correlation_context.set_correlation_id(str(uuid.uuid4())[:8])
            
            extra = {
                'component': component_name,
                'operation': operation_name
            }
            
            if log_args:
                extra['args'] = str(args)[:200]  # Limit length
                extra['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
            
            logger.info(f"Starting {operation_name}", extra=extra)
            
            try:
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                extra['duration_ms'] = duration_ms
                
                if log_result and result is not None:
                    extra['result'] = str(result)[:200]  # Limit length
                
                logger.info(f"Completed {operation_name}", extra=extra)
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                extra['duration_ms'] = duration_ms
                extra['error'] = str(e)
                
                logger.error(f"Failed {operation_name}", extra=extra, exc_info=True)
                
                # Record error metrics
                metrics_collector.record_error(type(e).__name__, component_name)
                
                raise
        
        return wrapper
    return decorator


# Initialize logging system
def setup_logging():
    """Setup logging system with default configuration"""
    logging_manager.setup_logging(
        log_level=settings.log_level,
        log_dir="logs",
        enable_console=settings.debug,
        enable_file=True,
        enable_json=True
    )

# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger"""
    return logging_manager.get_logger(name)

def get_metrics() -> Dict[str, Any]:
    """Get current application metrics"""
    return logging_manager.get_metrics()

def log_security_event(message: str, **kwargs):
    """Log security event"""
    logging_manager.log_security_event(message, **kwargs)

def set_correlation_id(correlation_id: str):
    """Set correlation ID for current request"""
    correlation_context.set_correlation_id(correlation_id)

def get_correlation_id() -> Optional[str]:
    """Get correlation ID for current request"""
    return correlation_context.get_correlation_id()

def set_request_context(request_id: str, user_id: str = None, 
                       session_id: str = None, client_ip: str = None,
                       user_agent: str = None):
    """Set request context"""
    correlation_context.set_request_context(
        request_id, user_id, session_id, client_ip, user_agent
    )

# Setup logging on import if not in test environment
if not os.getenv('TESTING'):
    setup_logging()