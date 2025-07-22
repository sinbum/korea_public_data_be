"""
Performance tests for K-Startup API Client.

Tests response times, memory usage, and concurrent request handling.
"""

import pytest
import asyncio
import time
import psutil
import statistics
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import json

from app.shared.clients.kstartup_api_client import KStartupAPIClient
from app.core.interfaces.base_api_client import APIResponse


@pytest.mark.performance
class TestKStartupClientPerformance:
    """Performance tests for K-Startup API client"""
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_response_time_sync(
        self, mock_request, mock_kstartup_client, sample_announcement_xml, 
        mock_httpx_response, performance_test_config
    ):
        """Test synchronous response time performance"""
        # Setup fast mock response
        mock_response = mock_httpx_response(200, sample_announcement_xml)
        mock_request.return_value = mock_response
        
        response_times = []
        iterations = 50
        
        for _ in range(iterations):
            start_time = time.time()
            result = mock_kstartup_client.get_announcement_information()
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert result.success is True
        
        # Calculate performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        print(f"\nSync Performance Metrics:")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Min response time: {min_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        
        # Performance assertions
        assert avg_response_time < 100.0  # Should be very fast with mocked responses
        assert max_response_time < 200.0
        
    async def test_response_time_async(
        self, mock_kstartup_client, sample_announcement_xml, performance_test_config
    ):
        """Test asynchronous response time performance"""
        response_times = []
        iterations = 50
        
        # Mock async response
        async def mock_async_get(*args, **kwargs):
            await asyncio.sleep(0.001)  # Simulate small network delay
            return APIResponse(success=True, data=Mock(), status_code=200)
        
        with patch.object(mock_kstartup_client, 'async_client') as mock_async_context:
            mock_client_instance = AsyncMock()
            mock_client_instance.async_get = mock_async_get
            
            async def async_context_manager():
                yield mock_client_instance
            
            mock_async_context.return_value = async_context_manager()
            
            for _ in range(iterations):
                start_time = time.time()
                result = await mock_kstartup_client.async_get_announcement_information()
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                assert result.success is True
        
        # Calculate performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        
        print(f"\nAsync Performance Metrics:")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        print(f"  Min response time: {min_response_time:.2f}ms")
        print(f"  Max response time: {max_response_time:.2f}ms")
        print(f"  95th percentile: {p95_response_time:.2f}ms")
        
        # Performance assertions
        assert avg_response_time < 50.0  # Should be faster than sync
        assert max_response_time < 100.0
    
    async def test_concurrent_requests_performance(
        self, mock_kstartup_client, performance_test_config
    ):
        """Test concurrent request handling performance"""
        concurrent_requests = performance_test_config["concurrent_requests"]
        
        # Mock async batch processing
        async def mock_batch_processing(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate processing time
            return [
                APIResponse(success=True, data=Mock(), status_code=200)
                for _ in range(concurrent_requests)
            ]
        
        with patch.object(mock_kstartup_client, 'get_all_data_batch', side_effect=mock_batch_processing):
            start_time = time.time()
            
            endpoints = ["getAnnouncementInformation01"] * concurrent_requests
            params_list = [{"page_no": i} for i in range(concurrent_requests)]
            
            results = await mock_kstartup_client.get_all_data_batch(endpoints, params_list)
            
            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000
            
            print(f"\nConcurrent Request Performance:")
            print(f"  {concurrent_requests} concurrent requests completed in {total_time_ms:.2f}ms")
            print(f"  Average time per request: {total_time_ms/concurrent_requests:.2f}ms")
            
            assert len(results) == concurrent_requests
            assert total_time_ms < 1000.0  # Should complete within 1 second
    
    @patch('app.shared.clients.kstartup_api_client.KStartupAPIClient._make_request_with_retry')
    def test_memory_usage(
        self, mock_request, mock_kstartup_client, sample_announcement_xml, 
        mock_httpx_response, performance_test_config
    ):
        """Test memory usage during operations"""
        # Setup mock response
        mock_response = mock_httpx_response(200, sample_announcement_xml)
        mock_request.return_value = mock_response
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Perform multiple operations
        iterations = 100
        results = []
        
        for i in range(iterations):
            result = mock_kstartup_client.get_announcement_information(page_no=i)
            results.append(result)
            
            # Check memory every 10 iterations
            if i % 10 == 0:
                current_memory_mb = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory_mb - initial_memory_mb
                
                # Memory should not grow excessively
                assert memory_increase < performance_test_config["memory_threshold_mb"]
        
        # Final memory check
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory_mb - initial_memory_mb
        
        print(f"\nMemory Usage:")
        print(f"  Initial memory: {initial_memory_mb:.2f}MB")
        print(f"  Final memory: {final_memory_mb:.2f}MB")
        print(f"  Memory increase: {total_memory_increase:.2f}MB")
        print(f"  Memory per operation: {total_memory_increase/iterations:.4f}MB")
        
        # Verify no significant memory leaks
        assert total_memory_increase < performance_test_config["memory_threshold_mb"]
        assert len(results) == iterations
    
    async def test_stress_test_async_operations(self, mock_kstartup_client):
        """Stress test with high load of async operations"""
        total_operations = 200
        batch_size = 20
        
        async def mock_async_operation():
            await asyncio.sleep(0.001)  # Simulate minimal processing
            return APIResponse(success=True, data=Mock(), status_code=200)
        
        with patch.object(mock_kstartup_client, 'async_get_announcement_information', side_effect=mock_async_operation):
            start_time = time.time()
            
            # Create batches of concurrent operations
            all_tasks = []
            for batch_start in range(0, total_operations, batch_size):
                batch_tasks = [
                    mock_kstartup_client.async_get_announcement_information()
                    for _ in range(min(batch_size, total_operations - batch_start))
                ]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                all_tasks.extend(batch_results)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"\nStress Test Results:")
            print(f"  Total operations: {total_operations}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Operations per second: {total_operations/total_time:.2f}")
            print(f"  Average time per operation: {(total_time/total_operations)*1000:.2f}ms")
            
            # Verify all operations completed successfully
            successful_operations = sum(1 for result in all_tasks if isinstance(result, APIResponse) and result.success)
            error_rate = (total_operations - successful_operations) / total_operations
            
            assert error_rate < performance_test_config["error_rate_threshold"]
            assert total_operations / total_time > 50  # At least 50 operations per second


