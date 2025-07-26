"""
Content domain Celery tasks.

Provides asynchronous task processing for content-related operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from celery import shared_task
from ...core.celery_config import celery_app
from ...core.database import get_database
from .service import ContentService
from .repository import ContentRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.domains.contents.tasks.fetch_contents_comprehensive")
def fetch_contents_comprehensive(
    self,
    page_no: int = 1,
    num_of_rows: int = 50,
    content_type: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive content data fetching task.
    
    Args:
        page_no: Page number to fetch
        num_of_rows: Number of rows per page
        content_type: Content type filter
        category: Category filter
        
    Returns:
        Dictionary with task results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = ContentRepository(db.contents)
        api_client = KStartupAPIClient()
        service = ContentService(repository, api_client)
        
        # Perform data fetch
        start_time = datetime.utcnow()
        contents = service.fetch_and_save_contents(
            page_no=page_no,
            num_of_rows=num_of_rows,
            content_type=content_type,
            category=category
        )
        end_time = datetime.utcnow()
        
        # Prepare result
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "fetched_count": len(contents),
            "page_no": page_no,
            "filters": {
                "content_type": content_type,
                "category": category
            },
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully fetched {len(contents)} contents")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to fetch contents: {exc}")
        # Retry logic
        if self.request.retries < 3:
            logger.info(f"Retrying task {self.request.id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        # Final failure
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.contents.tasks.fetch_contents_incremental")
def fetch_contents_incremental(self, max_pages: int = 5) -> Dict[str, Any]:
    """
    Incremental content data fetching task.
    
    Args:
        max_pages: Maximum number of pages to fetch
        
    Returns:
        Dictionary with task results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = ContentRepository(db.contents)
        api_client = KStartupAPIClient()
        service = ContentService(repository, api_client)
        
        start_time = datetime.utcnow()
        total_fetched = 0
        
        # Fetch multiple pages
        for page in range(1, max_pages + 1):
            try:
                contents = service.fetch_and_save_contents(
                    page_no=page,
                    num_of_rows=20
                )
                total_fetched += len(contents)
                
                # Break if no more data
                if len(contents) == 0:
                    break
                    
            except Exception as page_exc:
                logger.warning(f"Failed to fetch page {page}: {page_exc}")
                continue
        
        end_time = datetime.utcnow()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "total_fetched": total_fetched,
            "pages_processed": page,
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Incremental fetch completed: {total_fetched} contents")
        return result
        
    except Exception as exc:
        logger.error(f"Failed incremental fetch: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.contents.tasks.update_content_metrics")
def update_content_metrics(self) -> Dict[str, Any]:
    """
    Update content metrics like view counts, like counts, etc.
    
    Returns:
        Dictionary with update results
    """
    try:
        # Initialize dependencies
        db = get_database()
        
        # Update metrics (placeholder logic)
        # In a real scenario, this would update view counts, like counts, etc.
        # based on actual user interaction data
        
        updated_count = 0
        
        # Example: Reset metrics for testing or update based on external data
        # This is a placeholder implementation
        result = db.contents.update_many(
            {"is_active": True},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        updated_count = result.modified_count
        
        task_result = {
            "task_id": self.request.id,
            "status": "completed",
            "updated_count": updated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Updated metrics for {updated_count} contents")
        return task_result
        
    except Exception as exc:
        logger.error(f"Failed to update content metrics: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.contents.tasks.cleanup_inactive_contents")
def cleanup_inactive_contents(self, days_old: int = 180) -> Dict[str, Any]:
    """
    Clean up inactive contents older than specified days.
    
    Args:
        days_old: Number of days to consider for cleanup
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        # Initialize dependencies
        db = get_database()
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find and deactivate old contents
        filter_criteria = {
            "is_active": True,
            "updated_at": {"$lt": cutoff_date}
        }
        
        # Update inactive contents
        result = db.contents.update_many(
            filter_criteria,
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        cleanup_result = {
            "task_id": self.request.id,
            "status": "completed",
            "deactivated_count": result.modified_count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Deactivated {result.modified_count} inactive contents")
        return cleanup_result
        
    except Exception as exc:
        logger.error(f"Failed to cleanup contents: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.contents.tasks.generate_content_statistics")
def generate_content_statistics(self) -> Dict[str, Any]:
    """
    Generate comprehensive content statistics.
    
    Returns:
        Dictionary with statistics
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = ContentRepository(db.contents)
        service = ContentService(repository)
        
        # Generate statistics
        stats = service.get_content_statistics()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Content statistics generated successfully")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to generate content statistics: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.contents.tasks.validate_content_data")
def validate_content_data(self) -> Dict[str, Any]:
    """
    Validate content data integrity.
    
    Returns:
        Dictionary with validation results
    """
    try:
        # Initialize dependencies
        db = get_database()
        
        # Validation checks
        total_count = db.contents.count_documents({})
        active_count = db.contents.count_documents({"is_active": True})
        invalid_count = db.contents.count_documents({
            "$or": [
                {"content_data": {"$exists": False}},
                {"content_data": None},
                {"content_data": {}}
            ]
        })
        
        # Check for duplicates (basic check on source_url)
        pipeline = [
            {"$group": {"_id": "$source_url", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(db.contents.aggregate(pipeline))
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "validation_results": {
                "total_contents": total_count,
                "active_contents": active_count,
                "invalid_contents": invalid_count,
                "duplicate_sources": len(duplicates),
                "data_integrity_score": (total_count - invalid_count) / max(total_count, 1) * 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Content data validation completed: {total_count} total, {invalid_count} invalid")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to validate content data: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }