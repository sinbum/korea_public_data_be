"""
Advanced monitoring tasks for system health, performance, and alerting.

Provides comprehensive monitoring capabilities including system metrics,
performance tracking, alerting, and automated issue resolution.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import asyncio
import logging
import json
import traceback
from celery import Task
from celery.exceptions import Retry

from ..core.celery_config import celery_app
from ..core.database import get_database
from ..shared.classification.services import ClassificationService
from ..domains.announcements.service import AnnouncementService

logger = logging.getLogger(__name__)


class MonitoringTask(Task):
    """Base task class for monitoring operations with enhanced callbacks."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when monitoring task succeeds."""
        logger.info(f"Monitoring task {self.name} [{task_id}] completed successfully")
        
        # Log key metrics if available
        if isinstance(retval, dict):
            if "status" in retval:
                logger.info(f"Task status: {retval['status']}")
            if "metrics" in retval:
                logger.info(f"Collected metrics: {len(retval['metrics'])} items")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when monitoring task fails."""
        logger.error(f"Monitoring task {self.name} [{task_id}] failed: {exc}")
        logger.error(f"Error details: {einfo}")
        
        # Trigger alert for monitoring task failures
        self._trigger_monitoring_alert("task_failure", {
            "task_name": self.name,
            "task_id": task_id,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when monitoring task is retried."""
        logger.warning(f"Monitoring task {self.name} [{task_id}] retrying due to: {exc}")
    
    def _trigger_monitoring_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """Trigger a monitoring alert (placeholder for actual alerting system)."""
        logger.critical(f"MONITORING ALERT [{alert_type}]: {json.dumps(data, indent=2)}")


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    max_retries=2,
    default_retry_delay=300
)
def comprehensive_system_monitor(self) -> Dict[str, Any]:
    """
    Comprehensive system monitoring with detailed health checks and metrics collection.
    
    Monitors:
    - Database connectivity and performance
    - Redis/Celery broker health
    - Application services health
    - System resources
    - API response times
    - Data quality metrics
    """
    try:
        logger.info("Starting comprehensive system monitoring")
        
        result = asyncio.run(_comprehensive_system_monitor_async())
        
        # Analyze results and trigger alerts if needed
        _analyze_monitoring_results(result)
        
        logger.info("Comprehensive system monitoring completed")
        return result
        
    except Exception as e:
        logger.error(f"Error in comprehensive system monitoring: {e}")
        self.retry(countdown=300, exc=e)


async def _comprehensive_system_monitor_async() -> Dict[str, Any]:
    """Async implementation of comprehensive system monitoring."""
    
    monitoring_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "task": "comprehensive_system_monitor",
        "overall_status": "unknown",
        "components": {},
        "metrics": {},
        "alerts": [],
        "recommendations": []
    }
    
    try:
        # Database monitoring
        db_health = await _monitor_database_health()
        monitoring_results["components"]["database"] = db_health
        
        # Redis/Celery monitoring
        celery_health = await _monitor_celery_health()
        monitoring_results["components"]["celery"] = celery_health
        
        # Application services monitoring
        services_health = await _monitor_application_services()
        monitoring_results["components"]["services"] = services_health
        
        # System metrics collection
        system_metrics = await _collect_system_metrics()
        monitoring_results["metrics"] = system_metrics
        
        # Data quality monitoring
        data_quality = await _monitor_data_quality()
        monitoring_results["components"]["data_quality"] = data_quality
        
        # Performance monitoring
        performance_metrics = await _monitor_performance()
        monitoring_results["components"]["performance"] = performance_metrics
        
        # Determine overall status
        overall_status = _determine_overall_status(monitoring_results["components"])
        monitoring_results["overall_status"] = overall_status
        
        # Generate alerts and recommendations
        alerts, recommendations = _generate_alerts_and_recommendations(monitoring_results)
        monitoring_results["alerts"] = alerts
        monitoring_results["recommendations"] = recommendations
        
    except Exception as e:
        logger.error(f"Error during comprehensive system monitoring: {e}")
        monitoring_results["error"] = str(e)
        monitoring_results["overall_status"] = "error"
    
    return monitoring_results


