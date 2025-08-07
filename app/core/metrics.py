from typing import Optional

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


