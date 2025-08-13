from __future__ import annotations

from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import AlertSubscription, Notification, AlertFilters
from .repository import AlertsRepository


class AlertsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repo = AlertsRepository(db)

    async def init(self) -> None:
        await self.repo.ensure_indexes()

    async def create_subscription(self, sub: AlertSubscription) -> str:
        return await self.repo.create_subscription(sub)

    async def list_subscriptions(self, user_id: Any) -> List[Dict[str, Any]]:
        return await self.repo.list_subscriptions(user_id)

    async def enqueue_notification(self, notif: Notification) -> None:
        # Upsert to avoid duplicates; actual send is handled by celery tasks
        await self.repo.upsert_notification(notif)

    # MVP text match builder using Mongo $text and filter conjunctions
    def build_query(self, domain: str, keywords: List[str], filters: Optional[AlertFilters | Dict[str, Any]]) -> Dict[str, Any]:
        query: Dict[str, Any] = {}
        if keywords:
            # phrase match for multiword, OR across keywords
            # e.g., "keyword1" "keyword2"
            search = " ".join([f'"{k}"' if " " in k else k for k in keywords])
            query["$text"] = {"$search": search}
        if filters:
            # Support both pydantic model and dict input
            def _get(name: str):
                if isinstance(filters, dict):
                    return filters.get(name)
                return getattr(filters, name)

            domain_filter = _get("domain")
            categories = _get("categories")
            regions = _get("regions")
            statuses = _get("statuses")
            start_date_from = _get("start_date_from")
            start_date_to = _get("start_date_to")

            if domain_filter:
                query["domain"] = domain_filter
            if categories:
                query["category"] = {"$in": categories}
            if regions:
                query["region"] = {"$in": regions}
            if statuses:
                query["status"] = {"$in": statuses}
            # Example date filter mapped to common fields
            date_range: Dict[str, Any] = {}
            if start_date_from:
                date_range["$gte"] = start_date_from
            if start_date_to:
                date_range["$lte"] = start_date_to
            if date_range:
                # try common fields in our domain collections
                query["published_at"] = date_range
        return query

