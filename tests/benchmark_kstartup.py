"""
Benchmark script for K-Startup API Client performance analysis.

Provides detailed performance metrics and comparison between sync/async operations.
"""

import asyncio
import time
import statistics
import psutil
import json
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import matplotlib.pyplot as plt
import pandas as pd
from dataclasses import dataclass

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.core.interfaces.base_api_client import APIResponse


@dataclass
class BenchmarkResult:
    """Benchmark result data structure"""
    test_name: str
    operation_count: int
    total_time_seconds: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    operations_per_second: float
    memory_used_mb: float
    error_count: int
    success_rate: float


class KStartupBenchmark:
    """Comprehensive benchmark suite for K-Startup API client"""
    
    def __init__(self, api_key: str = "test_key"):
        self.api_key = api_key
        self.results: List[BenchmarkResult] = []
        
        # Sample response data for mocking
        self.sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <response>
            <currentCount>1</currentCount>
            <matchCount>1</matchCount>
            <totalCount>1</totalCount>
            <data>
                <item>
                    <col name="pbanc_no">A2024001</col>
                    <col name="pbanc_titl_nm">테스트 공고</col>
                    <col name="pbanc_de">20240115</col>
                </item>
            </data>
        </response>"""
        
        self.sample_json = {
            "currentCount": 1,
            "totalCount": 1,
            "data": [{"pbanc_no": "A2024001", "pbanc_titl_nm": "테스트 공고"}]
        }
    
    def _mock_httpx_response(self, status_code: int = 200, content: str = None):
        """Create mock httpx response"""
        response = Mock()
        response.status_code = status_code
        response.text = content or self.sample_xml
        response.headers = {}
        return response
    
    async def _mock_async_response(self, delay_ms: float = 0):
        """Create mock async response with configurable delay"""
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)
        return APIResponse(success=True, data=Mock(), status_code=200)
    
    def benchmark_sync_operations(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark synchronous operations"""
        print(f"Running sync benchmark with {iterations} iterations...")
        
        client = KStartupAPIClient(api_key=self.api_key)
        response_times = []
        error_count = 0
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        with patch.object(client, '_make_request_with_retry') as mock_request:
            mock_request.return_value = self._mock_httpx_response()
            
            start_time = time.time()
            
            for i in range(iterations):
                operation_start = time.time()
                
                try:
                    result = client.get_announcement_information(page_no=i % 10 + 1)
                    if not result.success:
                        error_count += 1
                except Exception:
                    error_count += 1
                
                operation_end = time.time()
                response_times.append((operation_end - operation_start) * 1000)
            
            total_time = time.time() - start_time
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        ops_per_second = iterations / total_time
        success_rate = (iterations - error_count) / iterations
        
        result = BenchmarkResult(
            test_name="Sync Operations",
            operation_count=iterations,
            total_time_seconds=total_time,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            operations_per_second=ops_per_second,
            memory_used_mb=memory_used,
            error_count=error_count,
            success_rate=success_rate
        )
        
        self.results.append(result)
        return result
    
    async def benchmark_async_operations(self, iterations: int = 100) -> BenchmarkResult:
        """Benchmark asynchronous operations"""
        print(f"Running async benchmark with {iterations} iterations...")
        
        client = KStartupAPIClient(api_key=self.api_key)
        response_times = []
        error_count = 0
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        
        # Mock async client context
        async def mock_async_get(*args, **kwargs):
            return await self._mock_async_response(delay_ms=1)
        
        with patch.object(client, 'async_client') as mock_async_context:
            mock_client_instance = Mock()
            mock_client_instance.async_get = mock_async_get
            
            async def async_context_manager():
                yield mock_client_instance
            
            mock_async_context.return_value = async_context_manager()
            
            for i in range(iterations):
                operation_start = time.time()
                
                try:
                    result = await client.async_get_announcement_information(page_no=i % 10 + 1)
                    if not result.success:
                        error_count += 1
                except Exception:
                    error_count += 1
                
                operation_end = time.time()
                response_times.append((operation_end - operation_start) * 1000)
        
        total_time = time.time() - start_time
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        ops_per_second = iterations / total_time
        success_rate = (iterations - error_count) / iterations
        
        result = BenchmarkResult(
            test_name="Async Operations",
            operation_count=iterations,
            total_time_seconds=total_time,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            operations_per_second=ops_per_second,
            memory_used_mb=memory_used,
            error_count=error_count,
            success_rate=success_rate
        )
        
        self.results.append(result)
        return result
    
    async def benchmark_concurrent_operations(self, concurrent_count: int = 20, batches: int = 5) -> BenchmarkResult:
        """Benchmark concurrent operations"""
        print(f"Running concurrent benchmark with {concurrent_count} concurrent ops, {batches} batches...")
        
        client = KStartupAPIClient(api_key=self.api_key)
        total_operations = concurrent_count * batches
        response_times = []
        error_count = 0
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Mock batch processing
        async def mock_batch_processing(endpoints, params_list):
            await asyncio.sleep(0.01)  # Simulate batch processing time
            return [
                APIResponse(success=True, data=Mock(), status_code=200)
                for _ in range(len(endpoints))
            ]
        
        start_time = time.time()
        
        with patch.object(client, 'get_all_data_batch', side_effect=mock_batch_processing):
            for batch in range(batches):
                batch_start = time.time()
                
                endpoints = ["getAnnouncementInformation01"] * concurrent_count
                params_list = [{"page_no": i} for i in range(concurrent_count)]
                
                try:
                    results = await client.get_all_data_batch(endpoints, params_list)
                    batch_errors = sum(1 for r in results if not (hasattr(r, 'success') and r.success))
                    error_count += batch_errors
                except Exception:
                    error_count += concurrent_count
                
                batch_end = time.time()
                batch_time = (batch_end - batch_start) * 1000
                
                # Record time per operation in this batch
                for _ in range(concurrent_count):
                    response_times.append(batch_time / concurrent_count)
        
        total_time = time.time() - start_time
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        ops_per_second = total_operations / total_time
        success_rate = (total_operations - error_count) / total_operations
        
        result = BenchmarkResult(
            test_name="Concurrent Operations",
            operation_count=total_operations,
            total_time_seconds=total_time,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            operations_per_second=ops_per_second,
            memory_used_mb=memory_used,
            error_count=error_count,
            success_rate=success_rate
        )
        
        self.results.append(result)
        return result
    
    def benchmark_retry_scenarios(self, iterations: int = 50) -> BenchmarkResult:
        """Benchmark retry scenarios"""
        print(f"Running retry benchmark with {iterations} iterations...")
        
        client = KStartupAPIClient(api_key=self.api_key, use_aggressive_retry=True)
        response_times = []
        error_count = 0
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Mock retry scenario
        retry_count = 0
        def mock_request_with_retries():
            nonlocal retry_count
            retry_count += 1
            
            # Simulate failures for first few attempts
            if retry_count % 3 == 1:  # Fail every 3rd attempt initially
                from app.shared.exceptions import APIServerError
                raise APIServerError("Temporary failure", status_code=500)
            else:
                return self._mock_httpx_response()
        
        with patch.object(client.retry_executor, 'execute_sync') as mock_executor:
            start_time = time.time()
            
            for i in range(iterations):
                operation_start = time.time()
                
                try:
                    # Simulate some operations succeeding after retry
                    if i % 4 == 0:  # 25% of operations need retry
                        mock_executor.side_effect = mock_request_with_retries
                    else:
                        mock_executor.return_value = self._mock_httpx_response()
                    
                    result = client.get_announcement_information(page_no=i)
                    if not result.success:
                        error_count += 1
                except Exception:
                    error_count += 1
                
                operation_end = time.time()
                response_times.append((operation_end - operation_start) * 1000)
            
            total_time = time.time() - start_time
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        ops_per_second = iterations / total_time
        success_rate = (iterations - error_count) / iterations
        
        result = BenchmarkResult(
            test_name="Retry Scenarios",
            operation_count=iterations,
            total_time_seconds=total_time,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            operations_per_second=ops_per_second,
            memory_used_mb=memory_used,
            error_count=error_count,
            success_rate=success_rate
        )
        
        self.results.append(result)
        return result
    
    def print_results(self):
        """Print benchmark results in a formatted table"""
        print("\n" + "="*120)
        print("K-STARTUP API CLIENT BENCHMARK RESULTS")
        print("="*120)
        
        headers = [
            "Test Name", "Operations", "Total Time(s)", "Avg RT(ms)", 
            "Min RT(ms)", "Max RT(ms)", "P95 RT(ms)", "Ops/sec", 
            "Memory(MB)", "Errors", "Success%"
        ]
        
        print(f"{headers[0]:<20} {headers[1]:<10} {headers[2]:<12} {headers[3]:<10} {headers[4]:<10} "
              f"{headers[5]:<10} {headers[6]:<10} {headers[7]:<8} {headers[8]:<10} {headers[9]:<6} {headers[10]:<8}")
        print("-" * 120)
        
        for result in self.results:
            print(f"{result.test_name:<20} {result.operation_count:<10} {result.total_time_seconds:<12.2f} "
                  f"{result.avg_response_time_ms:<10.2f} {result.min_response_time_ms:<10.2f} "
                  f"{result.max_response_time_ms:<10.2f} {result.p95_response_time_ms:<10.2f} "
                  f"{result.operations_per_second:<8.1f} {result.memory_used_mb:<10.2f} "
                  f"{result.error_count:<6} {result.success_rate*100:<8.1f}")
    
    def save_results_to_json(self, filename: str = "benchmark_results.json"):
        """Save results to JSON file"""
        results_data = []
        for result in self.results:
            results_data.append({
                "test_name": result.test_name,
                "operation_count": result.operation_count,
                "total_time_seconds": result.total_time_seconds,
                "avg_response_time_ms": result.avg_response_time_ms,
                "min_response_time_ms": result.min_response_time_ms,
                "max_response_time_ms": result.max_response_time_ms,
                "p95_response_time_ms": result.p95_response_time_ms,
                "operations_per_second": result.operations_per_second,
                "memory_used_mb": result.memory_used_mb,
                "error_count": result.error_count,
                "success_rate": result.success_rate
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to {filename}")
    
    def create_performance_plots(self):
        """Create performance visualization plots"""
        if not self.results:
            print("No results to plot")
            return
        
        try:
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            test_names = [r.test_name for r in self.results]
            
            # 1. Operations per second comparison
            ops_per_sec = [r.operations_per_second for r in self.results]
            ax1.bar(test_names, ops_per_sec, color='skyblue')
            ax1.set_title('Operations per Second')
            ax1.set_ylabel('Ops/sec')
            ax1.tick_params(axis='x', rotation=45)
            
            # 2. Response time comparison
            avg_times = [r.avg_response_time_ms for r in self.results]
            p95_times = [r.p95_response_time_ms for r in self.results]
            
            x = range(len(test_names))
            width = 0.35
            ax2.bar([i - width/2 for i in x], avg_times, width, label='Average', color='lightgreen')
            ax2.bar([i + width/2 for i in x], p95_times, width, label='95th Percentile', color='orange')
            ax2.set_title('Response Times')
            ax2.set_ylabel('Time (ms)')
            ax2.set_xticks(x)
            ax2.set_xticklabels(test_names, rotation=45)
            ax2.legend()
            
            # 3. Memory usage
            memory_usage = [r.memory_used_mb for r in self.results]
            ax3.bar(test_names, memory_usage, color='lightcoral')
            ax3.set_title('Memory Usage')
            ax3.set_ylabel('Memory (MB)')
            ax3.tick_params(axis='x', rotation=45)
            
            # 4. Success rate
            success_rates = [r.success_rate * 100 for r in self.results]
            ax4.bar(test_names, success_rates, color='lightpink')
            ax4.set_title('Success Rate')
            ax4.set_ylabel('Success (%)')
            ax4.set_ylim(0, 100)
            ax4.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.savefig('kstartup_performance_benchmark.png', dpi=300, bbox_inches='tight')
            print("Performance plots saved to kstartup_performance_benchmark.png")
            
        except ImportError:
            print("Matplotlib not available. Skipping plot generation.")


async def main():
    """Run comprehensive benchmark suite"""
    print("Starting K-Startup API Client Benchmark Suite")
    print("=" * 60)
    
    benchmark = KStartupBenchmark()
    
    # Run all benchmarks
    await benchmark.benchmark_sync_operations(iterations=100)
    await benchmark.benchmark_async_operations(iterations=100)
    await benchmark.benchmark_concurrent_operations(concurrent_count=20, batches=5)
    benchmark.benchmark_retry_scenarios(iterations=50)
    
    # Display results
    benchmark.print_results()
    
    # Save results
    benchmark.save_results_to_json("tests/benchmark_results.json")
    
    # Create visualizations
    benchmark.create_performance_plots()
    
    print("\nBenchmark completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())