#!/usr/bin/env python3
"""
MongoDB 성능 모니터링 스크립트
데이터베이스 쿼리 성능과 인덱스 사용을 모니터링
"""

import time
import json
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, List
import statistics

class MongoDBMonitor:
    def __init__(self, connection_string: str = "mongodb://admin:admin123@localhost:27017/"):
        self.client = MongoClient(connection_string)
        self.db = self.client['korea_public_api']
        
    def check_indexes(self):
        """현재 인덱스 상태 확인"""
        print("\n📋 MongoDB 인덱스 현황")
        print("=" * 60)
        
        collections = ['announcements', 'companies', 'investments']
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                indexes = list(collection.list_indexes())
                
                print(f"\n📁 {collection_name} 컬렉션:")
                for idx in indexes:
                    print(f"  - {idx['name']}: {json.dumps(idx['key'], indent=0)}")
                
                # 컬렉션 통계
                stats = self.db.command("collStats", collection_name)
                print(f"  📊 문서 수: {stats.get('count', 0):,}")
                print(f"  💾 크기: {stats.get('size', 0) / 1024 / 1024:.2f} MB")
                
            except Exception as e:
                print(f"  ❌ 오류: {e}")
    
    def analyze_slow_queries(self):
        """느린 쿼리 분석"""
        print("\n🐌 느린 쿼리 분석")
        print("=" * 60)
        
        # 프로파일링 활성화 (레벨 1: 느린 쿼리만, 100ms 이상)
        self.db.command("profile", 1, slowms=100)
        
        # 프로파일 데이터 조회
        profile_collection = self.db['system.profile']
        slow_queries = list(profile_collection.find().sort("ts", -1).limit(10))
        
        if slow_queries:
            print(f"\n최근 느린 쿼리 {len(slow_queries)}개:")
            for query in slow_queries:
                print(f"\n  ⏱️  실행시간: {query.get('millis', 0)}ms")
                print(f"  📁 컬렉션: {query.get('ns', 'N/A')}")
                print(f"  🔍 작업: {query.get('op', 'N/A')}")
                
                if 'command' in query:
                    cmd = query['command']
                    if 'filter' in cmd:
                        print(f"  📝 필터: {json.dumps(cmd['filter'], indent=4)}")
                
                if 'planSummary' in query:
                    print(f"  📊 실행계획: {query['planSummary']}")
        else:
            print("  ✅ 최근 느린 쿼리가 없습니다.")
    
    def test_query_performance(self):
        """주요 쿼리 성능 테스트"""
        print("\n⚡ 쿼리 성능 테스트")
        print("=" * 60)
        
        collection = self.db['announcements']
        
        test_queries = [
            {
                "name": "전체 조회",
                "query": {},
                "limit": 100
            },
            {
                "name": "비즈니스 타입별 조회",
                "query": {"announcement_data.business_type": "K-Startup"},
                "limit": 100
            },
            {
                "name": "활성 문서만 조회",
                "query": {"is_active": True},
                "limit": 100
            },
            {
                "name": "복합 조건 조회",
                "query": {
                    "is_active": True,
                    "announcement_data.business_type": {"$exists": True}
                },
                "limit": 100
            },
            {
                "name": "중복 체크 쿼리",
                "query": {
                    "announcement_data.business_id": "TEST_ID",
                    "is_active": True
                },
                "limit": 1
            }
        ]
        
        for test in test_queries:
            times = []
            
            # 각 쿼리를 10번 실행
            for _ in range(10):
                start = time.perf_counter()
                list(collection.find(test['query']).limit(test['limit']))
                elapsed = (time.perf_counter() - start) * 1000  # ms로 변환
                times.append(elapsed)
                time.sleep(0.01)  # 짧은 딜레이
            
            avg = statistics.mean(times)
            std = statistics.stdev(times) if len(times) > 1 else 0
            
            # 실행 계획 확인
            explain = collection.find(test['query']).limit(test['limit']).explain()
            plan = explain.get('executionStats', {})
            
            print(f"\n📊 {test['name']}:")
            print(f"  평균: {avg:.2f}ms (±{std:.2f}ms)")
            print(f"  최소/최대: {min(times):.2f}ms / {max(times):.2f}ms")
            print(f"  검사한 문서: {plan.get('totalDocsExamined', 'N/A')}")
            print(f"  반환한 문서: {plan.get('nReturned', 'N/A')}")
            
            # 인덱스 사용 여부
            if plan.get('totalDocsExamined', 0) > plan.get('nReturned', 0) * 2:
                print(f"  ⚠️  비효율적: 너무 많은 문서를 검사함")
    
    def suggest_indexes(self):
        """인덱스 추천"""
        print("\n💡 인덱스 최적화 제안")
        print("=" * 60)
        
        suggestions = [
            {
                "collection": "announcements",
                "index": {"announcement_data.business_id": 1, "is_active": 1},
                "reason": "중복 체크 쿼리 최적화"
            },
            {
                "collection": "announcements",
                "index": {"announcement_data.business_type": 1, "is_active": 1},
                "reason": "비즈니스 타입별 조회 최적화"
            },
            {
                "collection": "announcements",
                "index": {"announcement_data.status": 1, "created_at": -1},
                "reason": "상태별 최신 데이터 조회 최적화"
            },
            {
                "collection": "announcements",
                "index": {"is_active": 1, "updated_at": -1},
                "reason": "활성 문서 조회 최적화"
            }
        ]
        
        print("\n권장 인덱스:")
        for idx, suggestion in enumerate(suggestions, 1):
            print(f"\n{idx}. {suggestion['collection']} 컬렉션:")
            print(f"   인덱스: {json.dumps(suggestion['index'])}")
            print(f"   이유: {suggestion['reason']}")
            
            # 인덱스 생성 명령어 제공
            index_cmd = f"db.{suggestion['collection']}.createIndex({json.dumps(suggestion['index'])})"
            print(f"   명령어: {index_cmd}")
    
    def monitor_connections(self):
        """연결 상태 모니터링"""
        print("\n🔌 MongoDB 연결 상태")
        print("=" * 60)
        
        server_status = self.db.command("serverStatus")
        connections = server_status.get('connections', {})
        
        print(f"  현재 연결: {connections.get('current', 0)}")
        print(f"  사용 가능: {connections.get('available', 0)}")
        print(f"  총 생성됨: {connections.get('totalCreated', 0)}")
        
        # 메모리 사용량
        mem = server_status.get('mem', {})
        print(f"\n💾 메모리 사용:")
        print(f"  상주: {mem.get('resident', 0)} MB")
        print(f"  가상: {mem.get('virtual', 0)} MB")
        
        # 작업 통계
        opcounters = server_status.get('opcounters', {})
        print(f"\n📊 작업 통계:")
        print(f"  삽입: {opcounters.get('insert', 0):,}")
        print(f"  조회: {opcounters.get('query', 0):,}")
        print(f"  업데이트: {opcounters.get('update', 0):,}")
        print(f"  삭제: {opcounters.get('delete', 0):,}")

def main():
    print("🔍 MongoDB 성능 모니터링 시작")
    print("=" * 60)
    
    try:
        monitor = MongoDBMonitor()
        
        # 1. 인덱스 확인
        monitor.check_indexes()
        
        # 2. 느린 쿼리 분석
        monitor.analyze_slow_queries()
        
        # 3. 쿼리 성능 테스트
        monitor.test_query_performance()
        
        # 4. 인덱스 제안
        monitor.suggest_indexes()
        
        # 5. 연결 상태
        monitor.monitor_connections()
        
        print("\n✅ 모니터링 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("\nMongoDB가 실행 중인지 확인해주세요:")
        print("  docker-compose -f docker-compose.dev.yml up -d mongodb")

if __name__ == "__main__":
    main()