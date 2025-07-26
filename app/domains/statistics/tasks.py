"""
Statistics domain Celery tasks.

Provides asynchronous task processing for statistics-related operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from celery import shared_task
from ...core.celery_config import celery_app
from ...core.database import get_database
from .service import StatisticsService
from .repository import StatisticsRepository
from ...shared.clients.kstartup_api_client import KStartupAPIClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.domains.statistics.tasks.fetch_statistics_comprehensive")
def fetch_statistics_comprehensive(
    self,
    page_no: int = 1,
    num_of_rows: int = 50,
    year: Optional[int] = None,
    month: Optional[int] = None
) -> Dict[str, Any]:
    """
    Comprehensive statistics data fetching task.
    
    Args:
        page_no: Page number to fetch
        num_of_rows: Number of rows per page
        year: Year filter
        month: Month filter
        
    Returns:
        Dictionary with task results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = StatisticsRepository(db.statistics)
        api_client = KStartupAPIClient()
        service = StatisticsService(repository, api_client)
        
        # Perform data fetch
        start_time = datetime.utcnow()
        statistics_list = service.fetch_and_save_statistics(
            page_no=page_no,
            num_of_rows=num_of_rows,
            year=year,
            month=month
        )
        end_time = datetime.utcnow()
        
        # Prepare result
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "fetched_count": len(statistics_list),
            "page_no": page_no,
            "filters": {
                "year": year,
                "month": month
            },
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully fetched {len(statistics_list)} statistics")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to fetch statistics: {exc}")
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


@shared_task(bind=True, name="app.domains.statistics.tasks.generate_monthly_reports")
def generate_monthly_reports(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate monthly statistical reports.
    
    Args:
        year: Year for the report (defaults to current year)
        month: Month for the report (defaults to current month)
        
    Returns:
        Dictionary with report generation results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = StatisticsRepository(db.statistics)
        service = StatisticsService(repository)
        
        # Default to current year/month if not provided
        now = datetime.utcnow()
        year = year or now.year
        month = month or now.month
        
        # Generate monthly report
        start_time = datetime.utcnow()
        report = service.generate_monthly_report(year, month)
        end_time = datetime.utcnow()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "report_year": year,
            "report_month": month,
            "report_data": report,
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated monthly report for {year}-{month:02d}")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to generate monthly report: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.statistics.tasks.generate_yearly_reports")
def generate_yearly_reports(self, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate yearly statistical reports.
    
    Args:
        year: Year for the report (defaults to current year)
        
    Returns:
        Dictionary with report generation results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = StatisticsRepository(db.statistics)
        service = StatisticsService(repository)
        
        # Default to current year if not provided
        year = year or datetime.utcnow().year
        
        # Generate yearly report
        start_time = datetime.utcnow()
        report = service.generate_yearly_report(year)
        end_time = datetime.utcnow()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "report_year": year,
            "report_data": report,
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated yearly report for {year}")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to generate yearly report: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.statistics.tasks.calculate_aggregated_metrics")
def calculate_aggregated_metrics(
    self,
    stat_type: Optional[str] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate aggregated statistical metrics.
    
    Args:
        stat_type: Statistics type filter
        year: Year filter
        
    Returns:
        Dictionary with calculated metrics
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = StatisticsRepository(db.statistics)
        service = StatisticsService(repository)
        
        # Calculate metrics
        start_time = datetime.utcnow()
        metrics = service.get_aggregated_metrics(stat_type, year)
        end_time = datetime.utcnow()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "metrics": metrics,
            "filters": {
                "stat_type": stat_type,
                "year": year
            },
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Calculated aggregated metrics for {stat_type or 'all'} statistics")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to calculate aggregated metrics: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.statistics.tasks.cleanup_old_statistics")
def cleanup_old_statistics(self, days_old: int = 365) -> Dict[str, Any]:
    """
    Clean up old statistics data.
    
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
        
        # Find and archive old statistics
        filter_criteria = {
            "is_active": True,
            "created_at": {"$lt": cutoff_date}
        }
        
        # Archive old statistics (mark as inactive instead of deleting)
        result = db.statistics.update_many(
            filter_criteria,
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        cleanup_result = {
            "task_id": self.request.id,
            "status": "completed",
            "archived_count": result.modified_count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Archived {result.modified_count} old statistics")
        return cleanup_result
        
    except Exception as exc:
        logger.error(f"Failed to cleanup statistics: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.statistics.tasks.validate_statistics_data")
def validate_statistics_data(self) -> Dict[str, Any]:
    """
    Validate statistics data integrity.
    
    Returns:
        Dictionary with validation results
    """
    try:
        # Initialize dependencies
        db = get_database()
        
        # Validation checks
        total_count = db.statistics.count_documents({})
        active_count = db.statistics.count_documents({"is_active": True})
        invalid_count = db.statistics.count_documents({
            "$or": [
                {"statistical_data": {"$exists": False}},
                {"statistical_data": None},
                {"statistical_data": {}}
            ]
        })
        
        # Check for data consistency
        current_year = datetime.utcnow().year
        current_year_count = db.statistics.count_documents({
            "statistical_data.year": current_year
        })
        
        # Check for missing required fields
        missing_fields_count = db.statistics.count_documents({
            "$or": [
                {"created_at": {"$exists": False}},
                {"updated_at": {"$exists": False}}
            ]
        })
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "validation_results": {
                "total_statistics": total_count,
                "active_statistics": active_count,
                "invalid_statistics": invalid_count,
                "current_year_statistics": current_year_count,
                "missing_fields_count": missing_fields_count,
                "data_integrity_score": (total_count - invalid_count - missing_fields_count) / max(total_count, 1) * 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Statistics validation completed: {total_count} total, {invalid_count} invalid")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to validate statistics data: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="app.domains.statistics.tasks.update_statistics_cache")
def update_statistics_cache(self) -> Dict[str, Any]:
    """
    Update cached statistics for improved performance.
    
    Returns:
        Dictionary with cache update results
    """
    try:
        # Initialize dependencies
        db = get_database()
        repository = StatisticsRepository(db.statistics)
        service = StatisticsService(repository)
        
        # Update various cached statistics
        start_time = datetime.utcnow()
        
        # Generate overview statistics
        overview = service.get_statistics_overview()
        
        # Calculate recent statistics
        recent_count = db.statistics.count_documents({
            "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}
        })
        
        end_time = datetime.utcnow()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "cached_data": {
                "overview": overview,
                "recent_count": recent_count
            },
            "execution_time": (end_time - start_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Statistics cache updated successfully")
        return result
        
    except Exception as exc:
        logger.error(f"Failed to update statistics cache: {exc}")
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }