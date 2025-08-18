from __future__ import annotations

from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from .models import AlertSubscription, Notification, DeliveryLog, NotificationPreference


class AlertsRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.subs = db["alert_subscriptions"]
        self.notifications = db["notifications"]
        self.delivery_logs = db["delivery_logs"]
        self.preferences = db["notification_preferences"]

    async def ensure_indexes(self) -> None:
        await self.subs.create_index([("user_id", ASCENDING), ("is_active", ASCENDING), ("frequency", ASCENDING)])
        await self.notifications.create_index([("user_id", ASCENDING), ("subscription_id", ASCENDING), ("content_id", ASCENDING)], unique=True)
        await self.preferences.create_index([("user_id", ASCENDING)], unique=True)

    async def create_subscription(self, doc: AlertSubscription) -> str:
        res = await self.subs.insert_one(doc.model_dump(by_alias=True))
        return str(res.inserted_id)

    async def list_subscriptions(self, user_id: Any) -> List[Dict[str, Any]]:
        cursor = self.subs.find({"user_id": user_id}).sort("created_at", DESCENDING)
        result = []
        async for doc in cursor:
            # Convert ObjectId to string for serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            if "id" in doc:
                doc["id"] = str(doc["id"])
            result.append(doc)
        return result

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

    # NotificationPreference CRUD methods
    async def get_user_preferences(self, user_id: Any) -> Optional[Dict[str, Any]]:
        """사용자의 알림 설정 조회"""
        doc = await self.preferences.find_one({"user_id": user_id})
        if doc:
            # Convert ObjectId to string for serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            if "id" in doc:
                doc["id"] = str(doc["id"])
        return doc

    async def create_user_preferences(self, preferences: NotificationPreference) -> str:
        """사용자의 알림 설정 생성"""
        res = await self.preferences.insert_one(preferences.model_dump(by_alias=True))
        return str(res.inserted_id)

    async def upsert_user_preferences(self, user_id: Any, preferences_data: Dict[str, Any]) -> bool:
        """사용자의 알림 설정 생성 또는 업데이트"""
        from datetime import datetime
        
        # updated_at 필드 추가
        preferences_data["updated_at"] = datetime.utcnow()
        
        res = await self.preferences.update_one(
            {"user_id": user_id},
            {
                "$set": preferences_data,
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        return res.matched_count > 0 or res.upserted_id is not None

    async def update_user_preferences(self, user_id: Any, updates: Dict[str, Any]) -> bool:
        """사용자의 알림 설정 부분 업데이트"""
        from datetime import datetime
        
        # 빈 업데이트는 건너뛰기
        if not updates:
            return True
            
        # None 값 제거
        filtered_updates = {k: v for k, v in updates.items() if v is not None}
        if not filtered_updates:
            return True
            
        # updated_at 필드 추가
        filtered_updates["updated_at"] = datetime.utcnow()
        
        res = await self.preferences.update_one(
            {"user_id": user_id},
            {"$set": filtered_updates}
        )
        return res.matched_count > 0

    async def delete_user_preferences(self, user_id: Any) -> bool:
        """사용자의 알림 설정 삭제"""
        res = await self.preferences.delete_one({"user_id": user_id})
        return res.deleted_count > 0

    async def get_default_preferences(self) -> Dict[str, Any]:
        """기본 알림 설정 반환"""
        default_preferences = NotificationPreference(user_id="default")
        return default_preferences.model_dump(exclude={"id", "user_id", "created_at", "updated_at"})

    async def get_users_with_preferences(self, 
                                       channel: Optional[str] = None,
                                       category: Optional[str] = None,
                                       digest_frequency: Optional[str] = None) -> List[Dict[str, Any]]:
        """특정 조건에 맞는 사용자들의 알림 설정 조회"""
        query = {}
        
        if channel and channel in ["email", "web", "push", "sms"]:
            query[f"{channel}_enabled"] = True
            
        if category and category in ["new_announcements", "deadline_reminders", "digest_notifications", "system_notifications", "marketing_notifications"]:
            query[category] = True
            
        if digest_frequency:
            query["digest_frequency"] = digest_frequency
            
        cursor = self.preferences.find(query)
        result = []
        async for doc in cursor:
            # Convert ObjectId to string for serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            if "id" in doc:
                doc["id"] = str(doc["id"])
            result.append(doc)
        return result

    async def is_notification_allowed(self, user_id: Any, channel: str, category: str) -> tuple[bool, Dict[str, Any]]:
        """사용자가 특정 채널/카테고리 알림을 받을지 확인"""
        preferences = await self.get_user_preferences(user_id)
        
        if not preferences:
            # 기본 설정 사용
            default_prefs = await self.get_default_preferences()
            channel_enabled = default_prefs.get(f"{channel}_enabled", True)
            category_enabled = default_prefs.get(category, True)
            return channel_enabled and category_enabled, default_prefs
        
        channel_enabled = preferences.get(f"{channel}_enabled", True)
        category_enabled = preferences.get(category, True)
        
        return channel_enabled and category_enabled, preferences

    async def check_quiet_hours(self, user_id: Any) -> tuple[bool, Dict[str, Any]]:
        """사용자의 현재 시간이 방해금지 시간인지 확인"""
        from datetime import datetime
        import pytz
        
        preferences = await self.get_user_preferences(user_id)
        
        if not preferences:
            return False, {}
            
        if not preferences.get("quiet_hours_enabled", False):
            return False, preferences
            
        timezone_str = preferences.get("quiet_hours_timezone", "Asia/Seoul")
        try:
            timezone = pytz.timezone(timezone_str)
            current_time = datetime.now(timezone)
            current_hour = current_time.hour
            
            start_hour = preferences.get("quiet_hours_start", 22)
            end_hour = preferences.get("quiet_hours_end", 7)
            
            # 방해금지 시간 처리 (예: 22시-7시)
            if start_hour > end_hour:
                # 다음날로 넘어가는 경우
                is_quiet = current_hour >= start_hour or current_hour < end_hour
            else:
                # 같은 날 안에서 처리
                is_quiet = start_hour <= current_hour < end_hour
                
            return is_quiet, preferences
            
        except Exception:
            # 시간대 처리 오류시 방해금지 시간이 아닌 것으로 처리
            return False, preferences

    async def get_daily_notification_count(self, user_id: Any) -> int:
        """사용자의 오늘 알림 발송 수 조회"""
        from datetime import datetime, timedelta
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        count = await self.notifications.count_documents({
            "user_id": user_id,
            "status": "sent",
            "sent_at": {
                "$gte": today_start,
                "$lt": today_end
            }
        })
        
        return count

    async def check_daily_limit(self, user_id: Any) -> tuple[bool, int, int]:
        """사용자의 일일 알림 한도 확인 (허용 여부, 현재 수, 최대 수)"""
        preferences = await self.get_user_preferences(user_id)
        max_daily = preferences.get("max_daily_notifications", 10) if preferences else 10
        
        current_count = await self.get_daily_notification_count(user_id)
        
        return current_count < max_daily, current_count, max_daily

