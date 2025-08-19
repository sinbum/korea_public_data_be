#!/usr/bin/env python3
"""
20초 지연 문제 진단 스크립트
외부 API 호출과 MongoDB 쿼리 성능을 추적
"""

import time
import httpx
import asyncio
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_with_timing():
    """각 요청의 타이밍을 상세히 측정"""
    print("🔍 상세 타이밍 분석 시작")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 10번 반복 테스트
        for i in range(10):
            print(f"\n테스트 #{i+1}")
            
            # 1. 헬스체크 (단순)
            start = time.perf_counter()
            try:
                response = await client.get(f"{BASE_URL}/health")
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /health: {elapsed:.2f}ms - Status: {response.status_code}")
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /health: {elapsed:.2f}ms - Error: {e}")
            
            # 2. API 헬스체크
            start = time.perf_counter()
            try:
                response = await client.get(f"{BASE_URL}/api/v1/health")
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /api/v1/health: {elapsed:.2f}ms - Status: {response.status_code}")
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /api/v1/health: {elapsed:.2f}ms - Error: {e}")
            
            # 3. 공지사항 목록 (문제 엔드포인트)
            start = time.perf_counter()
            try:
                response = await client.get(f"{BASE_URL}/api/v1/announcements")
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /api/v1/announcements: {elapsed:.2f}ms - Status: {response.status_code}")
                
                # 20초 지연 발견 시 상세 정보
                if elapsed > 5000:
                    print(f"    ⚠️  극심한 지연 감지! {elapsed:.2f}ms")
                    print(f"    시간: {datetime.now().isoformat()}")
                    
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  /api/v1/announcements: {elapsed:.2f}ms - Error: {e}")
            
            await asyncio.sleep(1)  # 1초 대기

def check_docker_logs():
    """Docker 로그에서 지연 관련 패턴 찾기"""
    print("\n📋 Docker 로그 분석")
    print("=" * 60)
    
    import subprocess
    
    # 백엔드 로그에서 타임아웃이나 지연 패턴 찾기
    patterns = [
        "timeout",
        "slow",
        "delay",
        "20",  # 20초 관련
        "error",
        "failed",
        "retry"
    ]
    
    for pattern in patterns:
        cmd = f"docker logs korea_backend_dev 2>&1 | grep -i {pattern} | tail -5"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(f"\n패턴 '{pattern}':")
            print(result.stdout)

def check_network_issues():
    """네트워크 관련 문제 확인"""
    print("\n🌐 네트워크 진단")
    print("=" * 60)
    
    import subprocess
    
    # Docker 네트워크 확인
    cmd = "docker network inspect korea_dev_network | grep -A 5 korea_backend"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("Docker 네트워크 설정:")
    print(result.stdout)
    
    # 컨테이너 간 연결 테스트
    print("\n컨테이너 간 연결 테스트:")
    
    # Backend -> MongoDB
    cmd = "docker exec korea_backend_dev ping -c 1 mongodb"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "1 packets transmitted, 1 received" in result.stdout:
        print("  ✅ Backend -> MongoDB: 정상")
    else:
        print("  ❌ Backend -> MongoDB: 문제 발생")
    
    # Backend -> Redis
    cmd = "docker exec korea_backend_dev ping -c 1 redis"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "1 packets transmitted, 1 received" in result.stdout:
        print("  ✅ Backend -> Redis: 정상")
    else:
        print("  ❌ Backend -> Redis: 문제 발생")

async def trace_request():
    """요청 추적 - 어디서 지연이 발생하는지 확인"""
    print("\n🔎 요청 추적 (상세 디버그)")
    print("=" * 60)
    
    # 헤더에 추적 정보 추가
    headers = {
        "X-Request-ID": f"trace-{int(time.time())}",
        "X-Debug": "true"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n1. 단순 헬스체크:")
        start = time.perf_counter()
        response = await client.get(f"{BASE_URL}/health", headers=headers)
        print(f"   시간: {(time.perf_counter() - start) * 1000:.2f}ms")
        
        print("\n2. MongoDB 연결 체크 (API 헬스체크):")
        start = time.perf_counter()
        response = await client.get(f"{BASE_URL}/api/v1/health", headers=headers)
        print(f"   시간: {(time.perf_counter() - start) * 1000:.2f}ms")
        
        print("\n3. 빈 쿼리 (limit=0):")
        start = time.perf_counter()
        response = await client.get(f"{BASE_URL}/api/v1/announcements?limit=0", headers=headers)
        print(f"   시간: {(time.perf_counter() - start) * 1000:.2f}ms")
        
        print("\n4. 소량 데이터 (limit=1):")
        start = time.perf_counter()
        response = await client.get(f"{BASE_URL}/api/v1/announcements?limit=1", headers=headers)
        print(f"   시간: {(time.perf_counter() - start) * 1000:.2f}ms")
        
        print("\n5. 기본 쿼리 (limit=20):")
        start = time.perf_counter()
        response = await client.get(f"{BASE_URL}/api/v1/announcements", headers=headers)
        print(f"   시간: {(time.perf_counter() - start) * 1000:.2f}ms")
        
        if response.elapsed.total_seconds() > 5:
            print(f"\n   ⚠️  지연 발생! 응답 헤더:")
            for key, value in response.headers.items():
                if key.lower().startswith('x-'):
                    print(f"      {key}: {value}")

async def main():
    print("🚀 20초 지연 문제 진단 시작")
    print("=" * 60)
    
    # 1. 타이밍 테스트
    await test_with_timing()
    
    # 2. 요청 추적
    await trace_request()
    
    # 3. Docker 로그 분석
    check_docker_logs()
    
    # 4. 네트워크 진단
    check_network_issues()
    
    print("\n✅ 진단 완료")
    print("\n💡 권장사항:")
    print("  1. 외부 API 호출에 타임아웃 설정 확인")
    print("  2. MongoDB 연결 풀 설정 확인")
    print("  3. Redis Circuit Breaker 상태 확인")
    print("  4. 미들웨어 체인에서 블로킹 작업 확인")

if __name__ == "__main__":
    asyncio.run(main())