import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Simple JSON log formatter with minimal overhead."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Optional contextual fields
        request_id = getattr(record, "request_id", None)
        if request_id:
            log["request_id"] = request_id

        path = getattr(record, "path", None)
        if path:
            log["path"] = path

        method = getattr(record, "method", None)
        if method:
            log["method"] = method

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            log["status_code"] = status_code

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log["duration_ms"] = duration_ms

        return json.dumps(log, ensure_ascii=False)


def setup_logging(debug: bool, level: str) -> None:
    """Configure root logger. Uses JSON formatting in non-debug mode."""
    root = logging.getLogger()
    # Clear existing handlers to avoid duplicate logs
    for handler in list(root.handlers):
        root.removeHandler(handler)

    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()

    if debug:
        # Human-readable for local dev
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        formatter = JsonFormatter()

    handler.setFormatter(formatter)
    root.addHandler(handler)


