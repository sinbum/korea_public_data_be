from __future__ import annotations

from fastapi import APIRouter

from .router import router as alerts_router


def get_v1_router() -> APIRouter:
    v1 = APIRouter(prefix="/v1")
    # Note: Intentionally NOT including alerts router into main app yet to avoid runtime impact
    v1.include_router(alerts_router)
    return v1

