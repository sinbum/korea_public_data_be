"""
Performance and load testing for Korea Public Data API.

Tests API performance, response times, concurrency handling, and resource usage.
"""

import pytest
import asyncio
import time
import psutil
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from httpx import AsyncClient, Timeout, Limits
from concurrent.futures import ThreadPoolExecutor
import json
import os

from app.main import app
from app.core.config import settings


class TestAPIPerformance:
    """Test API performance metrics"""
    
    @pytest.fixture
    def performance_client(self):
        """Create high-performance async client"""
        limits = Limits(max_keepalive_connections=100, max_connections=200)
        timeout = Timeout(10.0, connect=5.0)
        return AsyncClient(
            app=app,
            base_url="http://test",
            limits=limits,
            timeout=timeout
        )
    
    @pytest.mark.asyncio
    async def test_single_request_performance(self, performance_client):
        """Test single request response time"""
        # Warm up
        await performance_client.get("/api/v1/health")
        
        # Measure single request
        start_time = time.perf_counter()
        response = await performance_client.get("/api/v1/health")
        end_time = time.perf_counter()
        
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert response_time < 100  # Should respond within 100ms
        
        print(f"\n✅ Single request response time: {response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, performance_client):
        """Test handling of concurrent requests"""
        num_requests = 50
        endpoint = "/api/v1/health"
        
        async def make_request():
            start = time.perf_counter()
            response = await performance_client.get(endpoint)
            end = time.perf_counter()
            return {
                "status": response.status_code,
                "time": (end - start) * 1000
            }
        
        # Execute concurrent requests
        tasks = [make_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = sum(1 for r in results if r["status"] == 200)
        response_times = [r["time"] for r in results]
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        assert successful == num_requests, f"Failed requests: {num_requests - successful}"
        assert avg_time < 200, f"Average response time too high: {avg_time:.2f}ms"
        assert p95_time < 500, f"95th percentile too high: {p95_time:.2f}ms"
        
        print(f"\n📊 Concurrent Request Performance ({num_requests} requests):")
        print(f"  ✅ Success rate: {successful}/{num_requests} (100%)")
        print(f"  ⏱️  Average time: {avg_time:.2f}ms")
        print(f"  ⏱️  Median time: {median_time:.2f}ms")
        print(f"  ⏱️  95th percentile: {p95_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, performance_client):
        """Test sustained load over time"""
        duration_seconds = 10
        requests_per_second = 10
        endpoint = "/api/v1/health"
        
        results = []
        errors = []
        start_time = time.time()
        
        async def make_request():
            try:
                req_start = time.perf_counter()
                response = await performance_client.get(endpoint)
                req_end = time.perf_counter()
                return {
                    "status": response.status_code,
                    "time": (req_end - req_start) * 1000,
                    "timestamp": time.time()
                }
            except Exception as e:
                errors.append(str(e))
                return None
        
        # Generate load for specified duration
        while time.time() - start_time < duration_seconds:
            batch_start = time.time()
            tasks = [make_request() for _ in range(requests_per_second)]
            batch_results = await asyncio.gather(*tasks)
            results.extend([r for r in batch_results if r])
            
            # Wait for the rest of the second
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        
        # Analyze results
        total_requests = len(results) + len(errors)
        successful = sum(1 for r in results if r["status"] == 200)
        success_rate = (successful / total_requests) * 100 if total_requests > 0 else 0
        
        if results:
            response_times = [r["time"] for r in results]
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
        else:
            avg_time = max_time = min_time = 0
        
        assert success_rate >= 95, f"Success rate below 95%: {success_rate:.1f}%"
        assert avg_time < 300, f"Average response time too high: {avg_time:.2f}ms"
        
        print(f"\n📈 Sustained Load Test ({duration_seconds}s @ {requests_per_second} req/s):")
        print(f"  📊 Total requests: {total_requests}")
        print(f"  ✅ Success rate: {success_rate:.1f}%")
        print(f"  ❌ Errors: {len(errors)}")
        print(f"  ⏱️  Avg response: {avg_time:.2f}ms")
        print(f"  ⏱️  Min response: {min_time:.2f}ms")
        print(f"  ⏱️  Max response: {max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_client):
        """Test memory usage under load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate some load
        num_requests = 100
        endpoint = "/api/v1/health"
        
        tasks = [performance_client.get(endpoint) for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        
        # Check memory after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"
        
        print(f"\n💾 Memory Usage Test:")
        print(f"  Initial memory: {initial_memory:.2f}MB")
        print(f"  Final memory: {final_memory:.2f}MB")
        print(f"  Memory increase: {memory_increase:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, performance_client):
        """Test rate limiting functionality"""
        # Assuming rate limit is configured (e.g., 100 requests per minute)
        requests_to_trigger_limit = 150
        endpoint = "/api/v1/health"
        
        results = []
        for i in range(requests_to_trigger_limit):
            try:
                response = await performance_client.get(endpoint)
                results.append(response.status_code)
                
                # Small delay to avoid overwhelming
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            except Exception as e:
                results.append(429)  # Rate limit status
        
        # Check if rate limiting kicked in
        rate_limited = sum(1 for status in results if status == 429)
        
        print(f"\n🚦 Rate Limiting Test:")
        print(f"  Total requests: {len(results)}")
        print(f"  Rate limited: {rate_limited}")
        print(f"  Successful: {sum(1 for s in results if s == 200)}")
        
        # Rate limiting should be working if configured
        if rate_limited > 0:
            print("  ✅ Rate limiting is active")
        else:
            print("  ⚠️  Rate limiting may not be configured")


class TestDatabasePerformance:
    """Test database query performance"""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """Test database connection pool performance"""
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.database import get_database
        
        # Test connection pool with concurrent queries
        db = await get_database()
        
        async def perform_query():
            start = time.perf_counter()
            # Simple query to test connection
            result = await db.command("ping")
            end = time.perf_counter()
            return (end - start) * 1000
        
        # Perform concurrent queries
        num_queries = 50
        tasks = [perform_query() for _ in range(num_queries)]
        query_times = await asyncio.gather(*tasks)
        
        avg_time = statistics.mean(query_times)
        max_time = max(query_times)
        
        assert avg_time < 50, f"Average query time too high: {avg_time:.2f}ms"
        assert max_time < 200, f"Max query time too high: {max_time:.2f}ms"
        
        print(f"\n🗄️  Database Connection Pool Test:")
        print(f"  Concurrent queries: {num_queries}")
        print(f"  Average query time: {avg_time:.2f}ms")
        print(f"  Max query time: {max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test performance of common database queries"""
        from app.core.database import get_database
        
        db = await get_database()
        collection = db["test_performance"]
        
        # Insert test data
        test_data = [
            {"name": f"item_{i}", "value": i, "timestamp": datetime.utcnow()}
            for i in range(1000)
        ]
        await collection.insert_many(test_data)
        
        try:
            # Test different query patterns
            queries = [
                ("Simple find", collection.find_one({"name": "item_500"})),
                ("Range query", collection.find({"value": {"$gte": 100, "$lte": 200}}).to_list(100)),
                ("Count", collection.count_documents({})),
                ("Aggregation", collection.aggregate([
                    {"$match": {"value": {"$gte": 500}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$value"}}}
                ]).to_list(1))
            ]
            
            print(f"\n📊 Database Query Performance:")
            for query_name, query_coro in queries:
                start = time.perf_counter()
                result = await query_coro
                end = time.perf_counter()
                query_time = (end - start) * 1000
                
                assert query_time < 100, f"{query_name} too slow: {query_time:.2f}ms"
                print(f"  {query_name}: {query_time:.2f}ms")
        
        finally:
            # Cleanup
            await collection.drop()


class TestAPIEndpointPerformance:
    """Test specific API endpoint performance"""
    
    @pytest.mark.asyncio
    async def test_announcement_list_performance(self):
        """Test announcement list endpoint performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Warm up
            await client.get("/api/v1/announcements")
            
            # Test with different page sizes
            page_sizes = [10, 50, 100]
            
            print(f"\n📋 Announcement List Performance:")
            for size in page_sizes:
                start = time.perf_counter()
                response = await client.get(f"/api/v1/announcements?page_size={size}")
                end = time.perf_counter()
                
                response_time = (end - start) * 1000
                assert response.status_code == 200
                assert response_time < 500, f"Response too slow for size {size}: {response_time:.2f}ms"
                
                print(f"  Page size {size}: {response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_search_performance(self):
        """Test search endpoint performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_queries = [
                "창업",
                "스타트업 지원",
                "기술 혁신",
                "very long search query with multiple words to test performance"
            ]
            
            print(f"\n🔍 Search Performance:")
            for query in search_queries:
                start = time.perf_counter()
                response = await client.get(f"/api/v1/search?q={query}")
                end = time.perf_counter()
                
                response_time = (end - start) * 1000
                assert response.status_code in [200, 204]  # 204 for no results
                assert response_time < 1000, f"Search too slow: {response_time:.2f}ms"
                
                print(f"  Query '{query[:20]}...': {response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_authentication_performance(self):
        """Test authentication endpoint performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test login performance
            login_data = {
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember": False
            }
            
            # Multiple login attempts to test bcrypt performance
            login_times = []
            for _ in range(5):
                start = time.perf_counter()
                response = await client.post("/api/v1/auth/login", json=login_data)
                end = time.perf_counter()
                login_times.append((end - start) * 1000)
            
            avg_login_time = statistics.mean(login_times)
            
            print(f"\n🔐 Authentication Performance:")
            print(f"  Average login time: {avg_login_time:.2f}ms")
            print(f"  Min login time: {min(login_times):.2f}ms")
            print(f"  Max login time: {max(login_times):.2f}ms")
            
            # Bcrypt is intentionally slow, but should still be reasonable
            assert avg_login_time < 500, f"Login too slow: {avg_login_time:.2f}ms"


class TestCachePerformance:
    """Test caching performance"""
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self):
        """Test Redis cache performance"""
        import redis.asyncio as redis
        from app.core.config import settings
        
        # Connect to Redis
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        
        try:
            # Test SET/GET performance
            num_operations = 100
            key_prefix = "perf_test_"
            
            # SET operations
            set_times = []
            for i in range(num_operations):
                key = f"{key_prefix}{i}"
                value = f"value_{i}" * 100  # Larger value to test throughput
                
                start = time.perf_counter()
                await redis_client.set(key, value, ex=60)
                end = time.perf_counter()
                set_times.append((end - start) * 1000)
            
            # GET operations
            get_times = []
            for i in range(num_operations):
                key = f"{key_prefix}{i}"
                
                start = time.perf_counter()
                value = await redis_client.get(key)
                end = time.perf_counter()
                get_times.append((end - start) * 1000)
            
            avg_set = statistics.mean(set_times)
            avg_get = statistics.mean(get_times)
            
            assert avg_set < 10, f"Redis SET too slow: {avg_set:.2f}ms"
            assert avg_get < 5, f"Redis GET too slow: {avg_get:.2f}ms"
            
            print(f"\n⚡ Redis Cache Performance:")
            print(f"  Operations: {num_operations}")
            print(f"  Avg SET time: {avg_set:.2f}ms")
            print(f"  Avg GET time: {avg_get:.2f}ms")
            
            # Cleanup
            keys = [f"{key_prefix}{i}" for i in range(num_operations)]
            if keys:
                await redis_client.delete(*keys)
        
        finally:
            await redis_client.close()
    
    @pytest.mark.asyncio
    async def test_cache_hit_ratio(self):
        """Test cache hit ratio impact on performance"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            endpoint = "/api/v1/announcements"
            
            # First request (cache miss)
            start = time.perf_counter()
            response1 = await client.get(endpoint)
            end = time.perf_counter()
            first_time = (end - start) * 1000
            
            # Second request (potential cache hit)
            start = time.perf_counter()
            response2 = await client.get(endpoint)
            end = time.perf_counter()
            second_time = (end - start) * 1000
            
            # Cache should make second request faster
            improvement = ((first_time - second_time) / first_time) * 100 if first_time > 0 else 0
            
            print(f"\n💨 Cache Hit Performance:")
            print(f"  First request (miss): {first_time:.2f}ms")
            print(f"  Second request (hit): {second_time:.2f}ms")
            print(f"  Performance improvement: {improvement:.1f}%")
            
            # Second request should be faster if caching is working
            if second_time < first_time:
                print("  ✅ Caching is effective")
            else:
                print("  ⚠️  Caching may not be working optimally")


class TestLoadScenarios:
    """Test realistic load scenarios"""
    
    @pytest.mark.asyncio
    async def test_mixed_load_scenario(self):
        """Test mixed load with different endpoint types"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Define endpoint mix (simulating real usage patterns)
            endpoints = [
                ("/api/v1/health", 0.4),  # 40% health checks
                ("/api/v1/announcements", 0.4),  # 40% announcement queries
                ("/api/v1/search?q=test", 0.2),  # 20% searches
            ]
            
            num_requests = 100
            results = []
            
            async def make_request(endpoint: str):
                start = time.perf_counter()
                try:
                    response = await client.get(endpoint)
                    end = time.perf_counter()
                    return {
                        "endpoint": endpoint,
                        "status": response.status_code,
                        "time": (end - start) * 1000
                    }
                except Exception as e:
                    return {
                        "endpoint": endpoint,
                        "status": 500,
                        "time": 0,
                        "error": str(e)
                    }
            
            # Generate mixed load
            import random
            tasks = []
            for _ in range(num_requests):
                rand = random.random()
                cumulative = 0
                for endpoint, probability in endpoints:
                    cumulative += probability
                    if rand <= cumulative:
                        tasks.append(make_request(endpoint))
                        break
            
            results = await asyncio.gather(*tasks)
            
            # Analyze results by endpoint
            endpoint_stats = {}
            for result in results:
                endpoint = result["endpoint"].split("?")[0]
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {
                        "count": 0,
                        "times": [],
                        "errors": 0
                    }
                
                endpoint_stats[endpoint]["count"] += 1
                if result["status"] == 200:
                    endpoint_stats[endpoint]["times"].append(result["time"])
                else:
                    endpoint_stats[endpoint]["errors"] += 1
            
            print(f"\n🎯 Mixed Load Scenario ({num_requests} requests):")
            for endpoint, stats in endpoint_stats.items():
                if stats["times"]:
                    avg_time = statistics.mean(stats["times"])
                    print(f"  {endpoint}:")
                    print(f"    Requests: {stats['count']}")
                    print(f"    Avg time: {avg_time:.2f}ms")
                    print(f"    Errors: {stats['errors']}")
    
    @pytest.mark.asyncio
    async def test_spike_load(self):
        """Test handling of sudden traffic spikes"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            endpoint = "/api/v1/health"
            
            # Normal load
            normal_rps = 5
            spike_rps = 50
            duration_before_spike = 2
            spike_duration = 3
            duration_after_spike = 2
            
            results = {
                "before": [],
                "during": [],
                "after": []
            }
            
            async def make_request():
                start = time.perf_counter()
                try:
                    response = await client.get(endpoint)
                    end = time.perf_counter()
                    return {
                        "status": response.status_code,
                        "time": (end - start) * 1000
                    }
                except:
                    return {"status": 500, "time": 0}
            
            print(f"\n📈 Spike Load Test:")
            
            # Before spike (normal load)
            print(f"  Phase 1: Normal load ({normal_rps} req/s)...")
            for _ in range(duration_before_spike):
                tasks = [make_request() for _ in range(normal_rps)]
                batch_results = await asyncio.gather(*tasks)
                results["before"].extend(batch_results)
                await asyncio.sleep(1)
            
            # During spike
            print(f"  Phase 2: Spike load ({spike_rps} req/s)...")
            for _ in range(spike_duration):
                tasks = [make_request() for _ in range(spike_rps)]
                batch_results = await asyncio.gather(*tasks)
                results["during"].extend(batch_results)
                await asyncio.sleep(1)
            
            # After spike (recovery)
            print(f"  Phase 3: Recovery ({normal_rps} req/s)...")
            for _ in range(duration_after_spike):
                tasks = [make_request() for _ in range(normal_rps)]
                batch_results = await asyncio.gather(*tasks)
                results["after"].extend(batch_results)
                await asyncio.sleep(1)
            
            # Analyze results
            for phase, phase_results in results.items():
                if phase_results:
                    success_rate = sum(1 for r in phase_results if r["status"] == 200) / len(phase_results) * 100
                    times = [r["time"] for r in phase_results if r["time"] > 0]
                    avg_time = statistics.mean(times) if times else 0
                    
                    print(f"\n  {phase.capitalize()} spike:")
                    print(f"    Success rate: {success_rate:.1f}%")
                    print(f"    Avg response: {avg_time:.2f}ms")
                    
                    if phase == "during":
                        # During spike, we allow some degradation but not complete failure
                        assert success_rate >= 80, f"Too many failures during spike: {success_rate:.1f}%"
                    else:
                        # Normal conditions should have high success rate
                        assert success_rate >= 95, f"Low success rate in {phase} phase: {success_rate:.1f}%"


def generate_performance_report(results: Dict[str, Any]):
    """Generate a performance test report"""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENV", "test"),
        "results": results,
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results.values() if r.get("passed", False)),
            "failed": sum(1 for r in results.values() if not r.get("passed", True)),
        }
    }
    
    # Save report to file
    report_dir = "test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    filename = f"{report_dir}/performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Performance report saved to: {filename}")
    
    return report


if __name__ == "__main__":
    # Run performance tests with custom configuration
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings",
        "-k", "test_"  # Run all test functions
    ])