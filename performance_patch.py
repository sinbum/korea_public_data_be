"""
성능 최적화 패치 - MongoDB 연결 및 타임아웃 설정
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

def get_optimized_mongodb_url():
    """최적화된 MongoDB URL 생성"""
    base_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/korea_public_api")
    
    # URL에 파라미터 추가
    params = {
        "maxPoolSize": os.getenv("MONGODB_MAX_POOL_SIZE", "20"),
        "minPoolSize": os.getenv("MONGODB_MIN_POOL_SIZE", "5"),
        "maxIdleTimeMS": os.getenv("MONGODB_MAX_IDLE_TIME_MS", "30000"),
        "serverSelectionTimeoutMS": os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"),
        "socketTimeoutMS": os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "10000"),
        "heartbeatFrequencyMS": os.getenv("MONGODB_HEARTBEAT_FREQUENCY_MS", "5000"),
        "retryWrites": "true",
        "w": "majority"
    }
    
    # URL에 파라미터 추가
    if "?" in base_url:
        url = base_url + "&" + "&".join([f"{k}={v}" for k, v in params.items()])
    else:
        url = base_url + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    return url

def create_optimized_async_client():
    """최적화된 비동기 MongoDB 클라이언트 생성"""
    url = get_optimized_mongodb_url()
    
    client = AsyncIOMotorClient(
        url,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=10000,
        connectTimeoutMS=5000,
        maxPoolSize=20,
        minPoolSize=5
    )
    
    return client

def create_optimized_sync_client():
    """최적화된 동기 MongoDB 클라이언트 생성"""
    url = get_optimized_mongodb_url()
    
    client = MongoClient(
        url,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=10000,
        connectTimeoutMS=5000,
        maxPoolSize=20,
        minPoolSize=5
    )
    
    return client

# Redis 연결 최적화
def get_redis_pool_config():
    """Redis 연결 풀 설정"""
    return {
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
        "socket_connect_timeout": int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
        "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
        "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
        "health_check_interval": 30
    }
