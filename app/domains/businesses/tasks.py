"""
Business domain Celery tasks.

Provides asynchronous task processing for business-related operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from celery import shared_task
from ...core.celery_config import celery_app
from ...core.database import get_database
from .service import BusinessService
from .repository import BusinessRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.domains.businesses.tasks.fetch_businesses_comprehensive")
def fetch_businesses_comprehensive(
    self,
    page_no: int = 1,
    num_of_rows: int = 50,
    business_field: Optional[str] = None,
    organization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive business data fetching task.
    
    Args:
        page_no: Page number to fetch
        num_of_rows: Number of rows per page
        business_field: Business field filter
        organization: Organization filter
        
    Returns:
        Dictionary with task results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = BusinessRepository(db.businesses)
        api_client = KStartupAPIClient()
        service = BusinessService(repository, api_client)
        
        # Perform data fetch
        start_time = datetime.utcnow()
        businesses = service.fetch_and_save_businesses(
            page_no=page_no,
            num_of_rows=num_of_rows,
            business_field=business_field,
            organization=organization
        )
        end_time = datetime.utcnow()
        
        # Prepare result
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "fetched_count": len(businesses),
            "page_no": page_no,
            "filters": {
                "business_field": business_field,
                "organization": organization
            },
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully fetched {len(businesses)} businesses")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to fetch businesses: {exc}")
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


@shared_task(bind=True, name="app.domains.businesses.tasks.fetch_businesses_incremental")
def fetch_businesses_incremental(self, max_pages: int = 5) -> Dict[str, Any]:
    """
    Incremental business data fetching task.
    
    Args:
        max_pages: Maximum number of pages to fetch
        
    Returns:
        Dictionary with task results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = BusinessRepository(db.businesses)
        api_client = KStartupAPIClient()
        service = BusinessService(repository, api_client)
        
        start_time = datetime.utcnow()
        total_fetched = 0
        
        # Fetch multiple pages
        for page in range(1, max_pages + 1):
            try:
                businesses = service.fetch_and_save_businesses(
                    page_no=page,
                    num_of_rows=20
                )
                total_fetched += len(businesses)
                
                # Break if no more data
                if len(businesses) == 0:
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
        
        logger.info(f"Incremental fetch completed: {total_fetched} businesses")
        return result
        
    except Exception as exc:
        logger.error(f"Failed incremental fetch: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.businesses.tasks.cleanup_inactive_businesses")
def cleanup_inactive_businesses(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up inactive businesses older than specified days.
    
    Args:
        days_old: Number of days to consider for cleanup
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = BusinessRepository(db.businesses)
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find and deactivate old businesses
        filter_criteria = {
            "is_active": True,
            "updated_at": {"$lt": cutoff_date}
        }
        
        # Update inactive businesses
        result = db.businesses.update_many(
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
        
        logger.info(f"Deactivated {result.modified_count} inactive businesses")
        return cleanup_result
        
    except Exception as exc:
        logger.error(f"Failed to cleanup businesses: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.businesses.tasks.generate_business_statistics")
def generate_business_statistics(self) -> Dict[str, Any]:
    """
    Generate comprehensive business statistics.
    
    Returns:
        Dictionary with statistics
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = BusinessRepository(db.businesses)
        service = BusinessService(repository)
        
        # Generate statistics
        stats = service.get_business_statistics()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Business statistics generated successfully")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to generate business statistics: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.businesses.tasks.validate_business_data")
def validate_business_data(self) -> Dict[str, Any]:
    """
    Validate business data integrity.
    
    Returns:
        Dictionary with validation results
    """
    try:
        # Initialize dependencies
        db = get_database()
        
        # Validation checks
        total_count = db.businesses.count_documents({})
        active_count = db.businesses.count_documents({"is_active": True})
        invalid_count = db.businesses.count_documents({
            "$or": [
                {"business_data": {"$exists": False}},
                {"business_data": None},
                {"business_data": {}}
            ]
        })
        
        # Check for duplicates (basic check on source_url)
        pipeline = [
            {"$group": {"_id": "$source_url", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(db.businesses.aggregate(pipeline))
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "validation_results": {
                "total_businesses": total_count,
                "active_businesses": active_count,
                "invalid_businesses": invalid_count,
                "duplicate_sources": len(duplicates),
                "data_integrity_score": (total_count - invalid_count) / max(total_count, 1) * 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Business data validation completed: {total_count} total, {invalid_count} invalid")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to validate business data: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }