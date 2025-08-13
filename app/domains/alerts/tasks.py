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
from .frequency_manager import NotificationFrequencyManager
from ...shared.clients.email_client import EmailClient
from ...shared.services.email_service import EmailService


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
                        # Check frequency manager for additional filtering
                        freq_manager = NotificationFrequencyManager(db)
                        should_send, reason = await freq_manager.should_send_notification(
                            sub["user_id"], 
                            "new_announcement", 
                            str(d.get("_id"))
                        )
                        
                        if should_send:
                            # Check for blocked content
                            is_blocked, block_reason = await freq_manager.is_content_blocked(sub["user_id"], d)
                            
                            if not is_blocked:
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
                            else:
                                logger.debug(f"Content {d.get('_id')} blocked for user {sub['user_id']}: {block_reason}")
                        else:
                            logger.debug(f"Notification skipped for user {sub['user_id']}: {reason}")
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
            # Check user notification preferences
            service = AlertsService(db)
            await service.init()
            
            # 1. Check if notification is allowed based on preferences
            is_allowed, preferences = await service.repository.is_notification_allowed(
                notif["user_id"], 
                notif.get("channel", "email"), 
                "new_announcements"  # Default category for regular notifications
            )
            if not is_allowed:
                logger.info("Notification blocked by user preferences for %s", notif["user_id"])
                await db["notifications"].update_one(
                    {"_id": notification_id},
                    {"$set": {"status": "skipped", "sent_at": datetime.utcnow()}}
                )
                return False
            
            # 2. Check quiet hours
            is_quiet, _ = await service.repository.check_quiet_hours(notif["user_id"])
            if is_quiet:
                logger.info("Notification blocked by quiet hours for %s", notif["user_id"])
                # Don't mark as failed, just skip for now (could reschedule later)
                return False
            
            # 3. Check daily limit (user preference + system limit)
            daily_allowed, current_count, max_daily = await service.repository.check_daily_limit(notif["user_id"])
            if not daily_allowed:
                logger.info("Daily notification limit reached for %s (%d/%d)", notif["user_id"], current_count, max_daily)
                await db["notifications"].update_one(
                    {"_id": notification_id},
                    {"$set": {"status": "skipped", "sent_at": datetime.utcnow()}}
                )
                return False
            
            # 4. Global rate limiting
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
            # Get content details for the notification
            content = await db[notif["domain"]].find_one({"_id": notif["content_id"]})
            if not content:
                logger.warning("Content not found for notification: %s", notification_id)
                return False
                
            # Get subscription details for matched keywords and threshold
            subscription = await db["alert_subscriptions"].find_one({"_id": notif["subscription_id"]})
            if not subscription:
                logger.warning("Subscription not found for notification: %s", notification_id)
                return False
            
            # Use EmailService for templated notification
            email_service = EmailService()
            
            result = await email_service.send_new_announcement_notification(
                user_email=to_email,
                user_name=(user or {}).get("name", "사용자"),
                announcement=content,
                matched_keywords=subscription.get("keywords", []),
                match_score=notif.get("score", 0.0),
                threshold=subscription.get("match_threshold", 0.5),
                tracking_id=str(notification_id)
            )
            
            # Update notification status
            await db["notifications"].update_one(
                {"_id": notification_id},
                {
                    "$set": {
                        "status": "sent" if result.get("success") else "failed",
                        "sent_at": datetime.utcnow(),
                        "delivery_info": {
                            "message_id": result.get("message_id"),
                            "template": "new_announcement",
                            "error": result.get("error")
                        }
                    }
                }
            )
            
            return result.get("success", False)

        return asyncio.run(_run())
    except Exception as e:
        logger.exception("send_notification failed: %s", e)
        raise