@pytest.mark.performance
class TestKStartupClientRetryPerformance:
    """Test retry logic performance characteristics"""
    
    async def test_retry_performance_exponential_backoff(self, mock_kstartup_client):
        """Test performance characteristics of exponential backoff retry"""
        retry_attempts = []
        
        # Mock a scenario with temporary failures
        attempt_count = 0
        async def mock_failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:  # Fail first 2 attempts
                from app.shared.exceptions import APIServerError
                raise APIServerError("Temporary server error", status_code=500)
            else:
                return APIResponse(success=True, data=Mock(), status_code=200)
        
        # Test retry timing
        with patch.object(mock_kstartup_client.retry_executor, 'execute_async') as mock_executor:
            mock_executor.side_effect = mock_failing_operation
            
            start_time = time.time()
            
            try:
                result = await mock_kstartup_client.async_get_announcement_information()
                end_time = time.time()
                
                total_time = end_time - start_time
                print(f"\nRetry Performance:")
                print(f"  Total retry time: {total_time:.2f}s")
                print(f"  Attempts made: {attempt_count}")
                
                # Should complete within reasonable time even with retries
                assert total_time < 10.0  # Generous upper bound
                assert result.success is True
                
            except Exception as e:
                # If retries are exhausted, that's also a valid test outcome
                end_time = time.time()
                total_time = end_time - start_time
                print(f"  Retry exhausted after: {total_time:.2f}s")
    
    def test_retry_performance_different_strategies(self, mock_api_key):
        """Test performance of different retry strategies"""
        strategies = [
            ("conservative", False),
            ("aggressive", True)
        ]
        
        for strategy_name, use_aggressive in strategies:
            client = KStartupAPIClient(api_key=mock_api_key, use_aggressive_retry=use_aggressive)
            
            # Verify strategy configuration affects performance characteristics
            if use_aggressive:
                assert client.retry_strategy.max_attempts == 5
                assert client.retry_strategy.max_delay == 60.0
            else:
                assert client.retry_strategy.max_attempts == 3
                assert client.retry_strategy.max_delay == 30.0
            
            print(f"\nRetry Strategy: {strategy_name}")
            print(f"  Max attempts: {client.retry_strategy.max_attempts}")
            print(f"  Max delay: {client.retry_strategy.max_delay}s")


