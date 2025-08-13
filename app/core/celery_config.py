"""
Enhanced Celery configuration with improved task management and monitoring.

Provides comprehensive Celery setup with error handling, monitoring, and optimization.
"""

from typing import Dict, Any, Optional, List
from datetime import timedelta
import os
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
from .config import settings

logger = logging.getLogger(__name__)


class CeleryConfig:
    """Enhanced Celery configuration class."""
    
    # Task execution settings
    task_time_limit = 30 * 60  # 30 minutes
    task_soft_time_limit = 25 * 60  # 25 minutes
    task_acks_late = True
    task_reject_on_worker_lost = True
    
    # Serialization settings
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    
    # Timezone settings
    timezone = "Asia/Seoul"
    enable_utc = True
    
    # Result backend settings
    result_expires = 60 * 60 * 24  # 24 hours
    # Simplified result backend settings for compatibility
    result_backend_transport_options = {
        "visibility_timeout": 3600,  # 1 hour
    }
    
    # Worker settings
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 1000
    worker_max_memory_per_child = 200000  # 200MB
    worker_disable_rate_limits = False
    worker_enable_remote_control = True
    
    # Connection settings
    broker_connection_retry_on_startup = True
    broker_connection_retry = True
    broker_connection_max_retries = 100
    broker_heartbeat = 120
    broker_pool_limit = 10
    
    # Task routing
    task_routes = {
        "app.domains.announcements.tasks.*": {"queue": "announcements"},
        "app.domains.businesses.tasks.*": {"queue": "businesses"},
        "app.domains.contents.tasks.*": {"queue": "contents"},
        "app.domains.statistics.tasks.*": {"queue": "statistics"},
        "app.shared.classification.tasks.*": {"queue": "classification"},
        "app.core.tasks.*": {"queue": "system"},
        "app.scheduler.monitoring_tasks.*": {"queue": "monitoring"},
    }
    # Conditionally add alerts routing to avoid importing tasks when disabled
    if settings.alerts_enabled:
        task_routes.update({
            "app.domains.alerts.tasks.match_and_enqueue": {"queue": settings.alerts_match_queue},
            "app.domains.alerts.tasks.send_notification": {"queue": settings.alerts_notify_queue},
            "app.domains.alerts.tasks.digest_daily": {"queue": settings.alerts_digest_queue},
        })
    
    # Queue configuration
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_routing_key = "default"
    
    # Advanced queue settings
    task_queue_ha_policy = "all"
    task_queue_max_priority = 10
    
    # Beat schedule (enhanced)
    beat_schedule = {
        # Data collection tasks
        "fetch-announcements-daily": {
            "task": "app.domains.announcements.tasks.fetch_announcements_comprehensive",
            "schedule": timedelta(hours=1),  # Every 1 hour
            "options": {"queue": "announcements", "priority": 5},
        },
        "fetch-businesses-daily": {
            "task": "app.domains.businesses.tasks.fetch_businesses_comprehensive",
            "schedule": timedelta(hours=8),  # Every 8 hours
            "options": {"queue": "businesses", "priority": 4},
        },
        "fetch-contents-daily": {
            "task": "app.domains.contents.tasks.fetch_contents_comprehensive",
            "schedule": timedelta(hours=12),  # Every 12 hours
            "options": {"queue": "contents", "priority": 4},
        },
        "fetch-statistics-daily": {
            "task": "app.domains.statistics.tasks.fetch_statistics_comprehensive",
            "schedule": timedelta(days=1),  # Daily
            "options": {"queue": "statistics", "priority": 3},
        },
        
        # Maintenance tasks
        "cleanup-old-tasks": {
            "task": "app.core.tasks.cleanup_old_task_results",
            "schedule": timedelta(hours=24),  # Daily
            "options": {"queue": "system", "priority": 2},
        },
        "health-check": {
            "task": "app.core.tasks.system_health_check",
            "schedule": timedelta(minutes=15),  # Every 15 minutes
            "options": {"queue": "monitoring", "priority": 7},
        },
        "generate-statistics": {
            "task": "app.core.tasks.generate_system_statistics",
            "schedule": timedelta(hours=4),  # Every 4 hours
            "options": {"queue": "system", "priority": 3},
        },
        
        # Data validation tasks
        "validate-data-integrity": {
            "task": "app.core.tasks.validate_data_integrity",
            "schedule": timedelta(hours=12),  # Twice daily
            "options": {"queue": "system", "priority": 6},
        },
        "classification-codes-validation": {
            "task": "app.shared.classification.tasks.validate_classification_usage",
            "schedule": timedelta(days=1),  # Daily
            "options": {"queue": "classification", "priority": 3},
        },
    }
    if settings.alerts_enabled:
        beat_schedule.update({
            # Alerts digest once per day at low priority
            "alerts-digest-daily": {
                "task": "app.domains.alerts.tasks.digest_daily",
                "schedule": timedelta(days=1),
                "options": {"queue": settings.alerts_digest_queue, "priority": 2},
            },
            # Match recent announcements every 15 minutes (canary friendly)
            "alerts-match-announcements-15m": {
                "task": "app.domains.alerts.tasks.match_and_enqueue",
                "schedule": timedelta(minutes=15),
                "options": {"queue": settings.alerts_match_queue, "priority": 5},
                "args": ("announcements", 15),
            },
        })
    
    # Task annotation settings
    task_annotations = {
        "*": {
            "rate_limit": "100/m",  # 100 tasks per minute default
        },
        "app.domains.announcements.tasks.fetch_announcements_comprehensive": {
            "rate_limit": "10/m",  # 10 per minute for heavy tasks
            "time_limit": 1800,  # 30 minutes
            "soft_time_limit": 1500,  # 25 minutes
        },
        "app.core.tasks.system_health_check": {
            "rate_limit": "20/m",  # 20 per minute for monitoring
            "time_limit": 300,  # 5 minutes
        },
    }
    
    # Error handling settings
    task_reject_on_worker_lost = True
    task_acks_late = True
    task_track_started = True
    task_send_sent_event = True
    
    # Security settings
    worker_hijack_root_logger = False
    worker_log_color = False
    
    # Monitoring settings
    worker_send_task_events = True
    task_send_sent_event = True
    
    @classmethod
    def get_broker_url(cls) -> str:
        """Get broker URL with basic configuration."""
        # Use basic Redis URL without problematic parameters
        return settings.redis_url
    
    @classmethod
    def get_result_backend_url(cls) -> str:
        """Get result backend URL with enhanced configuration."""
        return cls.get_broker_url()