@shared_task(bind=True, name="app.domains.alerts.tasks.digest_daily")
def digest_daily(self) -> int:
    if not settings.alerts_enabled:
        logger.info("Alerts disabled, skipping digest_daily")
        return 0
    
    try:
        import asyncio
        
        async def _run() -> int:
            dbm = DatabaseManager()
            db = await dbm.get_async_database()
            
            # Get users who have daily digest enabled in preferences
            daily_users_prefs = await svc.repository.get_users_with_preferences(
                category="digest_notifications",
                digest_frequency="daily"
            )
            
            # Also include users with daily subscriptions (backward compatibility)
            daily_users_subs = db["alert_subscriptions"].find({
                "frequency": "daily",
                "is_active": True
            }).distinct("user_id")
            
            # Combine both sets of users
            all_daily_users = set()
            
            # Add users from preferences
            for pref in daily_users_prefs:
                all_daily_users.add(pref["user_id"])
            
            # Add users from subscriptions
            async for user_id in daily_users_subs:
                all_daily_users.add(user_id)
            
            sent_count = 0
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Initialize service for preference checks
            service = AlertsService(db)
            await service.init()
            
            for user_id in all_daily_users:
                try:
                    # Get user info
                    user = await db["users"].find_one({"_id": user_id})
                    if not user or not user.get("email"):
                        continue
                    
                    # Check if digest notifications are allowed for this user
                    is_allowed, preferences = await service.repository.is_notification_allowed(
                        user_id, 
                        "email", 
                        "digest_notifications"
                    )
                    if not is_allowed:
                        logger.debug(f"Digest notification blocked by preferences for {user_id}")
                        continue
                    
                    # Check quiet hours (digest could be sent during quiet time, but respect user preference)
                    is_quiet, _ = await service.repository.check_quiet_hours(user_id)
                    if is_quiet:
                        logger.debug(f"Digest blocked by quiet hours for {user_id}")
                        continue
                    
                    # Get user's subscriptions
                    user_subs = []
                    async for sub in db["alert_subscriptions"].find({
                        "user_id": user_id,
                        "is_active": True
                    }):
                        user_subs.append(sub)
                    
                    if not user_subs:
                        continue
                    
                    # Aggregate new announcements for the user
                    new_announcements = []
                    deadline_announcements = []
                    
                    for sub in user_subs:
                        # Find new announcements matching this subscription
                        service = AlertsService(db)
                        query = service.build_query("announcements", sub.get("keywords", []), sub.get("filters"))
                        if query:
                            query["created_at"] = {"$gte": yesterday}
                            
                            async for content in db["announcements"].find(query).limit(5):
                                new_announcements.append({
                                    **content,
                                    "url": f"{settings.frontend_url}/announcements/{content['_id']}",
                                    "match_score": 0.8  # Simplified for digest
                                })
                        
                        # Find deadline announcements
                        deadline_query = {}
                        if sub.get("filters"):
                            deadline_query = service.build_query("announcements", [], sub.get("filters"))
                        
                        # Announcements expiring in the next 7 days
                        deadline_query["application_end_date"] = {
                            "$gte": datetime.utcnow(),
                            "$lte": datetime.utcnow() + timedelta(days=7)
                        }
                        
                        async for content in db["announcements"].find(deadline_query).limit(5):
                            days_left = (content.get("application_end_date", datetime.utcnow()) - datetime.utcnow()).days
                            deadline_announcements.append({
                                **content,
                                "url": f"{settings.frontend_url}/announcements/{content['_id']}",
                                "days_left": max(0, days_left)
                            })
                    
                    # Remove duplicates
                    new_announcements = {ann["_id"]: ann for ann in new_announcements}.values()
                    deadline_announcements = {ann["_id"]: ann for ann in deadline_announcements}.values()
                    
                    # Generate stats
                    stats = {
                        "new_this_week": len(new_announcements),
                        "matched_this_week": len(new_announcements),
                        "deadline_this_week": len(deadline_announcements),
                        "popular_keywords": [kw for sub in user_subs for kw in sub.get("keywords", [])][:3]
                    }
                    
                    # Send digest email
                    email_service = EmailService()
                    result = await email_service.send_daily_digest(
                        user_email=user["email"],
                        user_name=user.get("name", "사용자"),
                        new_announcements=list(new_announcements),
                        deadline_announcements=list(deadline_announcements),
                        stats=stats,
                        tracking_id=f"digest_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}"
                    )
                    
                    if result.get("success"):
                        sent_count += 1
                        logger.info(f"Daily digest sent to {user['email']}")
                    else:
                        logger.warning(f"Failed to send digest to {user['email']}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error sending digest to user {user_id}: {e}")
                    continue
            
            logger.info(f"Daily digest completed: {sent_count} emails sent")
            return sent_count
        
        return asyncio.run(_run())
        
    except Exception as e:
        logger.exception("digest_daily failed: %s", e)
        raise

