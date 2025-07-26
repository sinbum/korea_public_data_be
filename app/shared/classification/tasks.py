"""
Classification system tasks for monitoring and maintaining classification codes.

Provides background tasks for validation, cleanup, and optimization
of classification code usage across the system.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from celery import Task

from ...core.celery_config import celery_app
from ...core.database import get_database
from .services import ClassificationService

logger = logging.getLogger(__name__)


class ClassificationTask(Task):
    """Base task class for classification operations."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when classification task succeeds."""
        logger.info(f"Classification task {self.name} [{task_id}] completed successfully")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when classification task fails."""
        logger.error(f"Classification task {self.name} [{task_id}] failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when classification task is retried."""
        logger.warning(f"Classification task {self.name} [{task_id}] retrying due to: {exc}")


@celery_app.task(
    bind=True,
    base=ClassificationTask,
    max_retries=2,
    default_retry_delay=600
)
def validate_classification_usage(self) -> Dict[str, Any]:
    """
    Validate classification code usage across all domains.
    
    Checks all stored data for invalid classification codes and
    provides recommendations for data cleanup.
    """
    try:
        logger.info("Starting classification usage validation")
        
        result = asyncio.run(_validate_classification_usage_async())
        
        logger.info(f"Classification validation completed: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"Error in classification usage validation: {e}")
        self.retry(countdown=600, exc=e)


async def _validate_classification_usage_async() -> Dict[str, Any]:
    """Async implementation of classification usage validation."""
    
    validation_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": "validate_classification_usage",
        "domains": {},
        "overall_status": "healthy",
        "total_invalid_codes": 0,
        "recommendations": []
    }
    
    try:
        db = get_database()
        classification_service = ClassificationService()
        
        # Check announcements collection
        announcements_results = await _validate_announcements_codes(db, classification_service)
        validation_results["domains"]["announcements"] = announcements_results
        
        # Check businesses collection (when implemented)
        businesses_results = await _validate_businesses_codes(db, classification_service)
        validation_results["domains"]["businesses"] = businesses_results
        
        # Check contents collection (when implemented)
        contents_results = await _validate_contents_codes(db, classification_service)
        validation_results["domains"]["contents"] = contents_results
        
        # Calculate totals
        total_invalid = sum(
            domain.get("invalid_codes", 0) 
            for domain in validation_results["domains"].values()
        )
        validation_results["total_invalid_codes"] = total_invalid
        
        # Determine overall status
        if total_invalid == 0:
            validation_results["overall_status"] = "healthy"
        elif total_invalid < 10:
            validation_results["overall_status"] = "minor_issues"
        else:
            validation_results["overall_status"] = "needs_attention"
        
        # Generate recommendations
        validation_results["recommendations"] = _generate_cleanup_recommendations(
            validation_results["domains"]
        )
        
        validation_results["summary"] = (
            f"Validated classification usage across {len(validation_results['domains'])} domains, "
            f"found {total_invalid} invalid codes"
        )
        
    except Exception as e:
        logger.error(f"Error during classification usage validation: {e}")
        validation_results["error"] = str(e)
        validation_results["overall_status"] = "error"
    
    return validation_results


