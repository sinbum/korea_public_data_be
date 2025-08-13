"""Initialize MongoDB indexes for Alerts domain.

Usage:
  python -m scripts.python.init_alerts_indexes
"""

from __future__ import annotations

import asyncio
import logging
from pymongo import ASCENDING, DESCENDING, TEXT

from app.core.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    dbm = DatabaseManager()
    db = await dbm.get_async_database()

    subs = db["alert_subscriptions"]
    notifs = db["notifications"]
    delivery_logs = db["delivery_logs"]

    logger.info("Creating indexes for alert_subscriptions...")
    
    # Subscriptions: user, active, frequency
    await subs.create_index([("user_id", ASCENDING), ("is_active", ASCENDING), ("frequency", ASCENDING)])
    
    # Index for active realtime subscriptions
    await subs.create_index(
        [("is_active", ASCENDING), ("frequency", ASCENDING)],
        name="idx_active_frequency"
    )
    
    # Index for user lookups
    await subs.create_index(
        [("user_id", ASCENDING)],
        name="idx_user_id"
    )

    logger.info("Creating indexes for notifications...")
    
    # Notifications unique: one per (user, subscription, content)
    await notifs.create_index(
        [("user_id", ASCENDING), ("subscription_id", ASCENDING), ("content_id", ASCENDING)],
        unique=True,
        name="uniq_user_sub_content",
    )
    
    # Index for pending notifications
    await notifs.create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)],
        name="idx_status_created"
    )
    
    # Index for user notifications
    await notifs.create_index(
        [("user_id", ASCENDING), ("status", ASCENDING)],
        name="idx_user_status"
    )
    
    # Index for notification queries by domain
    await notifs.create_index(
        [("domain", ASCENDING), ("created_at", DESCENDING)],
        name="idx_domain_created"
    )

    logger.info("Creating indexes for delivery_logs...")
    
    # Index for notification delivery logs
    await delivery_logs.create_index(
        [("notification_id", ASCENDING), ("attempt", DESCENDING)],
        name="idx_notification_attempt"
    )
    
    # Index for retry scheduling
    await delivery_logs.create_index(
        [("next_retry_at", ASCENDING)],
        name="idx_next_retry"
    )

    # Text indexes for content collections (for keyword matching)
    content_collections = ["announcements", "contents", "statistics", "businesses"]
    
    for collection_name in content_collections:
        if collection_name in await db.list_collection_names():
            logger.info(f"Creating text index for {collection_name} collection...")
            coll = db[collection_name]
            
            # Create text index on searchable fields
            # Note: Only one text index per collection is allowed
            try:
                await coll.create_index(
                    [("$**", TEXT)],  # Index all string fields
                    name="idx_text_search",
                    default_language="korean",  # Support Korean text search
                    language_override="language"
                )
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"Text index already exists for {collection_name}")
                else:
                    logger.warning(f"Could not create text index for {collection_name}: {e}")
            
            # Also create index on updated_at for efficient recent content queries
            await coll.create_index(
                [("updated_at", DESCENDING)],
                name="idx_updated_at"
            )

    logger.info("✅ Alerts indexes initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())

