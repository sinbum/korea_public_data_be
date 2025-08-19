"""
Enhanced MongoDB connection management with async support and connection pooling.

Provides optimized database connections with proper connection pooling,
async support, and health monitoring for improved performance.
"""

import asyncio
from typing import Optional, Any, Dict
import logging
import time
from contextlib import asynccontextmanager

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from .config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Enhanced database manager with connection pooling and async support"""
    
    def __init__(self):
        self.sync_client: Optional[pymongo.MongoClient] = None
        self.async_client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.async_database = None
        self._connection_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
    
    def _get_sync_client_options(self) -> Dict[str, Any]:
        """Get optimized connection options for sync client"""
        return {
            # Connection pooling - 더 높은 값으로 증가
            "maxPoolSize": 100,  # 50에서 100으로 증가
            "minPoolSize": 10,   # 5에서 10으로 증가
            "maxIdleTimeMS": 900000,  # 15 minutes로 증가
            "waitQueueTimeoutMS": 3000,  # 3 seconds로 감소
            
            # Timeout configurations - 더 빠른 응답을 위해 조정
            "connectTimeoutMS": 5000,  # 5 seconds로 감소
            "socketTimeoutMS": 15000,   # 15 seconds로 감소
            "serverSelectionTimeoutMS": 5000,  # 5 seconds로 감소
            
            # Reliability options
            "retryWrites": True,
            "retryReads": True,
            "compressors": ["zstd", "zlib"],
            
            # Read preferences
            "readPreference": "primaryPreferred",
            "maxStalenessSeconds": 120,
        }
    
    def _get_async_client_options(self) -> Dict[str, Any]:
        """Get optimized connection options for async client"""
        return {
            # Connection pooling (async) - 더 공격적인 풀링
            "maxPoolSize": 150,  # 100에서 150으로 증가
            "minPoolSize": 20,   # 10에서 20으로 증가
            "maxIdleTimeMS": 900000,  # 15 minutes로 증가
            "waitQueueTimeoutMS": 5000,  # 5 seconds로 감소
            
            # Timeout configurations - 더 빠른 응답
            "connectTimeoutMS": 5000,  # 5 seconds로 감소
            "socketTimeoutMS": 20000,   # 20 seconds로 감소
            "serverSelectionTimeoutMS": 5000,  # 5 seconds로 감소
            
            # Reliability options
            "retryWrites": True,
            "retryReads": True,
            "compressors": ["zstd", "zlib"],
            
            # Read preferences
            "readPreference": "primaryPreferred",
            "maxStalenessSeconds": 120,
        }
    
    def connect_sync(self) -> None:
        """Create synchronous MongoDB connection with optimized settings"""
        try:
            options = self._get_sync_client_options()
            self.sync_client = pymongo.MongoClient(settings.mongodb_url, **options)
            self.database = self.sync_client[settings.database_name]
            
            # Health check
            self.sync_client.admin.command("ping", maxTimeMS=5000)
            self._connection_healthy = True
            self._last_health_check = time.time()
            
            logger.info("MongoDB 동기 연결 성공 (connection pooling 활성화)")
            
        except Exception as e:
            logger.error(f"MongoDB 동기 연결 실패: {e}")
            self._connection_healthy = False
            raise
    
    async def connect_async(self) -> None:
        """Create asynchronous MongoDB connection with optimized settings"""
        try:
            options = self._get_async_client_options()
            self.async_client = AsyncIOMotorClient(settings.mongodb_url, **options)
            self.async_database = self.async_client[settings.database_name]
            
            # Health check
            await self.async_client.admin.command("ping", maxTimeMS=5000)
            self._connection_healthy = True
            self._last_health_check = time.time()
            
            logger.info("MongoDB 비동기 연결 성공 (connection pooling 활성화)")
            
        except Exception as e:
            logger.error(f"MongoDB 비동기 연결 실패: {e}")
            self._connection_healthy = False
            raise
    
    def close_sync_connection(self) -> None:
        """Close synchronous MongoDB connection"""
        if self.sync_client:
            self.sync_client.close()
            self.sync_client = None
            self.database = None
            logger.info("MongoDB 동기 연결 종료")
    
    async def close_async_connection(self) -> None:
        """Close asynchronous MongoDB connection"""
        if self.async_client:
            self.async_client.close()
            self.async_client = None
            self.async_database = None
            logger.info("MongoDB 비동기 연결 종료")
    
    def get_database(self):
        """Get synchronous database instance"""
        if self.database is None:
            self.connect_sync()
        return self.database
    
    async def get_async_database(self):
        """Get asynchronous database instance"""
        if self.async_database is None:
            await self.connect_async()
        return self.async_database
    
    def is_healthy(self) -> bool:
        """Check if database connection is healthy"""
        current_time = time.time()
        
        # Return cached health status if within interval
        if (current_time - self._last_health_check) < self._health_check_interval:
            return self._connection_healthy
        
        # Perform health check
        try:
            if self.sync_client:
                self.sync_client.admin.command("ping", maxTimeMS=2000)
            elif self.async_client:
                # Cannot perform async operation in sync method
                # Rely on cached status for async connections
                pass
            
            self._connection_healthy = True
            self._last_health_check = current_time
            return True
            
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self._connection_healthy = False
            self._last_health_check = current_time
            return False
    
    async def async_is_healthy(self) -> bool:
        """Async version of health check"""
        current_time = time.time()
        
        # Return cached health status if within interval
        if (current_time - self._last_health_check) < self._health_check_interval:
            return self._connection_healthy
        
        # Perform async health check
        try:
            if self.async_client:
                await self.async_client.admin.command("ping", maxTimeMS=2000)
            elif self.sync_client:
                self.sync_client.admin.command("ping", maxTimeMS=2000)
            
            self._connection_healthy = True
            self._last_health_check = current_time
            return True
            
        except Exception as e:
            logger.warning(f"Database async health check failed: {e}")
            self._connection_healthy = False
            self._last_health_check = current_time
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = {
            "sync_connected": self.sync_client is not None,
            "async_connected": self.async_client is not None,
            "healthy": self._connection_healthy,
            "last_health_check": self._last_health_check
        }
        
        # Add sync client stats if available
        if self.sync_client:
            try:
                server_info = self.sync_client.server_info()
                stats.update({
                    "server_version": server_info.get("version"),
                    "server_uptime": server_info.get("uptime"),
                    "sync_pool_size": len(self.sync_client.nodes)
                })
            except Exception:
                pass
        
        return stats


# Global database manager instance
db_manager = DatabaseManager()

# Legacy compatibility functions
def connect_to_mongo():
    """Legacy function - creates sync connection"""
    return db_manager.connect_sync()

def close_mongo_connection():
    """Legacy function - closes sync connection"""
    return db_manager.close_sync_connection()

def get_database():
    """Legacy function - returns sync database"""
    return db_manager.get_database()

# New async functions
async def connect_to_mongo_async():
    """Create async MongoDB connection"""
    return await db_manager.connect_async()

async def close_mongo_connection_async():
    """Close async MongoDB connection"""
    return await db_manager.close_async_connection()

async def get_database_async():
    """Get async database instance"""
    return await db_manager.get_async_database()

@asynccontextmanager
async def get_async_db_session():
    """Context manager for async database operations"""
    db = await db_manager.get_async_database()
    try:
        yield db
    finally:
        # Connection cleanup is handled by the pool
        pass

# Health check functions
def is_database_healthy() -> bool:
    """Check database health (sync)"""
    return db_manager.is_healthy()

async def is_database_healthy_async() -> bool:
    """Check database health (async)"""
    return await db_manager.async_is_healthy()

def get_database_stats() -> Dict[str, Any]:
    """Get database connection statistics"""
    return db_manager.get_connection_stats()

# Backward compatibility
mongodb = db_manager