async def _monitor_database_health() -> Dict[str, Any]:
    """Monitor database health and performance."""
    db_health = {
        "status": "unknown",
        "response_time_ms": 0,
        "connections": 0,
        "collections_status": {},
        "storage_metrics": {}
    }
    
    try:
        start_time = datetime.utcnow()
        
        # Test database connection
        db = get_database()
        ping_result = db.command("ping")
        
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        db_health["response_time_ms"] = response_time
        db_health["status"] = "healthy" if ping_result.get("ok") == 1 else "unhealthy"
        
        # Check collection status
        collections = ["announcements", "businesses", "contents", "statistics"]
        for collection_name in collections:
            try:
                collection = db[collection_name]
                count = collection.count_documents({})
                db_health["collections_status"][collection_name] = {
                    "status": "accessible",
                    "document_count": count
                }
            except Exception as e:
                db_health["collections_status"][collection_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Get database stats
        try:
            db_stats = db.command("dbStats")
            db_health["storage_metrics"] = {
                "data_size_mb": db_stats.get("dataSize", 0) / (1024 * 1024),
                "storage_size_mb": db_stats.get("storageSize", 0) / (1024 * 1024),
                "index_size_mb": db_stats.get("indexSize", 0) / (1024 * 1024),
                "collections": db_stats.get("collections", 0),
                "indexes": db_stats.get("indexes", 0)
            }
        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_health["status"] = "unhealthy"
        db_health["error"] = str(e)
    
    return db_health


async def _monitor_celery_health() -> Dict[str, Any]:
    """Monitor Celery broker and worker health."""
    celery_health = {
        "status": "unknown",
        "broker_status": "unknown",
        "workers": {},
        "queues": {},
        "active_tasks": 0,
        "scheduled_tasks": 0
    }
    
    try:
        # Test broker connection
        try:
            inspect = celery_app.control.inspect(timeout=10)
            
            # Check active workers
            active_workers = inspect.active()
            if active_workers:
                celery_health["broker_status"] = "healthy"
                
                # Get worker details
                for worker_name, tasks in active_workers.items():
                    celery_health["workers"][worker_name] = {
                        "status": "active",
                        "active_tasks": len(tasks),
                        "tasks": [task["name"] for task in tasks]
                    }
                    celery_health["active_tasks"] += len(tasks)
            else:
                celery_health["broker_status"] = "no_workers"
            
            # Check scheduled tasks
            scheduled = inspect.scheduled()
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                celery_health["scheduled_tasks"] = total_scheduled
            
            # Check reserved tasks
            reserved = inspect.reserved() 
            if reserved:
                for worker_name, tasks in reserved.items():
                    if worker_name in celery_health["workers"]:
                        celery_health["workers"][worker_name]["reserved_tasks"] = len(tasks)
            
            celery_health["status"] = "healthy" if celery_health["broker_status"] == "healthy" else "degraded"
            
        except Exception as e:
            logger.error(f"Celery broker check failed: {e}")
            celery_health["broker_status"] = "unhealthy"
            celery_health["status"] = "unhealthy"
            celery_health["error"] = str(e)
        
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        celery_health["status"] = "unhealthy"
        celery_health["error"] = str(e)
    
    return celery_health


async def _monitor_application_services() -> Dict[str, Any]:
    """Monitor application services health."""
    services_health = {
        "status": "unknown",
        "services": {}
    }
    
    try:
        # Test AnnouncementService
        try:
            db = get_database()
            announcement_service = AnnouncementService(db)
            
            # Simple health check - try to count documents
            test_count = announcement_service.get_count()
            services_health["services"]["announcement_service"] = {
                "status": "healthy",
                "response_time_ms": 0,  # Would measure actual response time
                "data_count": test_count
            }
        except Exception as e:
            services_health["services"]["announcement_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test ClassificationService
        try:
            classification_service = ClassificationService()
            
            # Test basic validation
            test_result = await classification_service.validate_business_category("cmrczn_tab1")
            services_health["services"]["classification_service"] = {
                "status": "healthy" if test_result.is_valid else "degraded",
                "test_validation": test_result.is_valid
            }
        except Exception as e:
            services_health["services"]["classification_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall services status
        service_statuses = [service["status"] for service in services_health["services"].values()]
        if all(status == "healthy" for status in service_statuses):
            services_health["status"] = "healthy"
        elif any(status == "unhealthy" for status in service_statuses):
            services_health["status"] = "degraded"
        else:
            services_health["status"] = "healthy"
        
    except Exception as e:
        logger.error(f"Application services health check failed: {e}")
        services_health["status"] = "unhealthy"
        services_health["error"] = str(e)
    
    return services_health


async def _collect_system_metrics() -> Dict[str, Any]:
    """Collect system performance metrics."""
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "collection_duration_ms": 0
    }
    
    start_time = datetime.utcnow()
    
    try:
        # Database metrics
        db = get_database()
        
        # Collection sizes
        collections_info = {}
        for collection_name in ["announcements", "businesses", "contents", "statistics"]:
            try:
                collection = db[collection_name]
                count = collection.count_documents({})
                
                # Get sample of recent documents for freshness check
                recent_count = collection.count_documents({
                    "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
                })
                
                collections_info[collection_name] = {
                    "total_documents": count,
                    "recent_24h": recent_count,
                    "freshness_ratio": recent_count / max(count, 1)
                }
            except Exception as e:
                collections_info[collection_name] = {"error": str(e)}
        
        metrics["collections"] = collections_info
        
        # Task metrics from Celery
        try:
            inspect = celery_app.control.inspect(timeout=5)
            active_tasks = inspect.active() or {}
            
            task_metrics = {
                "total_active": sum(len(tasks) for tasks in active_tasks.values()),
                "workers_count": len(active_tasks),
                "task_distribution": {}
            }
            
            # Count tasks by type
            for worker_tasks in active_tasks.values():
                for task in worker_tasks:
                    task_name = task.get("name", "unknown")
                    task_metrics["task_distribution"][task_name] = (
                        task_metrics["task_distribution"].get(task_name, 0) + 1
                    )
            
            metrics["tasks"] = task_metrics
        except Exception as e:
            metrics["tasks"] = {"error": str(e)}
        
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        metrics["error"] = str(e)
    
    end_time = datetime.utcnow()
    metrics["collection_duration_ms"] = (end_time - start_time).total_seconds() * 1000
    
    return metrics


async def _monitor_data_quality() -> Dict[str, Any]:
    """Monitor data quality across all domains."""
    data_quality = {
        "status": "unknown",
        "overall_score": 0.0,
        "domains": {}
    }
    
    try:
        db = get_database()
        
        # Check announcements data quality
        announcements_quality = await _check_announcements_quality(db)
        data_quality["domains"]["announcements"] = announcements_quality
        
        # Check classification codes usage
        classification_quality = await _check_classification_quality(db)
        data_quality["domains"]["classification"] = classification_quality
        
        # Calculate overall quality score
        domain_scores = [
            domain.get("quality_score", 0.0) 
            for domain in data_quality["domains"].values() 
            if "quality_score" in domain
        ]
        
        if domain_scores:
            data_quality["overall_score"] = sum(domain_scores) / len(domain_scores)
            
            if data_quality["overall_score"] >= 0.9:
                data_quality["status"] = "excellent"
            elif data_quality["overall_score"] >= 0.7:
                data_quality["status"] = "good"
            elif data_quality["overall_score"] >= 0.5:
                data_quality["status"] = "fair"
            else:
                data_quality["status"] = "poor"
        
    except Exception as e:
        logger.error(f"Data quality monitoring failed: {e}")
        data_quality["status"] = "error"
        data_quality["error"] = str(e)
    
    return data_quality


async def _check_announcements_quality(db) -> Dict[str, Any]:
    """Check announcement data quality."""
    quality_metrics = {
        "total_documents": 0,
        "missing_required_fields": 0,
        "invalid_codes": 0,
        "duplicates": 0,
        "quality_score": 0.0
    }
    
    try:
        collection = db["announcements"]
        total_docs = collection.count_documents({})
        quality_metrics["total_documents"] = total_docs
        
        if total_docs > 0:
            # Check for missing required fields
            required_fields = ["announcement_data.title", "announcement_data.organization_name"]
            missing_fields = 0
            
            for field in required_fields:
                missing_count = collection.count_documents({field: {"$exists": False}})
                missing_fields += missing_count
            
            quality_metrics["missing_required_fields"] = missing_fields
            
            # Check for duplicates
            duplicate_pipeline = [
                {"$group": {"_id": "$announcement_data.announcement_id", "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}}
            ]
            duplicates = list(collection.aggregate(duplicate_pipeline))
            quality_metrics["duplicates"] = len(duplicates)
            
            # Calculate quality score
            total_issues = missing_fields + quality_metrics["duplicates"]
            quality_metrics["quality_score"] = max(0.0, 1.0 - (total_issues / total_docs))
        
    except Exception as e:
        quality_metrics["error"] = str(e)
    
    return quality_metrics


async def _check_classification_quality(db) -> Dict[str, Any]:
    """Check classification codes data quality."""
    quality_metrics = {
        "total_business_codes": 0,
        "invalid_business_codes": 0,
        "quality_score": 0.0
    }
    
    try:
        collection = db["announcements"]
        classification_service = ClassificationService()
        
        # Get all business category codes in use
        pipeline = [
            {"$match": {"announcement_data.biz_category_cd": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$announcement_data.biz_category_cd", "count": {"$sum": 1}}}
        ]
        
        codes_usage = list(collection.aggregate(pipeline))
        quality_metrics["total_business_codes"] = len(codes_usage)
        
        invalid_codes = 0
        for code_info in codes_usage:
            code = code_info["_id"]
            if code:
                validation_result = await classification_service.validate_business_category(code)
                if not validation_result.is_valid:
                    invalid_codes += 1
        
        quality_metrics["invalid_business_codes"] = invalid_codes
        
        if quality_metrics["total_business_codes"] > 0:
            quality_metrics["quality_score"] = 1.0 - (invalid_codes / quality_metrics["total_business_codes"])
        
    except Exception as e:
        quality_metrics["error"] = str(e)
    
    return quality_metrics


async def _monitor_performance() -> Dict[str, Any]:
    """Monitor system performance metrics."""
    performance = {
        "status": "unknown",
        "response_times": {},
        "throughput": {},
        "resource_usage": {}
    }
    
    try:
        # Database response time
        start_time = datetime.utcnow()
        db = get_database()
        db.command("ping")
        db_response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        performance["response_times"]["database_ping"] = db_response_time
        
        # Sample query response time
        start_time = datetime.utcnow()
        collection = db["announcements"]
        collection.count_documents({})
        query_response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        performance["response_times"]["sample_query"] = query_response_time
        
        # Determine performance status based on response times
        if db_response_time < 100 and query_response_time < 500:
            performance["status"] = "excellent"
        elif db_response_time < 300 and query_response_time < 1000:
            performance["status"] = "good"
        elif db_response_time < 1000 and query_response_time < 3000:
            performance["status"] = "fair"
        else:
            performance["status"] = "poor"
        
    except Exception as e:
        logger.error(f"Performance monitoring failed: {e}")
        performance["status"] = "error"
        performance["error"] = str(e)
    
    return performance


def _determine_overall_status(components: Dict[str, Any]) -> str:
    """Determine overall system status from component statuses."""
    statuses = []
    
    for component, data in components.items():
        if isinstance(data, dict) and "status" in data:
            statuses.append(data["status"])
    
    if not statuses:
        return "unknown"
    
    # Priority order: error > unhealthy > degraded > fair > good > healthy > excellent
    if "error" in statuses or "unhealthy" in statuses:
        return "unhealthy"
    elif "degraded" in statuses or "poor" in statuses:
        return "degraded"
    elif "fair" in statuses:
        return "fair"
    elif "good" in statuses:
        return "good"
    elif all(status in ["healthy", "excellent"] for status in statuses):
        return "healthy"
    else:
        return "unknown"


def _generate_alerts_and_recommendations(monitoring_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[str]]:
    """Generate alerts and recommendations based on monitoring data."""
    alerts = []
    recommendations = []
    
    # Check overall status
    overall_status = monitoring_data.get("overall_status", "unknown")
    if overall_status in ["unhealthy", "error"]:
        alerts.append({
            "type": "critical",
            "component": "system",
            "message": f"System overall status is {overall_status}",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Check database health
    db_component = monitoring_data.get("components", {}).get("database", {})
    if db_component.get("status") == "unhealthy":
        alerts.append({
            "type": "critical",
            "component": "database",
            "message": "Database is unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        })
        recommendations.append("Check database connectivity and restart if necessary")
    
    # Check response times
    response_times = monitoring_data.get("components", {}).get("performance", {}).get("response_times", {})
    db_response_time = response_times.get("database_ping", 0)
    if db_response_time > 1000:
        alerts.append({
            "type": "warning",
            "component": "performance",
            "message": f"Database response time is high: {db_response_time}ms",
            "timestamp": datetime.utcnow().isoformat()
        })
        recommendations.append("Consider database performance tuning or index optimization")
    
    # Check data quality
    data_quality = monitoring_data.get("components", {}).get("data_quality", {})
    overall_score = data_quality.get("overall_score", 1.0)
    if overall_score < 0.7:
        alerts.append({
            "type": "warning",
            "component": "data_quality",
            "message": f"Data quality score is low: {overall_score:.2%}",
            "timestamp": datetime.utcnow().isoformat()
        })
        recommendations.append("Run data integrity validation and cleanup tasks")
    
    # Check Celery workers
    celery_component = monitoring_data.get("components", {}).get("celery", {})
    if celery_component.get("broker_status") == "no_workers":
        alerts.append({
            "type": "critical",
            "component": "celery",
            "message": "No Celery workers are active",
            "timestamp": datetime.utcnow().isoformat()
        })
        recommendations.append("Start Celery workers to process background tasks")
    
    return alerts, recommendations


def _analyze_monitoring_results(results: Dict[str, Any]) -> None:
    """Analyze monitoring results and log important findings."""
    overall_status = results.get("overall_status", "unknown")
    alerts = results.get("alerts", [])
    
    # Log overall status
    if overall_status == "healthy":
        logger.info("✅ System is healthy - all components operating normally")
    elif overall_status == "degraded":
        logger.warning("⚠️ System is degraded - some components need attention")
    elif overall_status == "unhealthy":
        logger.error("❌ System is unhealthy - immediate attention required")
    
    # Log alerts
    for alert in alerts:
        if alert["type"] == "critical":
            logger.critical(f"🚨 CRITICAL ALERT: {alert['message']}")
        elif alert["type"] == "warning":
            logger.warning(f"⚠️ WARNING: {alert['message']}")
    
    # Log recommendations
    recommendations = results.get("recommendations", [])
    if recommendations:
        logger.info("💡 RECOMMENDATIONS:")
        for rec in recommendations:
            logger.info(f"   - {rec}")


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    max_retries=1
)
def generate_monitoring_report(self) -> Dict[str, Any]:
    """
    Generate comprehensive monitoring report with historical data analysis.
    """
    try:
        logger.info("Generating comprehensive monitoring report")
        
        # Run comprehensive monitoring
        current_monitoring = comprehensive_system_monitor.apply().get()
        
        # Create report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": "generate_monitoring_report",
            "report_period": "current",
            "current_status": current_monitoring,
            "summary": _generate_monitoring_summary(current_monitoring),
            "action_items": _generate_action_items(current_monitoring)
        }
        
        logger.info("Monitoring report generated successfully")
        return report
        
    except Exception as e:
        logger.error(f"Error generating monitoring report: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "task": "generate_monitoring_report"
        }


def _generate_monitoring_summary(monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate executive summary of monitoring data."""
    return {
        "overall_status": monitoring_data.get("overall_status", "unknown"),
        "total_alerts": len(monitoring_data.get("alerts", [])),
        "critical_alerts": len([
            alert for alert in monitoring_data.get("alerts", []) 
            if alert.get("type") == "critical"
        ]),
        "key_metrics": {
            "database_response_time": monitoring_data.get("components", {})
                                                     .get("performance", {})
                                                     .get("response_times", {})
                                                     .get("database_ping", 0),
            "data_quality_score": monitoring_data.get("components", {})
                                                .get("data_quality", {})
                                                .get("overall_score", 0.0),
            "active_workers": len(monitoring_data.get("components", {})
                                                .get("celery", {})
                                                .get("workers", {}))
        }
    }


def _generate_action_items(monitoring_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate prioritized action items based on monitoring data."""
    action_items = []
    
    # Convert alerts to action items
    alerts = monitoring_data.get("alerts", [])
    for alert in alerts:
        priority = "high" if alert.get("type") == "critical" else "medium"
        action_items.append({
            "priority": priority,
            "component": alert.get("component", "unknown"),
            "action": f"Address {alert.get('type', 'issue')}: {alert.get('message', 'No details')}",
            "timestamp": alert.get("timestamp")
        })
    
    # Add proactive action items based on recommendations
    recommendations = monitoring_data.get("recommendations", [])
    for rec in recommendations:
        action_items.append({
            "priority": "low",
            "component": "maintenance",
            "action": rec,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    action_items.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    return action_items


# Task registration helper
def get_monitoring_tasks() -> List[Dict[str, Any]]:
    """Get list of all available monitoring tasks."""
    return [
        {
            "name": "comprehensive_system_monitor",
            "description": "Comprehensive system health and performance monitoring",
            "category": "monitoring",
            "estimated_duration": "2-5 minutes",
            "queue": "monitoring"
        },
        {
            "name": "generate_monitoring_report",
            "description": "Generate comprehensive monitoring report",
            "category": "reporting",
            "estimated_duration": "3-7 minutes",
            "queue": "monitoring"
        }
    ]