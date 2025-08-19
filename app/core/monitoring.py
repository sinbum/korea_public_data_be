"""
MongoDB 연결 풀 및 성능 모니터링 모듈
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import deque
import threading

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """MongoDB 성능 모니터링 클래스"""
    
    def __init__(self, window_size: int = 100):
        """
        Args:
            window_size: 성능 메트릭을 추적할 윈도우 크기
        """
        self.window_size = window_size
        self.query_times = deque(maxlen=window_size)
        self.connection_wait_times = deque(maxlen=window_size)
        self.slow_queries = deque(maxlen=20)  # 최근 20개의 느린 쿼리
        self.lock = threading.Lock()
        
        # 임계값 설정
        self.slow_query_threshold = 50  # 50ms 이상을 느린 쿼리로 정의
        self.connection_wait_threshold = 10  # 10ms 이상을 느린 연결로 정의
    
    def record_query(self, query_time: float, query_info: Dict[str, Any] = None):
        """쿼리 실행 시간 기록"""
        with self.lock:
            self.query_times.append(query_time)
            
            # 느린 쿼리 기록
            if query_time > self.slow_query_threshold:
                self.slow_queries.append({
                    "time": query_time,
                    "info": query_info,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def record_connection_wait(self, wait_time: float):
        """연결 대기 시간 기록"""
        with self.lock:
            self.connection_wait_times.append(wait_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 성능 통계 반환"""
        with self.lock:
            query_stats = self._calculate_stats(self.query_times)
            connection_stats = self._calculate_stats(self.connection_wait_times)
            
            return {
                "query_performance": {
                    "count": len(self.query_times),
                    "avg_ms": query_stats["avg"],
                    "min_ms": query_stats["min"],
                    "max_ms": query_stats["max"],
                    "p50_ms": query_stats["p50"],
                    "p95_ms": query_stats["p95"],
                    "p99_ms": query_stats["p99"]
                },
                "connection_performance": {
                    "count": len(self.connection_wait_times),
                    "avg_wait_ms": connection_stats["avg"],
                    "min_wait_ms": connection_stats["min"],
                    "max_wait_ms": connection_stats["max"],
                    "p95_wait_ms": connection_stats["p95"]
                },
                "slow_queries": list(self.slow_queries)[-10:],  # 최근 10개
                "thresholds": {
                    "slow_query_ms": self.slow_query_threshold,
                    "connection_wait_ms": self.connection_wait_threshold
                }
            }
    
    def _calculate_stats(self, data: deque) -> Dict[str, float]:
        """통계 계산"""
        if not data:
            return {
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            }
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        return {
            "avg": sum(sorted_data) / n,
            "min": sorted_data[0],
            "max": sorted_data[-1],
            "p50": sorted_data[int(n * 0.5)],
            "p95": sorted_data[int(n * 0.95)] if n > 20 else sorted_data[-1],
            "p99": sorted_data[int(n * 0.99)] if n > 100 else sorted_data[-1]
        }
    
    def check_health(self) -> Dict[str, Any]:
        """시스템 건강 상태 체크"""
        stats = self.get_stats()
        
        health_status = "healthy"
        issues = []
        
        # 쿼리 성능 체크
        if stats["query_performance"]["avg_ms"] > 30:
            health_status = "degraded"
            issues.append(f"평균 쿼리 시간이 높음: {stats['query_performance']['avg_ms']:.1f}ms")
        
        if stats["query_performance"]["p95_ms"] > 100:
            health_status = "degraded"
            issues.append(f"P95 쿼리 시간이 높음: {stats['query_performance']['p95_ms']:.1f}ms")
        
        # 연결 성능 체크
        if stats["connection_performance"]["avg_wait_ms"] > 5:
            health_status = "degraded"
            issues.append(f"평균 연결 대기 시간이 높음: {stats['connection_performance']['avg_wait_ms']:.1f}ms")
        
        # 느린 쿼리 체크
        if len(self.slow_queries) > 10:
            health_status = "warning"
            issues.append(f"최근 느린 쿼리가 많음: {len(self.slow_queries)}개")
        
        return {
            "status": health_status,
            "issues": issues,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }


