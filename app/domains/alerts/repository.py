from __future__ import annotations

from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from .models import AlertSubscription, Notification, DeliveryLog


class AlertsRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.subs = db["alert_subscriptions"]
        self.notifications = db["notifications"]
        self.delivery_logs = db["delivery_logs"]

    async def ensure_indexes(self) -> None:
        await self.subs.create_index([("user_id", ASCENDING), ("is_active", ASCENDING), ("frequency", ASCENDING)])
        await self.notifications.create_index([("user_id", ASCENDING), ("subscription_id", ASCENDING), ("content_id", ASCENDING)], unique=True)

    async def create_subscription(self, doc: AlertSubscription) -> str:
        res = await self.subs.insert_one(doc.model_dump(by_alias=True))
        return str(res.inserted_id)

    async def list_subscriptions(self, user_id: Any) -> List[Dict[str, Any]]:
        cursor = self.subs.find({"user_id": user_id}).sort("created_at", DESCENDING)
        return [doc async for doc in cursor]

    async def upsert_notification(self, notif: Notification) -> Optional[str]:
        try:
            res = await self.notifications.update_one(
                {
                    "user_id": notif.user_id,
                    "subscription_id": notif.subscription_id,
                    "content_id": notif.content_id,
                },
                {"$setOnInsert": notif.model_dump(by_alias=True)},
                upsert=True,
            )
            if res.upserted_id:
                return str(res.upserted_id)
            return None
        except DuplicateKeyError:
            return None

