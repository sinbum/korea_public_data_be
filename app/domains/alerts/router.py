from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, List

from ...core.config import settings
from ...core.database import DatabaseManager
from .schemas import SubscriptionCreateRequest, SubscriptionResponse, NotificationPreviewRequest
from .models import AlertSubscription
from .service import AlertsService


router = APIRouter(prefix="/alerts", tags=["alerts"])


async def get_service() -> AlertsService:
    dbm = DatabaseManager()
    db = await dbm.get_async_database()
    service = AlertsService(db)
    await service.init()
    return service


@router.post("/subscriptions", response_model=dict)
async def create_subscription(payload: SubscriptionCreateRequest, svc: AlertsService = Depends(get_service)):
    if not settings.alerts_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alerts feature disabled")

    sub = AlertSubscription(
        user_id="me",  # TODO: replace with authenticated user id dependency
        keywords=payload.keywords,
        filters=payload.filters or {},
        channels=payload.channels or ["email"],
        frequency=payload.frequency or "realtime",
    )
    sub_id = await svc.create_subscription(sub)
    return {"id": sub_id}


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def list_subscriptions(svc: AlertsService = Depends(get_service)):
    if not settings.alerts_enabled:
        return []
    docs = await svc.list_subscriptions("me")  # TODO: replace with authenticated user id
    return docs


@router.post("/test", response_model=dict)
async def preview_matches(req: NotificationPreviewRequest):
    if not settings.alerts_enabled:
        return {"total": 0, "items": []}
    # Scaffold: return empty preview for now
    return {"total": 0, "items": []}

