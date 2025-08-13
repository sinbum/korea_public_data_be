from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from celery import shared_task
from pymongo import ASCENDING, DESCENDING

from ...core.celery_config import celery_app
from ...core.config import settings
from ...core.database import DatabaseManager
from ...core.rate_limiter import RateLimiter, RateLimitConfig, RateLimitStrategy
from .models import Notification
from .service import AlertsService
from ...shared.clients.email_client import EmailClient


logger = logging.getLogger(__name__)


async def _get_service() -> AlertsService:
    dbm = DatabaseManager()
    db = await dbm.get_async_database()
    service = AlertsService(db)
    await service.init()
    return service


@shared_task(bind=True, name="app.domains.alerts.tasks.match_and_enqueue")
def match_and_enqueue(self, domain: str, since_minutes: int = 15) -> int:
    """Batch match recent contents and enqueue notifications.
    Safe to enable only when settings.alerts_enabled is True.
    """
    if not settings.alerts_enabled:
        logger.info("Alerts disabled, skipping match_and_enqueue")
        return 0

    try:
        import asyncio

        async def _run() -> int:
            dbm = DatabaseManager()
            db = await dbm.get_async_database()
            service = AlertsService(db)
            await service.init()

            # Determine target collection by domain
            collection = db[domain]

            since = datetime.utcnow() - timedelta(minutes=since_minutes)
            cursor = collection.find({"updated_at": {"$gte": since}}).sort("updated_at", DESCENDING)

            matched = 0
            # Fetch active subscriptions (simple: all realtime)
            subs_cursor = db["alert_subscriptions"].find({"is_active": True, "frequency": "realtime"})
            subs = [s async for s in subs_cursor]

            for sub in subs:
                query = service.build_query(domain, sub.get("keywords", []), sub.get("filters"))
                if not query:
                    continue
                # Get match threshold (default to 0.5 if not set)
                threshold = sub.get("match_threshold", 0.5)
                
                # Search recent docs matched by subscription
                docs = collection.find({"updated_at": {"$gte": since}, **query}, projection={"score": {"$meta": "textScore"}}).sort("score", DESCENDING)
                async for d in docs:
                    # Normalize text score (MongoDB text scores typically range from 0 to a few points)
                    # We'll normalize by dividing by keyword count as a simple heuristic
                    raw_score = d.get("score", 0)
                    keyword_count = len(sub.get("keywords", []))
                    normalized_score = min(1.0, raw_score / max(1, keyword_count))
                    
                    # Only create notification if score meets threshold
                    if normalized_score >= threshold:
                        notif = Notification(
                            subscription_id=sub["_id"],
                            user_id=sub["user_id"],
                            domain=domain,
                            content_id=d.get("_id"),
                            channel=(sub.get("channels") or ["email"])[0],
                            score=normalized_score,
                        )
                        await service.enqueue_notification(notif)
                        matched += 1
                        logger.debug(f"Matched content {d.get('_id')} with score {normalized_score:.2f} (threshold: {threshold})")
            return matched

        return asyncio.run(_run())

    except Exception as e:
        logger.exception("match_and_enqueue failed: %s", e)
        raise


@shared_task(bind=True, name="app.domains.alerts.tasks.send_notification", autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_notification(self, notification_id: str) -> bool:
    if not settings.alerts_enabled:
        logger.info("Alerts disabled, skipping send_notification")
        return False
    # Scaffold: fetch notification+user and send via EmailClient(dev)
    try:
        import asyncio

        async def _run() -> bool:
            dbm = DatabaseManager()
            db = await dbm.get_async_database()
            notif = await db["notifications"].find_one({"_id": notification_id})
            if not notif:
                logger.warning("Notification not found: %s", notification_id)
                return False
            user = await db["users"].find_one({"_id": notif["user_id"]})
            to_email = (user or {}).get("email")
            if not to_email:
                logger.warning("User email not found for: %s", notif.get("user_id"))
                return False
            # Global RPS limiter (sliding window per second)
            global_limiter = RateLimiter(
                RateLimitConfig(
                    requests=max(1, settings.alerts_global_rps),
                    window=1,
                    strategy=RateLimitStrategy.SLIDING_WINDOW,
                )
            )
            ok, _ = await global_limiter.check_rate_limit("alerts:global")
            if not ok:
                logger.info("Global alert send rate limited")
                return False
            # Per-user daily cap
            user_limiter = RateLimiter(
                RateLimitConfig(
                    requests=max(1, settings.alerts_user_daily_cap),
                    window=24 * 60 * 60,
                    strategy=RateLimitStrategy.FIXED_WINDOW,
                )
            )
            ok_user, _ = await user_limiter.check_rate_limit(f"alerts:user:{notif['user_id']}")
            if not ok_user:
                logger.info("User daily cap reached for %s", notif["user_id"])
                return False
            client = EmailClient(provider="dev")
            subject = "[알림] 관심 키워드에 새 콘텐츠가 매칭되었습니다"
            html = f"<p>도메인: {notif.get('domain')}</p><p>콘텐츠 ID: {notif.get('content_id')}</p>"
            res = client.send(to=to_email, subject=subject, html=html, meta={"notification_id": str(notification_id)})
            return bool(res.get("ok"))

        return asyncio.run(_run())
    except Exception as e:
        logger.exception("send_notification failed: %s", e)
        raise


@shared_task(bind=True, name="app.domains.alerts.tasks.digest_daily")
def digest_daily(self) -> int:
    if not settings.alerts_enabled:
        logger.info("Alerts disabled, skipping digest_daily")
        return 0
    logger.info("Running daily digest (scaffold)")
    return 0

