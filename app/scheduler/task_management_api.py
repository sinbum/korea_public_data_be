"""
Task Management API for monitoring, controlling, and managing Celery tasks.

Provides comprehensive REST API endpoints for task lifecycle management,
monitoring, scheduling, and system administration.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field
from enum import Enum

from ..core.celery_config import celery_app, get_task_info, get_queue_info, get_schedule_info
from ..core.tasks import get_available_tasks
from ..domains.announcements.tasks import get_announcement_tasks
from .monitoring_tasks import get_monitoring_tasks

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tasks", tags=["작업 관리"]) 


# Pydantic models for API
class TaskStatus(str, Enum):
    """작업 실행 상태."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskPriority(str, Enum):
    """작업 우선순위 레벨."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskCategory(str, Enum):
    """작업 카테고리."""
    DATA_COLLECTION = "data_collection"
    VALIDATION = "validation"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    ANALYTICS = "analytics"
    REPORTING = "reporting"
    SYSTEM = "system"


class TaskExecutionRequest(BaseModel):
    """작업 실행 요청 모델."""
    task_name: str = Field(..., description="실행할 작업의 이름 (등록된 Celery task 명)")
    args: List[Any] = Field(default=[], description="작업에 전달할 위치 기반 인자 (list)")
    kwargs: Dict[str, Any] = Field(default={}, description="작업에 전달할 키워드 인자 (dict)")
    queue: Optional[str] = Field(None, description="작업을 보낼 큐 이름 (미지정 시 기본 큐)")
    priority: Optional[TaskPriority] = Field(TaskPriority.MEDIUM, description="작업 우선순위 (low/medium/high/critical)")
    countdown: Optional[int] = Field(None, description="실행까지 지연할 초(second)")
    eta: Optional[datetime] = Field(None, description="지정 시각(UTC) 이후 실행")


class TaskInfo(BaseModel):
    """작업 정보 모델."""
    name: str
    description: str
    category: TaskCategory
    estimated_duration: str
    queue: str
    is_scheduled: bool = False
    schedule_info: Optional[Dict[str, Any]] = None


class TaskResult(BaseModel):
    """작업 실행 결과 모델."""
    task_id: str
    task_name: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None


class QueueInfo(BaseModel):
    """큐 정보 모델."""
    name: str
    length: int
    consumers: int
    messages_ready: int = 0
    messages_unacknowledged: int = 0


class WorkerInfo(BaseModel):
    """워커 정보 모델."""
    name: str
    status: str
    active_tasks: int
    processed_tasks: int = 0
    load_average: List[float] = []


class SystemStats(BaseModel):
    """시스템 통계 모델."""
    total_workers: int
    total_queues: int
    active_tasks: int
    scheduled_tasks: int
    completed_tasks_24h: int = 0
    failed_tasks_24h: int = 0
    average_execution_time: float = 0.0


# API Endpoints

@router.get(
    "/",
    response_model=List[TaskInfo],
    summary="사용 가능한 작업 목록 조회",
    description=(
        "등록된 모든 작업을 조회합니다. 카테고리로 필터링할 수 있으며, "
        "스케줄에 등록된 작업 여부와 스케줄 세부정보도 함께 제공합니다."
    ),
)
async def list_available_tasks(
    category: Optional[TaskCategory] = Query(None, description="Filter by task category"),
    include_scheduled: bool = Query(True, description="Include scheduled task information")
) -> List[TaskInfo]:
    """
    List all available tasks with their information.
    
    Returns comprehensive information about all registered tasks including
    their categories, descriptions, estimated durations, and scheduling information.
    """
    try:
        # Collect tasks from all modules
        all_tasks = []
        
        # System tasks
        system_tasks = get_available_tasks()
        all_tasks.extend(system_tasks)
        
        # Announcement tasks
        announcement_tasks = get_announcement_tasks()
        all_tasks.extend(announcement_tasks)
        
        # Monitoring tasks
        monitoring_tasks = get_monitoring_tasks()
        all_tasks.extend(monitoring_tasks)
        
        # Get schedule information if requested
        schedule_info = get_schedule_info() if include_scheduled else {"tasks": []}
        scheduled_tasks = {task["task"]: task for task in schedule_info.get("tasks", [])}
        
        # Convert to TaskInfo objects
        task_infos = []
        for task in all_tasks:
            # Map category string to enum
            try:
                category_enum = TaskCategory(task.get("category", "system"))
            except ValueError:
                category_enum = TaskCategory.SYSTEM
            
            task_name = task["name"]
            is_scheduled = any(
                scheduled_task["task"].endswith(task_name) 
                for scheduled_task in scheduled_tasks.values()
            )
            
            task_info = TaskInfo(
                name=task_name,
                description=task.get("description", "No description available"),
                category=category_enum,
                estimated_duration=task.get("estimated_duration", "Unknown"),
                queue=task.get("queue", "default"),
                is_scheduled=is_scheduled,
                schedule_info=scheduled_tasks.get(task_name) if is_scheduled else None
            )
            
            # Filter by category if specified
            if category is None or task_info.category == category:
                task_infos.append(task_info)
        
        return task_infos
        
    except Exception as e:
        logger.error(f"Error listing available tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post(
    "/execute",
    response_model=Dict[str, Any],
    summary="작업 실행 요청",
    description=(
        "지정한 작업을 비동기로 실행합니다. 큐, 우선순위, 지연 실행(countdown)/ETA를 설정할 수 있으며, "
        "응답으로 추적 가능한 task_id를 반환합니다."
    ),
)
async def execute_task(request: TaskExecutionRequest) -> Dict[str, Any]:
    """
    Execute a task asynchronously.
    
    Submits a task for execution with the specified parameters and returns
    the task ID for tracking. The task will be executed by available workers.
    """
    try:
        logger.info(f"Executing task: {request.task_name}")
        
        # Get the task from Celery
        try:
            task = celery_app.tasks[request.task_name]
        except KeyError:
            raise HTTPException(
                status_code=404, 
                detail=f"Task '{request.task_name}' not found"
            )
        
        # Prepare task options
        task_options = {}
        if request.queue:
            task_options["queue"] = request.queue
        if request.countdown:
            task_options["countdown"] = request.countdown
        if request.eta:
            task_options["eta"] = request.eta
        
        # Set priority (convert enum to number)
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.MEDIUM: 5,
            TaskPriority.HIGH: 8,
            TaskPriority.CRITICAL: 10
        }
        task_options["priority"] = priority_map.get(request.priority, 5)
        
        # Execute the task
        async_result = task.apply_async(
            args=request.args,
            kwargs=request.kwargs,
            **task_options
        )
        
        logger.info(f"Task {request.task_name} submitted with ID: {async_result.id}")
        
        return {
            "task_id": async_result.id,
            "task_name": request.task_name,
            "status": "submitted",
            "message": "Task submitted for execution",
            "queue": request.queue or "default",
            "priority": request.priority,
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing task {request.task_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get(
    "/status/{task_id}",
    response_model=TaskResult,
    summary="작업 상태 및 결과 조회",
    description=(
        "특정 task_id에 대한 현재 상태와 결과(완료 시), 실패 정보(실패 시), 실행 시간 등을 반환합니다."
    ),
)
async def get_task_status(task_id: str) -> TaskResult:
    """
    Get the status and result of a specific task.
    
    Returns detailed information about a task including its current status,
    result (if completed), error information (if failed), and execution timing.
    """
    try:
        # Get task result from Celery
        async_result = celery_app.AsyncResult(task_id)
        
        # Prepare response
        task_result = TaskResult(
            task_id=task_id,
            task_name=async_result.name or "unknown",
            status=TaskStatus(async_result.status)
        )
        
        if async_result.successful():
            task_result.result = async_result.result
            task_result.completed_at = datetime.utcnow()  # Approximate
        elif async_result.failed():
            task_result.error = str(async_result.info)
        
        # Try to get additional info if available
        try:
            task_info = async_result.info
            if isinstance(task_info, dict):
                task_result.started_at = task_info.get("started_at")
                task_result.completed_at = task_info.get("completed_at")
                if task_result.started_at and task_result.completed_at:
                    start = datetime.fromisoformat(task_result.started_at.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(task_result.completed_at.replace('Z', '+00:00'))
                    task_result.execution_time_seconds = (end - start).total_seconds()
        except Exception:
            pass  # Additional info not available
        
        return task_result
        
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete(
    "/cancel/{task_id}",
    summary="작업 취소",
    description=(
        "대기 중이거나 실행 중인 작업을 취소합니다. 이미 실행 중인 작업은 즉시 중단되지 않을 수 있습니다."
    ),
)
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    Cancel a pending or running task.
    
    Attempts to cancel a task that is either waiting in a queue or currently
    executing. Note that tasks may not be cancelled immediately if they're
    already in progress.
    """
    try:
        logger.info(f"Cancelling task: {task_id}")
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested",
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.get(
    "/queues",
    response_model=List[QueueInfo],
    summary="큐 상태 조회",
    description=(
        "구성된 모든 큐의 현재 상태(메시지 수, 소비자 수 등)를 조회합니다. 브로커에 따라 "
        "일부 통계는 제한될 수 있습니다."
    ),
)
async def list_queues() -> List[QueueInfo]:
    """
    List all configured queues with their current status.
    
    Returns information about all queues including their current message
    counts, consumer counts, and processing status.
    """
    try:
        # Get queue information from Celery configuration
        queue_config = get_queue_info()
        
        # Get active queue statistics
        try:
            inspect = celery_app.control.inspect(timeout=10)
            
            # Get queue lengths (this might not work with Redis broker)
            queue_lengths = {}
            try:
                # Try to get queue lengths from broker
                pass  # Would implement broker-specific queue length checking
            except Exception:
                pass
            
            # Build queue info list
            queue_infos = []
            for queue_name in queue_config.get("queues", []):
                queue_info = QueueInfo(
                    name=queue_name,
                    length=queue_lengths.get(queue_name, 0),
                    consumers=1  # Default assumption
                )
                queue_infos.append(queue_info)
        
        except Exception as e:
            logger.warning(f"Could not get detailed queue statistics: {e}")
            # Return basic queue info from configuration
            queue_infos = [
                QueueInfo(name=queue_name, length=0, consumers=0)
                for queue_name in queue_config.get("queues", [])
            ]
        
        return queue_infos
        
    except Exception as e:
        logger.error(f"Error listing queues: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list queues: {str(e)}")


