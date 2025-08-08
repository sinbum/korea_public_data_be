from typing import Optional
import asyncio
from typing import Tuple

from fastapi import FastAPI

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    from prometheus_fastapi_instrumentator.metrics import (
        default,
        request_size,
        response_size,
    )
except Exception:  # pragma: no cover - optional dependency
    Instrumentator = None  # type: ignore
    default = request_size = response_size = None  # type: ignore

try:
    from prometheus_client import Gauge  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Gauge = None  # type: ignore


def init_metrics(app: FastAPI, enabled: bool = True, endpoint: str = "/metrics") -> Optional[object]:
    """Initialize Prometheus metrics if dependency is available.

    Avoids high-cardinality labels (e.g., request_id). Groups by handler/method/status.
    """
    if not enabled or Instrumentator is None:
        return None

    instr = (
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            excluded_handlers={"/health", "/docs", "/redoc", "/openapi.json"},
            env_var_name="ENABLE_METRICS",
        )
        .add(default())
        .add(request_size())
        .add(response_size())
    )

    instr.instrument(app).expose(app, endpoint=endpoint, include_in_schema=False)
    return instr


# -----------------------------
# Celery runtime metrics (poll)
# -----------------------------

# Gauges are global so Prometheus can scrape current values
if Gauge is not None:
    CELERY_WORKERS_GAUGE = Gauge(
        "korea_celery_workers_total",
        "Total active Celery workers",
    )
    CELERY_ACTIVE_TASKS_GAUGE = Gauge(
        "korea_celery_tasks_active_total",
        "Total active Celery tasks across all workers",
    )
    CELERY_SCHEDULED_TASKS_GAUGE = Gauge(
        "korea_celery_tasks_scheduled_total",
        "Total scheduled Celery tasks across all workers",
    )
    CELERY_QUEUES_GAUGE = Gauge(
        "korea_celery_queues_total",
        "Total configured Celery queues",
    )
else:  # pragma: no cover
    CELERY_WORKERS_GAUGE = None  # type: ignore
    CELERY_ACTIVE_TASKS_GAUGE = None  # type: ignore
    CELERY_SCHEDULED_TASKS_GAUGE = None  # type: ignore
    CELERY_QUEUES_GAUGE = None  # type: ignore


async def _collect_celery_runtime() -> Tuple[int, int, int, int]:
    """Collect basic Celery runtime stats.

    Returns: (workers, active_tasks, scheduled_tasks, queues)
    """
    try:
        from app.core.celery_config import celery_app, get_queue_info  # local import to avoid cycles

        inspect = celery_app.control.inspect(timeout=10)
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}

        workers = len(active)
        active_tasks = sum(len(tasks) for tasks in active.values()) if active else 0
        scheduled_tasks = sum(len(tasks) for tasks in scheduled.values()) if scheduled else 0
        queue_info = get_queue_info() or {}
        queues = int(queue_info.get("total_queues", 0))

        return workers, active_tasks, scheduled_tasks, queues
    except Exception:
        return 0, 0, 0, 0


async def poll_celery_metrics(stop_event: asyncio.Event, interval_seconds: int = 15) -> None:
    """Background polling loop to keep Celery gauges up-to-date."""
    if Gauge is None:
        return

    while not stop_event.is_set():
        workers, active_tasks, scheduled_tasks, queues = await _collect_celery_runtime()
        try:
            CELERY_WORKERS_GAUGE.set(workers)
            CELERY_ACTIVE_TASKS_GAUGE.set(active_tasks)
            CELERY_SCHEDULED_TASKS_GAUGE.set(scheduled_tasks)
            CELERY_QUEUES_GAUGE.set(queues)
        except Exception:
            # Best-effort metrics; ignore update errors
            pass

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
