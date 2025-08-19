#!/usr/bin/env python3
"""
백엔드 API 성능 테스트 스크립트
간헐적으로 느려지는 엔드포인트를 찾기 위한 도구
"""

import time
import asyncio
import statistics
import json
from typing import List, Dict
from datetime import datetime
import httpx
import random
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

# API 엔드포인트 설정
BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    # 공지사항 관련 엔드포인트
    {"method": "GET", "path": "/api/v1/announcements", "name": "공지사항 목록"},
    {"method": "GET", "path": "/api/v1/announcements/stats", "name": "공지사항 통계"},
    {"method": "GET", "path": "/api/v1/announcements/types", "name": "공지사항 타입"},
    {"method": "GET", "path": "/api/v1/announcements/search", "name": "공지사항 검색", "params": {"keyword": "테스트"}},
    
    # 건강 체크
    {"method": "GET", "path": "/health", "name": "헬스체크"},
    {"method": "GET", "path": "/api/v1/health", "name": "API 헬스체크"},
]

class PerformanceMonitor:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = defaultdict(list)
        self.slow_requests = []
        
    def measure_request(self, endpoint: Dict) -> Dict:
        """단일 요청의 응답 시간을 측정"""
        url = f"{self.base_url}{endpoint['path']}"
        params = endpoint.get('params', {})
        
        start_time = time.perf_counter()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=endpoint['method'],
                    url=url,
                    params=params
                )
                elapsed = time.perf_counter() - start_time
                
                return {
                    "endpoint": endpoint['name'],
                    "path": endpoint['path'],
                    "status": response.status_code,
                    "elapsed": elapsed * 1000,  # ms로 변환
                    "timestamp": datetime.now().isoformat(),
                    "success": response.status_code == 200,
                    "size": len(response.content)
                }
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return {
                "endpoint": endpoint['name'],
                "path": endpoint['path'],
                "status": -1,
                "elapsed": elapsed * 1000,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "size": 0
            }
    
    async def measure_request_async(self, endpoint: Dict) -> Dict:
        """비동기 요청 측정"""
        url = f"{self.base_url}{endpoint['path']}"
        params = endpoint.get('params', {})
        
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=endpoint['method'],
                    url=url,
                    params=params
                )
                elapsed = time.perf_counter() - start_time
                
                return {
                    "endpoint": endpoint['name'],
                    "path": endpoint['path'],
                    "status": response.status_code,
                    "elapsed": elapsed * 1000,
                    "timestamp": datetime.now().isoformat(),
                    "success": response.status_code == 200,
                    "size": len(response.content)
                }
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return {
                "endpoint": endpoint['name'],
                "path": endpoint['path'],
                "status": -1,
                "elapsed": elapsed * 1000,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "size": 0
            }
    
    def run_sequential_test(self, iterations: int = 10):
        """순차적으로 각 엔드포인트를 여러 번 테스트"""
        print(f"\n🔍 순차 테스트 시작 (각 엔드포인트 {iterations}회 호출)")
        print("=" * 60)
        
        for endpoint in ENDPOINTS:
            times = []
            for i in range(iterations):
                result = self.measure_request(endpoint)
                times.append(result['elapsed'])
                self.results[endpoint['name']].append(result)
                
                # 느린 요청 기록 (500ms 초과)
                if result['elapsed'] > 500:
                    self.slow_requests.append(result)
                
                # 진행 상황 표시
                print(f"  [{endpoint['name']}] {i+1}/{iterations} - {result['elapsed']:.2f}ms", end='\r')
                
                # 요청 간 짧은 딜레이
                time.sleep(0.1)
            
            # 통계 출력
            avg = statistics.mean(times)
            std = statistics.stdev(times) if len(times) > 1 else 0
            min_time = min(times)
            max_time = max(times)
            
            print(f"\n📊 {endpoint['name']:30} | 평균: {avg:7.2f}ms | 표준편차: {std:7.2f}ms")
            print(f"   최소: {min_time:7.2f}ms | 최대: {max_time:7.2f}ms | 차이: {max_time-min_time:7.2f}ms")
            
            # 큰 편차 경고
            if max_time > min_time * 3:
                print(f"   ⚠️  최대/최소 시간 차이가 3배 이상입니다!")
    
    async def run_concurrent_test(self, concurrent_requests: int = 5):
        """동시에 여러 요청을 보내서 부하 테스트"""
        print(f"\n⚡ 동시성 테스트 시작 ({concurrent_requests}개 동시 요청)")
        print("=" * 60)
        
        tasks = []
        for _ in range(concurrent_requests):
            # 랜덤하게 엔드포인트 선택
            endpoint = random.choice(ENDPOINTS)
            tasks.append(self.measure_request_async(endpoint))
        
        results = await asyncio.gather(*tasks)
        
        # 결과 분석
        by_endpoint = defaultdict(list)
        for result in results:
            by_endpoint[result['endpoint']].append(result['elapsed'])
        
        print("\n📊 동시 요청 결과:")
        for endpoint_name, times in by_endpoint.items():
            avg = statistics.mean(times)
            print(f"  {endpoint_name:30} | 평균: {avg:7.2f}ms | 요청수: {len(times)}")
    
    def run_spike_test(self, duration_seconds: int = 30):
        """스파이크 테스트 - 갑자기 많은 요청을 보내기"""
        print(f"\n🚀 스파이크 테스트 시작 ({duration_seconds}초 동안)")
        print("=" * 60)
        
        start = time.time()
        request_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            while time.time() - start < duration_seconds:
                endpoint = random.choice(ENDPOINTS)
                future = executor.submit(self.measure_request, endpoint)
                request_count += 1
                
                # 진행 상황 표시
                elapsed = time.time() - start
                print(f"  진행: {elapsed:.1f}/{duration_seconds}s | 요청수: {request_count}", end='\r')
                
                # 랜덤 딜레이 (0~0.5초)
                time.sleep(random.uniform(0, 0.5))
        
        print(f"\n✅ 총 {request_count}개 요청 완료")
    
    def analyze_results(self):
        """결과 분석 및 문제점 진단"""
        print("\n" + "=" * 60)
        print("📈 성능 분석 결과")
        print("=" * 60)
        
        # 전체 통계
        all_times = []
        for endpoint_results in self.results.values():
            all_times.extend([r['elapsed'] for r in endpoint_results])
        
        if all_times:
            print(f"\n📊 전체 통계:")
            print(f"  총 요청수: {len(all_times)}")
            print(f"  평균 응답시간: {statistics.mean(all_times):.2f}ms")
            print(f"  중간값: {statistics.median(all_times):.2f}ms")
            print(f"  95 백분위수: {statistics.quantiles(all_times, n=20)[18]:.2f}ms")
            print(f"  99 백분위수: {statistics.quantiles(all_times, n=100)[98]:.2f}ms")
        
        # 느린 요청 분석
        if self.slow_requests:
            print(f"\n⚠️  느린 요청 ({len(self.slow_requests)}개, >500ms):")
            for req in self.slow_requests[:5]:  # 상위 5개만 표시
                print(f"  - {req['endpoint']:30} | {req['elapsed']:.2f}ms | {req['timestamp']}")
        
        # 엔드포인트별 변동성 분석
        print(f"\n📊 엔드포인트별 변동성:")
        variability = []
        for endpoint_name, results in self.results.items():
            if len(results) > 1:
                times = [r['elapsed'] for r in results]
                cv = (statistics.stdev(times) / statistics.mean(times)) * 100  # 변동계수
                variability.append((endpoint_name, cv, statistics.mean(times)))
        
        # 변동성이 큰 순서로 정렬
        variability.sort(key=lambda x: x[1], reverse=True)
        
        for name, cv, avg in variability[:5]:
            status = "🔴" if cv > 50 else "🟡" if cv > 25 else "🟢"
            print(f"  {status} {name:30} | 변동계수: {cv:6.2f}% | 평균: {avg:7.2f}ms")
        
        # 진단 및 권장사항
        print(f"\n💡 진단 결과:")
        
        high_variability = [v for v in variability if v[1] > 50]
        if high_variability:
            print(f"  ⚠️  높은 변동성 엔드포인트 {len(high_variability)}개 발견")
            print(f"     → 캐싱 또는 데이터베이스 쿼리 최적화 필요")
        
        if self.slow_requests:
            slow_endpoints = set(r['endpoint'] for r in self.slow_requests)
            print(f"  ⚠️  간헐적 지연 엔드포인트: {', '.join(slow_endpoints)}")
            print(f"     → 외부 API 의존성 또는 리소스 경합 확인 필요")
        
        # 결과를 파일로 저장
        self.save_results()
    
    def save_results(self):
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_test_{timestamp}.json"
        
        data = {
            "timestamp": timestamp,
            "results": dict(self.results),
            "slow_requests": self.slow_requests,
            "summary": {
                "total_requests": sum(len(r) for r in self.results.values()),
                "slow_request_count": len(self.slow_requests),
                "endpoints_tested": len(self.results)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n💾 결과가 {filename}에 저장되었습니다.")

async def main():
    """메인 테스트 실행"""
    monitor = PerformanceMonitor()
    
    print("🚀 백엔드 성능 테스트 시작")
    print("=" * 60)
    
    # 1. 순차 테스트
    monitor.run_sequential_test(iterations=20)
    
    # 2. 동시성 테스트
    await monitor.run_concurrent_test(concurrent_requests=10)
    
    # 3. 스파이크 테스트
    monitor.run_spike_test(duration_seconds=20)
    
    # 4. 결과 분석
    monitor.analyze_results()

if __name__ == "__main__":
    print("⏳ Docker 컨테이너 시작 확인 중...")
    time.sleep(2)
    
    try:
        # 헬스체크
        response = httpx.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ 백엔드 서버가 실행 중입니다.")
            asyncio.run(main())
        else:
            print("❌ 백엔드 서버 응답 오류")
    except Exception as e:
        print(f"❌ 백엔드 서버에 연결할 수 없습니다: {e}")
        print("\n먼저 Docker 컨테이너를 시작해주세요:")
        print("  docker-compose -f docker-compose.dev.yml up -d")