async def _validate_announcements_codes(db, classification_service: ClassificationService) -> Dict[str, Any]:
    """Validate classification codes in announcements collection."""
    
    results = {
        "collection": "announcements",
        "total_documents": 0,
        "documents_with_codes": 0,
        "invalid_codes": 0,
        "invalid_code_details": []
    }
    
    try:
        collection = db["announcements"]
        results["total_documents"] = collection.count_documents({})
        
        # Find all documents with business category codes
        pipeline = [
            {"$match": {"announcement_data.biz_category_cd": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": "$announcement_data.biz_category_cd",
                "count": {"$sum": 1},
                "sample_ids": {"$push": "$_id"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        code_usage = list(collection.aggregate(pipeline))
        results["documents_with_codes"] = sum(item["count"] for item in code_usage)
        
        # Validate each unique code
        for code_info in code_usage:
            code = code_info["_id"]
            if code:
                validation_result = await classification_service.validate_business_category(code)
                if not validation_result.is_valid:
                    results["invalid_codes"] += code_info["count"]
                    results["invalid_code_details"].append({
                        "code": code,
                        "usage_count": code_info["count"],
                        "errors": validation_result.errors,
                        "suggestions": validation_result.suggestions
                    })
        
    except Exception as e:
        logger.error(f"Error validating announcements codes: {e}")
        results["error"] = str(e)
    
    return results


async def _validate_businesses_codes(db, classification_service: ClassificationService) -> Dict[str, Any]:
    """Validate classification codes in businesses collection (placeholder)."""
    
    results = {
        "collection": "businesses",
        "total_documents": 0,
        "documents_with_codes": 0,
        "invalid_codes": 0,
        "status": "not_implemented"
    }
    
    try:
        collection = db["businesses"]
        results["total_documents"] = collection.count_documents({})
        # Would implement actual validation when businesses service is ready
        
    except Exception as e:
        logger.error(f"Error validating businesses codes: {e}")
        results["error"] = str(e)
    
    return results


async def _validate_contents_codes(db, classification_service: ClassificationService) -> Dict[str, Any]:
    """Validate classification codes in contents collection (placeholder)."""
    
    results = {
        "collection": "contents",
        "total_documents": 0,
        "documents_with_codes": 0,
        "invalid_codes": 0,
        "status": "not_implemented"
    }
    
    try:
        collection = db["contents"]
        results["total_documents"] = collection.count_documents({})
        # Would implement actual validation when contents service is ready
        
    except Exception as e:
        logger.error(f"Error validating contents codes: {e}")
        results["error"] = str(e)
    
    return results


def _generate_cleanup_recommendations(domains: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on validation results."""
    recommendations = []
    
    for domain_name, domain_data in domains.items():
        invalid_count = domain_data.get("invalid_codes", 0)
        
        if invalid_count > 0:
            recommendations.append(
                f"Clean up {invalid_count} invalid classification codes in {domain_name} collection"
            )
            
            # Add specific recommendations for invalid codes
            invalid_details = domain_data.get("invalid_code_details", [])
            high_usage_invalid = [
                detail for detail in invalid_details 
                if detail.get("usage_count", 0) > 10
            ]
            
            if high_usage_invalid:
                recommendations.append(
                    f"Priority cleanup needed for high-usage invalid codes in {domain_name}: "
                    f"{[detail['code'] for detail in high_usage_invalid]}"
                )
    
    if not recommendations:
        recommendations.append("All classification codes are valid - no cleanup needed")
    
    return recommendations


@celery_app.task(
    bind=True,
    base=ClassificationTask,
    max_retries=1
)
def generate_classification_statistics(self) -> Dict[str, Any]:
    """
    Generate comprehensive statistics about classification code usage.
    
    Provides insights into code usage patterns, popular categories,
    and system-wide classification health.
    """
    try:
        logger.info("Generating classification statistics")
        
        result = asyncio.run(_generate_classification_statistics_async())
        
        logger.info("Classification statistics generation completed")
        return result
        
    except Exception as e:
        logger.error(f"Error generating classification statistics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "task": "generate_classification_statistics"
        }


async def _generate_classification_statistics_async() -> Dict[str, Any]:
    """Async implementation of classification statistics generation."""
    
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": "generate_classification_statistics",
        "business_categories": {},
        "content_categories": {},
        "usage_patterns": {},
        "health_metrics": {}
    }
    
    try:
        db = get_database()
        classification_service = ClassificationService()
        
        # Business category statistics
        business_stats = await _collect_business_category_stats(db, classification_service)
        stats["business_categories"] = business_stats
        
        # Content category statistics
        content_stats = await _collect_content_category_stats(db, classification_service)
        stats["content_categories"] = content_stats
        
        # Usage patterns
        usage_patterns = await _analyze_usage_patterns(db)
        stats["usage_patterns"] = usage_patterns
        
        # Health metrics
        health_metrics = _calculate_health_metrics(business_stats, content_stats)
        stats["health_metrics"] = health_metrics
        
    except Exception as e:
        logger.error(f"Error during classification statistics generation: {e}")
        stats["error"] = str(e)
    
    return stats


async def _collect_business_category_stats(db, classification_service: ClassificationService) -> Dict[str, Any]:
    """Collect statistics for business category usage."""
    
    stats = {
        "total_unique_codes": 0,
        "total_usage_count": 0,
        "most_popular": [],
        "least_popular": [],
        "valid_codes": 0,
        "invalid_codes": 0
    }
    
    try:
        collection = db["announcements"]
        
        # Get business category usage
        pipeline = [
            {"$match": {"announcement_data.biz_category_cd": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": "$announcement_data.biz_category_cd",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        usage_data = list(collection.aggregate(pipeline))
        stats["total_unique_codes"] = len(usage_data)
        stats["total_usage_count"] = sum(item["count"] for item in usage_data)
        
        # Validate codes and categorize
        valid_codes = []
        invalid_codes = []
        
        for item in usage_data:
            code = item["_id"]
            if code:
                validation_result = await classification_service.validate_business_category(code)
                if validation_result.is_valid:
                    valid_codes.append({"code": code, "count": item["count"]})
                else:
                    invalid_codes.append({"code": code, "count": item["count"]})
        
        stats["valid_codes"] = len(valid_codes)
        stats["invalid_codes"] = len(invalid_codes)
        
        # Most and least popular (valid codes only)
        stats["most_popular"] = valid_codes[:5]  # Top 5
        stats["least_popular"] = valid_codes[-5:] if len(valid_codes) > 5 else []
        
    except Exception as e:
        logger.error(f"Error collecting business category stats: {e}")
        stats["error"] = str(e)
    
    return stats


async def _collect_content_category_stats(db, classification_service: ClassificationService) -> Dict[str, Any]:
    """Collect statistics for content category usage."""
    
    stats = {
        "total_unique_codes": 0,
        "total_usage_count": 0,
        "distribution": {},
        "status": "not_implemented"
    }
    
    try:
        # This would be implemented when content classification is used
        # For now, return placeholder data
        all_content_categories = await classification_service.get_all_content_categories()
        stats["total_unique_codes"] = len(all_content_categories)
        
    except Exception as e:
        logger.error(f"Error collecting content category stats: {e}")
        stats["error"] = str(e)
    
    return stats


async def _analyze_usage_patterns(db) -> Dict[str, Any]:
    """Analyze classification code usage patterns over time."""
    
    patterns = {
        "recent_activity": {},
        "trending_codes": [],
        "seasonal_patterns": {},
        "status": "basic_analysis"
    }
    
    try:
        collection = db["announcements"]
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_pipeline = [
            {"$match": {
                "created_at": {"$gte": thirty_days_ago},
                "announcement_data.biz_category_cd": {"$exists": True, "$ne": None}
            }},
            {"$group": {
                "_id": "$announcement_data.biz_category_cd",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        recent_activity = list(collection.aggregate(recent_pipeline))
        patterns["recent_activity"] = {
            "period": "last_30_days",
            "top_codes": recent_activity
        }
        
    except Exception as e:
        logger.error(f"Error analyzing usage patterns: {e}")
        patterns["error"] = str(e)
    
    return patterns


def _calculate_health_metrics(business_stats: Dict[str, Any], content_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall health metrics for classification system."""
    
    total_business_codes = business_stats.get("total_unique_codes", 0)
    valid_business_codes = business_stats.get("valid_codes", 0)
    
    health_score = 1.0
    if total_business_codes > 0:
        health_score = valid_business_codes / total_business_codes
    
    return {
        "overall_health_score": health_score,
        "health_status": "excellent" if health_score >= 0.95 else 
                        "good" if health_score >= 0.9 else
                        "fair" if health_score >= 0.8 else "poor",
        "total_codes_tracked": total_business_codes,
        "code_validity_rate": health_score,
        "recommendations": [
            "Classification system is healthy" if health_score >= 0.95 else
            "Consider cleaning up invalid classification codes"
        ]
    }


# Task registration helper
def get_classification_tasks() -> List[Dict[str, Any]]:
    """Get list of all available classification tasks."""
    return [
        {
            "name": "validate_classification_usage",
            "description": "Validate classification code usage across all domains",
            "category": "validation",
            "estimated_duration": "5-10 minutes",
            "queue": "classification"
        },
        {
            "name": "generate_classification_statistics",
            "description": "Generate comprehensive classification usage statistics",
            "category": "analytics",
            "estimated_duration": "3-5 minutes",
            "queue": "classification"
        }
    ]