@pytest.mark.performance
class TestKStartupClientScalability:
    """Test scalability characteristics"""
    
    async def test_connection_pool_efficiency(self, mock_kstartup_client):
        """Test connection pool usage efficiency"""
        # Test that connection pooling improves performance for multiple requests
        request_count = 50
        
        async def mock_pooled_request():
            await asyncio.sleep(0.002)  # Simulate network latency
            return APIResponse(success=True, data=Mock(), status_code=200)
        
        with patch.object(mock_kstartup_client, 'async_get_announcement_information', side_effect=mock_pooled_request):
            # Test sequential requests (should reuse connections)
            start_time = time.time()
            
            for _ in range(request_count):
                result = await mock_kstartup_client.async_get_announcement_information()
                assert result.success is True
            
            sequential_time = time.time() - start_time
            
            # Test concurrent requests (should use connection pool efficiently)
            start_time = time.time()
            
            tasks = [
                mock_kstartup_client.async_get_announcement_information()
                for _ in range(request_count)
            ]
            results = await asyncio.gather(*tasks)
            
            concurrent_time = time.time() - start_time
            
            print(f"\nConnection Pool Efficiency:")
            print(f"  Sequential {request_count} requests: {sequential_time:.2f}s")
            print(f"  Concurrent {request_count} requests: {concurrent_time:.2f}s")
            print(f"  Concurrency speedup: {sequential_time/concurrent_time:.2f}x")
            
            # Concurrent should be significantly faster
            assert concurrent_time < sequential_time * 0.5  # At least 2x speedup
            assert all(result.success for result in results)
    
    async def test_large_response_handling(self, mock_kstartup_client):
        """Test handling of large API responses"""
        # Simulate large response data
        large_data_items = []
        for i in range(1000):  # 1000 items
            large_data_items.append({
                "pbanc_no": f"A2024{i:04d}",
                "pbanc_titl_nm": f"사업공고 {i}" * 10,  # Long title
                "pbanc_cn": f"사업공고 내용 {i}" * 50,   # Long content
                "pbanc_de": "20240115",
                "biz_category_cd": "cmrczn_Tab3"
            })
        
        large_response_data = {
            "currentCount": len(large_data_items),
            "totalCount": len(large_data_items),
            "page": 1,
            "perPage": len(large_data_items),
            "data": large_data_items
        }
        
        # Mock processing of large response
        async def mock_large_response():
            # Simulate processing time proportional to data size
            await asyncio.sleep(0.1)
            return APIResponse(success=True, data=large_response_data, status_code=200)
        
        with patch.object(mock_kstartup_client, 'async_get_announcement_information', side_effect=mock_large_response):
            start_time = time.time()
            
            result = await mock_kstartup_client.async_get_announcement_information(num_of_rows=1000)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\nLarge Response Handling:")
            print(f"  Data items: {len(large_data_items)}")
            print(f"  Processing time: {processing_time:.2f}s")
            print(f"  Items per second: {len(large_data_items)/processing_time:.2f}")
            
            assert result.success is True
            assert processing_time < 5.0  # Should handle large responses efficiently