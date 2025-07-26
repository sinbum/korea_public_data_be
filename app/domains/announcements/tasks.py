"""
Enhanced announcement domain tasks with comprehensive data collection and processing.

Implements robust data fetching, validation, and synchronization for announcement data
following the enhanced Celery architecture.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from celery import Task
from celery.exceptions import Retry

from ...core.celery_config import celery_app
from ...core.database import get_database
from ...shared.schemas import DataCollectionResult
from ...shared.classification.services import ClassificationService
from .service import AnnouncementService
from .models import AnnouncementCreate

logger = logging.getLogger(__name__)


class AnnouncementTask(Task):
    """Base task class for announcement operations with enhanced callbacks."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when announcement task succeeds."""
        logger.info(f"Announcement task {self.name} [{task_id}] completed successfully")
        if isinstance(retval, dict) and 'total_fetched' in retval:
            logger.info(f"Processed {retval['total_fetched']} announcements")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when announcement task fails."""
        logger.error(f"Announcement task {self.name} [{task_id}] failed: {exc}")
        logger.error(f"Error details: {einfo}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when announcement task is retried."""
        logger.warning(f"Announcement task {self.name} [{task_id}] retrying due to: {exc}")


@celery_app.task(
    bind=True, 
    base=AnnouncementTask, 
    max_retries=3, 
    default_retry_delay=300,
    time_limit=1800,  # 30 minutes
    soft_time_limit=1500  # 25 minutes
)
def fetch_announcements_comprehensive(self, 
                                    start_page: int = 1, 
                                    max_pages: Optional[int] = None,
                                    validate_codes: bool = True) -> Dict[str, Any]:
    """
    Comprehensive announcement data fetching with validation and classification.
    
    Args:
        start_page: Starting page number for data collection
        max_pages: Maximum number of pages to process (None for all)
        validate_codes: Whether to validate classification codes
        
    Returns:
        Dictionary with collection results and statistics
    """
    try:
        logger.info(f"Starting comprehensive announcement fetch from page {start_page}")
        
        result = asyncio.run(_fetch_announcements_async(
            start_page=start_page,
            max_pages=max_pages,
            validate_codes=validate_codes
        ))
        
        logger.info(f"Comprehensive announcement fetch completed: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"Error in comprehensive announcement fetch: {e}")
        self.retry(countdown=300, exc=e)


async def _fetch_announcements_async(start_page: int, 
                                   max_pages: Optional[int],
                                   validate_codes: bool) -> Dict[str, Any]:
    """Async implementation of comprehensive announcement fetching."""
    
    # Initialize services
    db = get_database()
    announcement_service = AnnouncementService(db)
    classification_service = ClassificationService() if validate_codes else None
    
    # Collection statistics
    stats = {
        "start_time": datetime.utcnow(),
        "pages_processed": 0,
        "total_fetched": 0,
        "total_created": 0,
        "total_updated": 0,
        "validation_errors": 0,
        "api_errors": 0,
        "classification_stats": {}
    }
    
    current_page = start_page
    consecutive_empty_pages = 0
    
    try:
        while True:
            # Check page limits
            if max_pages and (current_page - start_page + 1) > max_pages:
                logger.info(f"Reached maximum page limit: {max_pages}")
                break
            
            if consecutive_empty_pages >= 3:
                logger.info("Found 3 consecutive empty pages, stopping")
                break
            
            try:
                logger.info(f"Processing page {current_page}")
                
                # Fetch data from external API
                page_result = await announcement_service.fetch_and_save_announcements(
                    page_no=current_page,
                    num_of_rows=100
                )
                
                if not page_result or len(page_result) == 0:
                    consecutive_empty_pages += 1
                    logger.info(f"Empty page {current_page}, consecutive empty: {consecutive_empty_pages}")
                    current_page += 1
                    continue
                
                consecutive_empty_pages = 0
                stats["pages_processed"] += 1
                stats["total_fetched"] += len(page_result)
                
                # Process each announcement
                for announcement_data in page_result:
                    try:
                        # Validate classification codes if enabled
                        if validate_codes and classification_service:
                            await _validate_announcement_codes(
                                announcement_data, 
                                classification_service, 
                                stats
                            )
                        
                        # Determine if create or update
                        existing = await announcement_service.get_by_announcement_id(
                            announcement_data.get("announcement_id")
                        )
                        
                        if existing:
                            stats["total_updated"] += 1
                        else:
                            stats["total_created"] += 1
                            
                    except Exception as e:
                        stats["validation_errors"] += 1
                        logger.warning(f"Error processing announcement {announcement_data.get('announcement_id', 'unknown')}: {e}")
                
                logger.info(f"Page {current_page} completed: {len(page_result)} announcements")
                current_page += 1
                
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(1)
                
            except Exception as e:
                stats["api_errors"] += 1
                logger.error(f"Error fetching page {current_page}: {e}")
                current_page += 1
                
                if stats["api_errors"] >= 5:
                    logger.error("Too many API errors, stopping")
                    break
    
    except Exception as e:
        logger.error(f"Fatal error in announcement fetching: {e}")
        raise
    
    finally:
        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        stats["summary"] = (
            f"Processed {stats['pages_processed']} pages, "
            f"fetched {stats['total_fetched']} announcements, "
            f"created {stats['total_created']}, updated {stats['total_updated']}"
        )
    
    return stats


async def _validate_announcement_codes(announcement_data: Dict[str, Any], 
                                     classification_service: ClassificationService,
                                     stats: Dict[str, Any]) -> None:
    """Validate classification codes in announcement data."""
    
    # Check business category code if present
    biz_category = announcement_data.get("biz_category_cd")
    if biz_category:
        validation_result = await classification_service.validate_business_category(biz_category)
        if not validation_result.is_valid:
            logger.warning(f"Invalid business category code: {biz_category}")
            stats["validation_errors"] += 1
        else:
            # Track classification usage
            if "business_categories" not in stats["classification_stats"]:
                stats["classification_stats"]["business_categories"] = {}
            
            code_stats = stats["classification_stats"]["business_categories"]
            code_stats[biz_category] = code_stats.get(biz_category, 0) + 1


@celery_app.task(
    bind=True, 
    base=AnnouncementTask, 
    max_retries=2, 
    default_retry_delay=600
)
def validate_announcement_integrity(self) -> Dict[str, Any]:
    """
    Validate data integrity for announcement collection.
    
    Performs comprehensive validation of announcement data including:
    - Required field validation
    - Classification code validation
    - Data consistency checks
    - Duplicate detection
    """
    try:
        logger.info("Starting announcement data integrity validation")
        
        result = asyncio.run(_validate_announcement_integrity_async())
        
        logger.info(f"Announcement integrity validation completed: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"Error in announcement integrity validation: {e}")
        self.retry(countdown=600, exc=e)


async def _validate_announcement_integrity_async() -> Dict[str, Any]:
    """Async implementation of announcement integrity validation."""
    
    db = get_database()
    collection = db["announcements"]
    classification_service = ClassificationService()
    
    validation_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_announcements": 0,
        "validation_errors": [],
        "missing_fields": {},
        "invalid_codes": [],
        "duplicates": [],
        "data_quality_score": 0.0
    }
    
    try:
        # Get total count
        validation_results["total_announcements"] = collection.count_documents({})
        
        # Check for missing required fields
        required_fields = [
            "announcement_data.title",
            "announcement_data.organization_name",
            "announcement_data.announcement_id"
        ]
        
        for field in required_fields:
            missing_count = collection.count_documents({field: {"$exists": False}})
            if missing_count > 0:
                validation_results["missing_fields"][field] = missing_count
        
        # Validate classification codes
        pipeline = [
            {"$match": {"announcement_data.biz_category_cd": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$announcement_data.biz_category_cd", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        code_usage = list(collection.aggregate(pipeline))
        
        for code_info in code_usage:
            code = code_info["_id"]
            if code:  # Skip null values
                validation_result = await classification_service.validate_business_category(code)
                if not validation_result.is_valid:
                    validation_results["invalid_codes"].append({
                        "code": code,
                        "usage_count": code_info["count"],
                        "errors": validation_result.errors
                    })
        
        # Check for duplicates by announcement_id
        duplicate_pipeline = [
            {"$group": {
                "_id": "$announcement_data.announcement_id",
                "count": {"$sum": 1},
                "docs": {"$push": "$_id"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = list(collection.aggregate(duplicate_pipeline))
        validation_results["duplicates"] = [
            {
                "announcement_id": dup["_id"],
                "duplicate_count": dup["count"],
                "document_ids": [str(doc_id) for doc_id in dup["docs"]]
            }
            for dup in duplicates
        ]
        
        # Calculate data quality score
        total_issues = (
            sum(validation_results["missing_fields"].values()) +
            len(validation_results["invalid_codes"]) +
            len(validation_results["duplicates"])
        )
        
        if validation_results["total_announcements"] > 0:
            validation_results["data_quality_score"] = max(0, 
                1.0 - (total_issues / validation_results["total_announcements"])
            )
        
        validation_results["summary"] = (
            f"Validated {validation_results['total_announcements']} announcements, "
            f"found {total_issues} issues, "
            f"quality score: {validation_results['data_quality_score']:.2%}"
        )
        
    except Exception as e:
        logger.error(f"Error during announcement integrity validation: {e}")
        validation_results["error"] = str(e)
    
    return validation_results


@celery_app.task(
    bind=True, 
    base=AnnouncementTask, 
    max_retries=2, 
    default_retry_delay=900
)
def cleanup_announcement_duplicates(self) -> Dict[str, Any]:
    """
    Clean up duplicate announcements based on announcement_id.
    
    Keeps the most recent version of each announcement and removes duplicates.
    """
    try:
        logger.info("Starting announcement duplicate cleanup")
        
        result = asyncio.run(_cleanup_announcement_duplicates_async())
        
        logger.info(f"Announcement duplicate cleanup completed: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"Error in announcement duplicate cleanup: {e}")
        self.retry(countdown=900, exc=e)


async def _cleanup_announcement_duplicates_async() -> Dict[str, Any]:
    """Async implementation of announcement duplicate cleanup."""
    
    db = get_database()
    collection = db["announcements"]
    
    cleanup_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "duplicates_found": 0,
        "documents_removed": 0,
        "errors": []
    }
    
    try:
        # Find duplicates by announcement_id
        duplicate_pipeline = [
            {"$group": {
                "_id": "$announcement_data.announcement_id",
                "count": {"$sum": 1},
                "docs": {"$push": {
                    "doc_id": "$_id",
                    "created_at": "$created_at",
                    "updated_at": "$updated_at"
                }}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = list(collection.aggregate(duplicate_pipeline))
        cleanup_results["duplicates_found"] = len(duplicates)
        
        for duplicate_group in duplicates:
            try:
                docs = duplicate_group["docs"]
                
                # Sort by updated_at (most recent first), then by created_at
                docs.sort(key=lambda x: (
                    x.get("updated_at") or x.get("created_at", datetime.min),
                    x.get("created_at", datetime.min)
                ), reverse=True)
                
                # Keep the first (most recent) document, remove the rest
                docs_to_remove = docs[1:]
                
                for doc_to_remove in docs_to_remove:
                    result = collection.delete_one({"_id": doc_to_remove["doc_id"]})
                    if result.deleted_count > 0:
                        cleanup_results["documents_removed"] += 1
                        logger.debug(f"Removed duplicate document: {doc_to_remove['doc_id']}")
                
            except Exception as e:
                error_msg = f"Error processing duplicate group {duplicate_group['_id']}: {e}"
                cleanup_results["errors"].append(error_msg)
                logger.error(error_msg)
        
        cleanup_results["summary"] = (
            f"Found {cleanup_results['duplicates_found']} duplicate groups, "
            f"removed {cleanup_results['documents_removed']} duplicate documents"
        )
        
    except Exception as e:
        logger.error(f"Error during announcement duplicate cleanup: {e}")
        cleanup_results["error"] = str(e)
    
    return cleanup_results


@celery_app.task(
    bind=True, 
    base=AnnouncementTask, 
    max_retries=1
)
def generate_announcement_statistics(self) -> Dict[str, Any]:
    """
    Generate comprehensive statistics for announcement data.
    
    Provides insights into announcement distribution, categories, and trends.
    """
    try:
        logger.info("Generating announcement statistics")
        
        result = asyncio.run(_generate_announcement_statistics_async())
        
        logger.info("Announcement statistics generation completed")
        return result
        
    except Exception as e:
        logger.error(f"Error generating announcement statistics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "task": "generate_announcement_statistics"
        }


async def _generate_announcement_statistics_async() -> Dict[str, Any]:
    """Async implementation of announcement statistics generation."""
    
    db = get_database()
    collection = db["announcements"]
    
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": "generate_announcement_statistics",
        "overview": {},
        "categories": {},
        "organizations": {},
        "temporal": {},
        "data_quality": {}
    }
    
    try:
        # Overview statistics
        stats["overview"]["total_announcements"] = collection.count_documents({})
        stats["overview"]["active_announcements"] = collection.count_documents({
            "announcement_data.status": {"$ne": "expired"}
        })
        
        # Category distribution
        category_pipeline = [
            {"$match": {"announcement_data.biz_category_cd": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$announcement_data.biz_category_cd", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        category_distribution = list(collection.aggregate(category_pipeline))
        stats["categories"]["distribution"] = {
            cat["_id"]: cat["count"] for cat in category_distribution
        }
        stats["categories"]["total_categories"] = len(category_distribution)
        
        # Organization statistics
        org_pipeline = [
            {"$match": {"announcement_data.organization_name": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$announcement_data.organization_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_organizations = list(collection.aggregate(org_pipeline))
        stats["organizations"]["top_10"] = {
            org["_id"]: org["count"] for org in top_organizations
        }
        
        # Temporal analysis (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = collection.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        stats["temporal"]["recent_30_days"] = recent_count
        
        # Data quality metrics
        total_docs = stats["overview"]["total_announcements"]
        if total_docs > 0:
            missing_title = collection.count_documents({
                "announcement_data.title": {"$exists": False}
            })
            missing_org = collection.count_documents({
                "announcement_data.organization_name": {"$exists": False}
            })
            
            stats["data_quality"]["completeness_score"] = (
                1.0 - (missing_title + missing_org) / (total_docs * 2)
            )
        
    except Exception as e:
        logger.error(f"Error during announcement statistics generation: {e}")
        stats["error"] = str(e)
    
    return stats


# Legacy tasks for backward compatibility
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_announcements_task(self) -> Dict[str, Any]:
    """Legacy task - redirects to comprehensive fetch."""
    logger.info("Legacy fetch_announcements_task called - redirecting to comprehensive fetch")
    return fetch_announcements_comprehensive.apply_async(
        args=[1, 10, True],  # start_page=1, max_pages=10, validate_codes=True
        queue="announcements"
    ).get()


@celery_app.task(bind=True)
def cleanup_old_announcements_task(self, days: int = 30) -> Dict[str, Any]:
    """Legacy cleanup task - enhanced version."""
    try:
        logger.info(f"Starting enhanced cleanup of announcements older than {days} days")
        
        db = get_database()
        collection = db["announcements"]
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find and delete old announcements
        delete_filter = {
            "created_at": {"$lt": cutoff_date},
            "announcement_data.status": {"$in": ["expired", "closed"]}
        }
        
        delete_result = collection.delete_many(delete_filter)
        deleted_count = delete_result.deleted_count
        
        logger.info(f"Cleanup completed - deleted {deleted_count} old announcements")
        
        return {
            "task_id": self.request.id,
            "status": "success",
            "message": f"Deleted {deleted_count} old announcements",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during announcement cleanup: {e}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "message": f"Cleanup failed: {str(e)}"
        }


@celery_app.task(bind=True)
def sync_announcement_data_task(self, announcement_id: str) -> Dict[str, Any]:
    """Legacy sync task - enhanced version."""
    try:
        logger.info(f"Starting announcement sync for ID: {announcement_id}")
        
        db = get_database()
        announcement_service = AnnouncementService(db)
        
        # Find and sync specific announcement
        existing = announcement_service.get_by_announcement_id(announcement_id)
        
        if existing:
            # Refresh data from external API
            refreshed = announcement_service.fetch_announcement_by_id(announcement_id)
            if refreshed:
                updated = announcement_service.update(existing["id"], refreshed)
                logger.info(f"Successfully synced announcement: {announcement_id}")
                return {
                    "task_id": self.request.id,
                    "status": "success",
                    "message": "Announcement synced successfully",
                    "announcement_id": announcement_id,
                    "updated": True
                }
            else:
                logger.warning(f"Could not fetch fresh data for announcement: {announcement_id}")
                return {
                    "task_id": self.request.id,
                    "status": "warning",
                    "message": "Announcement exists but fresh data unavailable",
                    "announcement_id": announcement_id,
                    "updated": False
                }
        else:
            logger.warning(f"Announcement not found: {announcement_id}")
            return {
                "task_id": self.request.id,
                "status": "error",
                "message": "Announcement not found",
                "announcement_id": announcement_id
            }
        
    except Exception as e:
        logger.error(f"Error syncing announcement {announcement_id}: {e}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "message": f"Sync failed: {str(e)}",
            "announcement_id": announcement_id
        }


# Task registration helper
def get_announcement_tasks() -> List[Dict[str, Any]]:
    """Get list of all available announcement tasks."""
    return [
        {
            "name": "fetch_announcements_comprehensive",
            "description": "Comprehensive announcement data fetching with validation",
            "category": "data_collection",
            "estimated_duration": "15-30 minutes",
            "queue": "announcements"
        },
        {
            "name": "validate_announcement_integrity",
            "description": "Validate data integrity for announcement collection",
            "category": "validation",
            "estimated_duration": "5-10 minutes",
            "queue": "announcements"
        },
        {
            "name": "cleanup_announcement_duplicates",
            "description": "Clean up duplicate announcements",
            "category": "maintenance",
            "estimated_duration": "5-15 minutes",
            "queue": "announcements"
        },
        {
            "name": "generate_announcement_statistics",
            "description": "Generate comprehensive announcement statistics",
            "category": "analytics",
            "estimated_duration": "2-5 minutes",
            "queue": "announcements"
        }
    ]