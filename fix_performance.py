#!/usr/bin/env python3
"""
성능 문제 해결 스크립트
MongoDB heartbeat 타임아웃과 API 리다이렉트 문제 해결
"""

import os
import json

def create_optimized_config():
    """최적화된 설정 파일 생성"""
    
    # 1. MongoDB 연결 최적화 설정
    mongodb_config = """
# MongoDB 연결 최적화 설정
MONGODB_MIN_POOL_SIZE=5
MONGODB_MAX_POOL_SIZE=20
MONGODB_MAX_IDLE_TIME_MS=30000
MONGODB_WAIT_QUEUE_TIMEOUT_MS=5000
MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
MONGODB_HEARTBEAT_FREQUENCY_MS=5000
MONGODB_SOCKET_TIMEOUT_MS=10000

# Redis 최적화 설정
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=True

# API 타임아웃 설정
EXTERNAL_API_TIMEOUT=10
REQUEST_TIMEOUT=30
"""
    
    print("📝 최적화 설정 생성:")
    print(mongodb_config)
    
    # .env.performance 파일로 저장
    with open('.env.performance', 'w') as f:
        f.write(mongodb_config)
    print("✅ .env.performance 파일 생성 완료")
    
    # 2. Docker Compose 수정 제안
    docker_compose_fix = """
# docker-compose.dev.yml 수정 제안:

backend:
  environment:
    # MongoDB 연결 최적화
    - MONGODB_URL=mongodb://api_user:api_password@mongodb:27017/korea_public_api?maxPoolSize=20&minPoolSize=5&maxIdleTimeMS=30000&serverSelectionTimeoutMS=5000
    
    # 추가 환경변수
    - PYTHONUNBUFFERED=1
    - UVICORN_WORKERS=1  # 개발환경에서는 1개로 제한
    - UVICORN_TIMEOUT_KEEP_ALIVE=30
    
  # 리소스 제한 추가
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
"""
    
    print("\n📋 Docker Compose 수정 제안:")
    print(docker_compose_fix)
    
    # 3. MongoDB 인덱스 생성 스크립트
    mongo_indexes = """
// MongoDB 인덱스 생성 스크립트
// mongo shell에서 실행

use korea_public_api;

// 기존 인덱스 확인
db.announcements.getIndexes();

// 성능 최적화 인덱스 생성
db.announcements.createIndex(
    {"is_active": 1, "created_at": -1},
    {name: "active_recent_idx"}
);

db.announcements.createIndex(
    {"announcement_data.business_id": 1, "is_active": 1},
    {name: "business_id_active_idx"}
);

db.announcements.createIndex(
    {"announcement_data.business_type": 1, "is_active": 1, "created_at": -1},
    {name: "type_active_recent_idx"}
);

db.announcements.createIndex(
    {"announcement_data.status": 1, "is_active": 1},
    {name: "status_active_idx"}
);

// 인덱스 생성 확인
db.announcements.getIndexes();
"""
    
    with open('create_indexes.js', 'w') as f:
        f.write(mongo_indexes)
    print("\n✅ create_indexes.js 파일 생성 완료")
    
    return True

def create_performance_patch():
    """성능 패치 코드 생성"""
    
    performance_patch = '''"""
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
'''
    
    with open('performance_patch.py', 'w') as f:
        f.write(performance_patch)
    print("\n✅ performance_patch.py 파일 생성 완료")

def apply_fixes():
    """즉시 적용 가능한 수정사항"""
    
    print("\n🔧 즉시 적용 가능한 수정사항:")
    
    commands = [
        # 1. MongoDB 인덱스 생성
        {
            "desc": "MongoDB 인덱스 생성",
            "cmd": "docker exec korea_mongodb_dev mongosh korea_public_api --eval 'db.announcements.createIndex({\"is_active\": 1, \"created_at\": -1})'"
        },
        
        # 2. 백엔드 재시작 (환경변수 적용)
        {
            "desc": "백엔드 컨테이너 재시작",
            "cmd": "docker-compose -f docker-compose.dev.yml restart backend"
        },
        
        # 3. Redis 플러시 (캐시 초기화)
        {
            "desc": "Redis 캐시 초기화",
            "cmd": "docker exec korea_redis_dev redis-cli FLUSHALL"
        }
    ]
    
    print("\n실행할 명령어:")
    for i, cmd in enumerate(commands, 1):
        print(f"\n{i}. {cmd['desc']}:")
        print(f"   $ {cmd['cmd']}")
    
    return commands

def main():
    print("🚀 성능 문제 해결 스크립트")
    print("=" * 60)
    
    # 1. 최적화 설정 생성
    create_optimized_config()
    
    # 2. 성능 패치 코드 생성
    create_performance_patch()
    
    # 3. 즉시 적용 가능한 수정사항
    commands = apply_fixes()
    
    print("\n" + "=" * 60)
    print("✅ 해결 방안 생성 완료!")
    print("\n다음 단계:")
    print("1. MongoDB 인덱스 생성: docker exec korea_mongodb_dev mongosh < create_indexes.js")
    print("2. 환경변수 추가: cat .env.performance >> be/.env")
    print("3. Docker 재시작: docker-compose -f docker-compose.dev.yml restart")
    print("\n문제 해결 후 다시 테스트를 실행하세요:")
    print("  python3 test_performance.py")

if __name__ == "__main__":
    main()