class ConnectionPoolMonitor:
    """MongoDB 연결 풀 모니터"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.performance_monitor = PerformanceMonitor()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """연결 풀 통계 반환"""
        try:
            if self.db_manager.sync_client:
                # PyMongo 클라이언트 통계
                client_options = self.db_manager.sync_client.options
                pool_options = client_options.pool_options
                
                stats = {
                    "sync_pool": {
                        "max_pool_size": pool_options.max_pool_size,
                        "min_pool_size": pool_options.min_pool_size,
                        "max_idle_time_ms": pool_options.max_idle_time_ms,
                        "wait_queue_timeout_ms": pool_options.wait_queue_timeout_ms
                    }
                }
                
                # 서버 상태 확인
                if self.db_manager.database:
                    server_status = self.db_manager.database.command("serverStatus")
                    connections = server_status.get("connections", {})
                    
                    stats["server_connections"] = {
                        "current": connections.get("current", 0),
                        "available": connections.get("available", 0),
                        "total_created": connections.get("totalCreated", 0)
                    }
                
                return stats
            
            return {"error": "No active database connection"}
            
        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {"error": str(e)}
    
    def optimize_pool_size(self, current_load: int) -> Dict[str, int]:
        """부하에 따른 연결 풀 크기 최적화 제안"""
        
        # 기본 권장 설정
        recommendations = {
            "min_pool_size": 10,
            "max_pool_size": 100
        }
        
        if current_load < 50:
            # 낮은 부하
            recommendations = {
                "min_pool_size": 5,
                "max_pool_size": 50
            }
        elif current_load < 200:
            # 중간 부하
            recommendations = {
                "min_pool_size": 10,
                "max_pool_size": 100
            }
        else:
            # 높은 부하
            recommendations = {
                "min_pool_size": 20,
                "max_pool_size": 200
            }
        
        return recommendations
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """종합 모니터링 리포트"""
        pool_stats = self.get_pool_stats()
        performance_stats = self.performance_monitor.get_stats()
        health = self.performance_monitor.check_health()
        
        # 현재 연결 수 기반 권장 사항
        current_connections = pool_stats.get("server_connections", {}).get("current", 0)
        recommendations = self.optimize_pool_size(current_connections)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pool_configuration": pool_stats,
            "performance_metrics": performance_stats,
            "health_check": health,
            "recommendations": recommendations,
            "alerts": self._generate_alerts(health, performance_stats)
        }
    
    def _generate_alerts(self, health: Dict, stats: Dict) -> List[str]:
        """경고 생성"""
        alerts = []
        
        if health["status"] != "healthy":
            alerts.extend(health["issues"])
        
        # 추가 경고 조건
        if stats["query_performance"]["max_ms"] > 200:
            alerts.append(f"매우 느린 쿼리 감지: {stats['query_performance']['max_ms']:.1f}ms")
        
        if stats["connection_performance"]["max_wait_ms"] > 50:
            alerts.append(f"연결 대기 시간 초과: {stats['connection_performance']['max_wait_ms']:.1f}ms")
        
        return alerts


# 전역 모니터 인스턴스
_monitor = None

def get_monitor() -> ConnectionPoolMonitor:
    """전역 모니터 인스턴스 반환"""
    global _monitor
    if _monitor is None:
        from .database import db_manager
        _monitor = ConnectionPoolMonitor(db_manager)
    return _monitor

def record_query_performance(query_time: float, query_info: Dict = None):
    """쿼리 성능 기록 헬퍼 함수"""
    monitor = get_monitor()
    monitor.performance_monitor.record_query(query_time, query_info)

def record_connection_wait(wait_time: float):
    """연결 대기 시간 기록 헬퍼 함수"""
    monitor = get_monitor()
    monitor.performance_monitor.record_connection_wait(wait_time)