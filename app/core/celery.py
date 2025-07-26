"""
Legacy Celery configuration for backward compatibility.

This module maintains the legacy celery_app import for existing code
while redirecting to the enhanced Celery configuration.
"""

import warnings
from .celery_config import celery_app

# Issue deprecation warning for legacy imports
warnings.warn(
    "Importing celery_app from app.core.celery is deprecated. "
    "Use 'from app.core.celery_config import celery_app' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Export the enhanced celery_app for backward compatibility
__all__ = ["celery_app"]

if __name__ == "__main__":
    celery_app.start()