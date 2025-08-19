#!/usr/bin/env python3
"""
MongoDB 인덱스 최적화 스크립트
성능 개선을 위한 복합 인덱스 생성
"""

import pymongo
from pymongo import IndexModel, ASCENDING, DESCENDING
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_database
import os

# MongoDB 호스트 환경 변수로 오버라이드
if not os.getenv("MONGODB_HOST"):
    os.environ["MONGODB_HOST"] = "localhost"
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017"

def create_optimized_indexes():
    """최적화된 인덱스 생성"""
    
    db = get_database()
    announcements_collection = db["announcements"]
    
    print("🔧 MongoDB 인덱스 최적화 시작...")
    
    # 기존 인덱스 확인
    existing_indexes = announcements_collection.list_indexes()
    print("\n📋 기존 인덱스:")
    for index in existing_indexes:
        print(f"  - {index['name']}: {index['key']}")
    
    # 최적화된 인덱스 정의
    indexes = [
        # 1. ID와 활성 상태 복합 인덱스 (가장 자주 사용)
        IndexModel([
            ("_id", ASCENDING),
            ("is_active", ASCENDING)
        ], name="idx_id_active"),
        
        # 2. 활성 상태와 생성일 복합 인덱스 (목록 조회)
        IndexModel([
            ("is_active", ASCENDING),
            ("created_at", DESCENDING)
        ], name="idx_active_created"),
        
        # 3. 공고 상태와 마감일 복합 인덱스
        IndexModel([
            ("announcement_data.status", ASCENDING),
            ("announcement_data.deadline", DESCENDING)
        ], name="idx_status_deadline"),
        
        # 4. 사업 유형과 활성 상태 복합 인덱스
        IndexModel([
            ("announcement_data.business_type", ASCENDING),
            ("is_active", ASCENDING),
            ("created_at", DESCENDING)
        ], name="idx_business_type_active"),
        
        # 5. 공고 ID 단일 인덱스 (unique)
        IndexModel([
            ("announcement_data.announcement_id", ASCENDING)
        ], name="idx_announcement_id", unique=True, sparse=True),
        
        # 6. 텍스트 검색을 위한 복합 텍스트 인덱스
        IndexModel([
            ("announcement_data.title", "text"),
            ("announcement_data.content", "text"),
            ("announcement_data.business_name", "text")
        ], name="idx_text_search", default_language="korean"),
        
        # 7. 날짜 범위 검색을 위한 인덱스
        IndexModel([
            ("announcement_data.start_date", ASCENDING),
            ("announcement_data.end_date", ASCENDING),
            ("is_active", ASCENDING)
        ], name="idx_date_range"),
    ]
    
    # 인덱스 생성
    print("\n✨ 새 인덱스 생성 중...")
    created_indexes = []
    
    for index in indexes:
        try:
            # 인덱스가 이미 존재하는지 확인
            index_name = index.document["name"]
            existing_names = [idx["name"] for idx in announcements_collection.list_indexes()]
            
            if index_name in existing_names:
                print(f"  ⏭️  {index_name} - 이미 존재함")
            else:
                announcements_collection.create_indexes([index])
                created_indexes.append(index_name)
                print(f"  ✅ {index_name} - 생성 완료")
        except Exception as e:
            print(f"  ❌ {index_name} - 생성 실패: {e}")
    
    # 인덱스 통계 확인
    print("\n📊 인덱스 통계:")
    stats = db.command("collStats", "announcements", indexDetails=True)
    
    if "indexSizes" in stats:
        print("  인덱스 크기:")
        for index_name, size in stats["indexSizes"].items():
            size_mb = size / 1024 / 1024
            print(f"    - {index_name}: {size_mb:.2f} MB")
    
    print(f"\n✅ 인덱스 최적화 완료! ({len(created_indexes)}개 새로 생성)")
    
    # 쿼리 실행 계획 테스트
    print("\n🔍 쿼리 실행 계획 테스트:")
    
    # 테스트 쿼리 1: ID로 조회
    explain1 = announcements_collection.find(
        {"_id": {"$exists": True}, "is_active": True}
    ).limit(1).explain()
    print(f"  1. ID 조회: {explain1['executionStats']['executionTimeMillis']}ms")
    
    # 테스트 쿼리 2: 목록 조회
    explain2 = announcements_collection.find(
        {"is_active": True}
    ).sort("created_at", -1).limit(10).explain()
    print(f"  2. 목록 조회: {explain2['executionStats']['executionTimeMillis']}ms")
    
    return created_indexes

def drop_unused_indexes():
    """사용하지 않는 인덱스 제거"""
    
    db = get_database()
    announcements_collection = db["announcements"]
    
    print("\n🗑️  사용하지 않는 인덱스 확인 중...")
    
    # 인덱스 사용 통계 확인 (MongoDB 4.2+)
    try:
        index_stats = list(announcements_collection.aggregate([
            {"$indexStats": {}}
        ]))
        
        unused_indexes = []
        for stat in index_stats:
            if stat["name"] != "_id_" and stat.get("accesses", {}).get("ops", 0) == 0:
                unused_indexes.append(stat["name"])
        
        if unused_indexes:
            print(f"  발견된 미사용 인덱스: {unused_indexes}")
            # 주의: 프로덕션에서는 신중하게 제거
            # for index_name in unused_indexes:
            #     announcements_collection.drop_index(index_name)
            #     print(f"  ✅ {index_name} 제거됨")
        else:
            print("  모든 인덱스가 사용 중입니다.")
    except Exception as e:
        print(f"  인덱스 통계를 가져올 수 없습니다: {e}")

if __name__ == "__main__":
    try:
        # 인덱스 최적화
        created = create_optimized_indexes()
        
        # 미사용 인덱스 확인
        drop_unused_indexes()
        
        print("\n🎉 MongoDB 인덱스 최적화가 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)