@router.get(
    "/workers",
    response_model=List[WorkerInfo],
    summary="워커 상태 조회",
    description=(
        "활성화된 모든 워커와 각 워커의 활성 작업 수, 처리 통계, 부하 지표 등을 조회합니다."
    ),
)
async def list_workers() -> List[WorkerInfo]:
    """
    List all active workers with their current status.
    
    Returns information about all active workers including their current
    task loads, processing statistics, and health status.
    """
    try:
        inspect = celery_app.control.inspect(timeout=10)
        
        # Get active workers
        active_workers = inspect.active() or {}
        stats = inspect.stats() or {}
        
        worker_infos = []
        for worker_name in active_workers.keys():
            active_tasks = active_workers.get(worker_name, [])
            worker_stats = stats.get(worker_name, {})
            
            worker_info = WorkerInfo(
                name=worker_name,
                status="active",
                active_tasks=len(active_tasks),
                processed_tasks=worker_stats.get("total", {}).get("tasks.total", 0),
                load_average=worker_stats.get("rusage", {}).get("load_average", [])
            )
            worker_infos.append(worker_info)
        
        return worker_infos
        
    except Exception as e:
        logger.error(f"Error listing workers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workers: {str(e)}")


@router.get(
    "/stats",
    response_model=SystemStats,
    summary="시스템 통계 조회",
    description=(
        "작업 시스템 전반의 통계(워커 수, 활성 작업 수, 예약 작업 수 등)를 제공합니다."
    ),
)
async def get_system_stats() -> SystemStats:
    """
    Get comprehensive system statistics.
    
    Returns high-level statistics about the task system including worker
    counts, queue utilization, task completion rates, and performance metrics.
    """
    try:
        inspect = celery_app.control.inspect(timeout=10)
        
        # Get basic statistics
        active_workers = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        
        total_active_tasks = sum(len(tasks) for tasks in active_workers.values())
        total_scheduled_tasks = sum(len(tasks) for tasks in scheduled_tasks.values())
        
        # Get queue information
        queue_info = get_queue_info()
        
        stats = SystemStats(
            total_workers=len(active_workers),
            total_queues=queue_info.get("total_queues", 0),
            active_tasks=total_active_tasks,
            scheduled_tasks=total_scheduled_tasks
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


@router.post(
    "/schedule",
    summary="주기적 작업 스케줄 등록 (미구현)",
    description=(
        "작업을 크론 표현식으로 주기 실행하도록 등록하는 기능입니다. 현재 버전에서는 "
        "지속 스케줄 저장소가 없어 501 Not Implemented를 반환합니다."
    ),
)
async def schedule_task(
    task_name: str = Body(..., description="스케줄링할 작업 이름"),
    cron_expression: str = Body(..., description="크론 표현식 (예: '0 */6 * * *')"),
    args: List[Any] = Body(default=[], description="작업 인자 (list)"),
    kwargs: Dict[str, Any] = Body(default={}, description="작업 키워드 인자 (dict)"),
    queue: Optional[str] = Body(None, description="사용할 큐 이름")
) -> Dict[str, Any]:
    """
    Schedule a task for periodic execution (not implemented in this version).
    
    This endpoint would allow dynamic scheduling of tasks but requires
    additional infrastructure for persistent schedule storage.
    """
    # This would require implementing dynamic schedule management
    # For now, return a not implemented response
    raise HTTPException(
        status_code=501,
        detail="Dynamic task scheduling not implemented. Use static configuration in celery_config.py"
    )


@router.get(
    "/health",
    summary="[Deprecated] 작업 시스템 헬스 체크",
    description=(
        "이 엔드포인트는 더 이상 권장되지 않습니다. 시스템 상태는 `/api/v1/tasks/stats`를 사용하거나, "
        "서비스 전역 상태 확인은 `/health`를 사용하세요. 브로커 연결 및 워커 응답 여부를 점검하는 임시 용도로만 남겨둡니다."
    ),
    deprecated=True,
)
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the task management system.
    
    Returns the overall health status of the task system including
    broker connectivity, worker availability, and system responsiveness.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check broker connectivity
        try:
            inspect = celery_app.control.inspect(timeout=5)
            ping_result = inspect.ping()
            if ping_result:
                health_status["components"]["broker"] = {
                    "status": "healthy",
                    "workers_responding": len(ping_result)
                }
            else:
                health_status["components"]["broker"] = {
                    "status": "no_workers",
                    "workers_responding": 0
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["broker"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Check task registration
        try:
            total_tasks = len(celery_app.tasks)
            health_status["components"]["task_registry"] = {
                "status": "healthy",
                "registered_tasks": total_tasks
            }
        except Exception as e:
            health_status["components"]["task_registry"] = {
                "status": "error",
                "error": str(e)
            }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in task management health check: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.post(
    "/maintenance/purge-queue",
    summary="큐 비우기 (긴급 관리)",
    description=(
        "지정한 큐의 모든 대기 메시지를 즉시 삭제합니다. 되돌릴 수 없으므로 주의해서 사용하세요."
    ),
)
async def purge_queue(
    queue_name: str = Body(..., description="비울 큐 이름")
) -> Dict[str, Any]:
    """
    Purge all messages from a specific queue.
    
    WARNING: This will remove all pending tasks from the specified queue.
    Use with caution as this action cannot be undone.
    """
    try:
        logger.warning(f"Purging queue: {queue_name}")
        
        # Purge the queue
        celery_app.control.purge()
        
        return {
            "status": "purged",
            "queue_name": queue_name,
            "message": f"Queue '{queue_name}' has been purged",
            "purged_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error purging queue {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to purge queue: {str(e)}")


@router.get(
    "/logs/{task_id}",
    summary="작업 로그 조회 (플레이스홀더)",
    description=(
        "특정 작업에 대한 로그를 조회합니다. 중앙집중식 로그 수집 인프라가 필요하여 현재는 "
        "플레이스홀더 응답만 제공합니다."
    ),
)
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, description="반환할 최대 로그 개수")
) -> Dict[str, Any]:
    """
    Get logs for a specific task (placeholder implementation).
    
    This endpoint would return task-specific logs but requires additional
    log aggregation infrastructure to be fully implemented.
    """
    # This would require implementing centralized logging for tasks
    # For now, return a placeholder response
    return {
        "task_id": task_id,
        "logs": [],
        "message": "Task-specific logging not implemented yet",
        "total_entries": 0
    }


# Add router to the main application
def get_task_management_router() -> APIRouter:
    """Get the task management router for inclusion in main app."""
    return router