def create_celery_app() -> Celery:
    """
    Create and configure Celery application with enhanced settings.
    
    Returns:
        Configured Celery application instance
    """
    # Create Celery app
    includes: List[str] = [
        "app.domains.announcements.tasks",
        "app.domains.businesses.tasks",
        "app.domains.contents.tasks",
        "app.domains.statistics.tasks",
        "app.shared.classification.tasks",
        "app.core.tasks",
        "app.scheduler.monitoring_tasks",
    ]
    if settings.alerts_enabled:
        includes.append("app.domains.alerts.tasks")

    celery_app = Celery(
        "korea_public_api",
        broker=CeleryConfig.get_broker_url(),
        backend=CeleryConfig.get_result_backend_url(),
        include=includes,
    )
    
    # Apply configuration
    celery_app.config_from_object(CeleryConfig)
    
    # Set up signal handlers
    setup_signal_handlers(celery_app)
    
    # Enable auto-discovery
    celery_app.autodiscover_tasks()
    
    logger.info("Enhanced Celery application created and configured")
    return celery_app


def setup_signal_handlers(celery_app: Celery) -> None:
    """Set up Celery signal handlers for monitoring and logging."""
    
    @task_prerun.connect
    def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
        """Handle task pre-run signal."""
        logger.info(f"Task {task.name} [{task_id}] started")
    
    @task_postrun.connect
    def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
        """Handle task post-run signal."""
        logger.info(f"Task {task.name} [{task_id}] completed with state: {state}")
    
    @task_failure.connect
    def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
        """Handle task failure signal."""
        logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")
        logger.error(f"Traceback: {traceback}")
    
    @task_retry.connect
    def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
        """Handle task retry signal."""
        logger.warning(f"Task {sender.name} [{task_id}] retrying: {reason}")


def get_task_info(task_name: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a specific task.
    
    Args:
        task_name: Name of the task
        
    Returns:
        Dictionary with task information
    """
    return {
        "name": task_name,
        "queue": CeleryConfig.task_routes.get(task_name, {}).get("queue", "default"),
        "annotations": CeleryConfig.task_annotations.get(task_name, {}),
        "schedule": None,  # Would be populated from beat_schedule if task is scheduled
    }


def get_queue_info() -> Dict[str, Any]:
    """
    Get information about all configured queues.
    
    Returns:
        Dictionary with queue information
    """
    queues = set()
    
    # Extract queues from routing
    for route_config in CeleryConfig.task_routes.values():
        if "queue" in route_config:
            queues.add(route_config["queue"])
    
    # Add default queue
    queues.add(CeleryConfig.task_default_queue)
    
    return {
        "total_queues": len(queues),
        "queues": list(queues),
        "default_queue": CeleryConfig.task_default_queue,
    }


def get_schedule_info() -> Dict[str, Any]:
    """
    Get information about scheduled tasks.
    
    Returns:
        Dictionary with schedule information
    """
    scheduled_tasks = []
    
    for task_name, schedule_config in CeleryConfig.beat_schedule.items():
        scheduled_tasks.append({
            "name": task_name,
            "task": schedule_config["task"],
            "schedule": str(schedule_config["schedule"]),
            "queue": schedule_config.get("options", {}).get("queue", "default"),
            "priority": schedule_config.get("options", {}).get("priority", 5),
        })
    
    return {
        "total_scheduled_tasks": len(scheduled_tasks),
        "tasks": scheduled_tasks,
    }


# Create the main Celery app instance
celery_app = create_celery_app()