"""
Template Method Pattern implementation for API processing.

Provides standardized workflow for API request processing with customizable hooks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic
from datetime import datetime
import logging
import asyncio
from contextlib import asynccontextmanager

from .base_api_client import BaseAPIClient, APIResponse
from ..interfaces.strategies import (
    RequestStrategy, 
    ErrorHandlingStrategy,
    StandardErrorHandlingStrategy
)

logger = logging.getLogger(__name__)

T = TypeVar('T')
ProcessorResult = TypeVar('ProcessorResult')


class APIProcessingContext(Generic[T]):
    """Context object passed through the API processing pipeline"""
    
    def __init__(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.endpoint = endpoint
        self.params = params or {}
        self.data = data
        self.headers = headers or {}
        self.metadata = metadata or {}
        
        # Processing state
        self.start_time = datetime.utcnow()
        self.processing_steps: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.raw_response: Optional[Dict[str, Any]] = None
        self.processed_data: Optional[T] = None
        self.success = False
    
    def add_step(self, step_name: str):
        """Add processing step to context"""
        self.processing_steps.append(f"{datetime.utcnow().isoformat()}: {step_name}")
    
    def add_error(self, error: str):
        """Add error to context"""
        self.errors.append(error)
        logger.error(f"API Processing Error: {error}")
    
    def add_warning(self, warning: str):
        """Add warning to context"""
        self.warnings.append(warning)
        logger.warning(f"API Processing Warning: {warning}")
    
    @property
    def processing_time_ms(self) -> float:
        """Get processing time in milliseconds"""
        return (datetime.utcnow() - self.start_time).total_seconds() * 1000


class APIProcessorTemplate(ABC, Generic[T]):
    """
    Template Method Pattern for API processing.
    
    Defines the standard workflow:
    1. Validate inputs
    2. Preprocess request  
    3. Execute API call
    4. Postprocess response
    5. Transform to domain model
    6. Validate results
    7. Handle errors/cleanup
    """
    
    def __init__(
        self,
        api_client: BaseAPIClient,
        request_strategy: Optional[RequestStrategy] = None,
        error_strategy: Optional[ErrorHandlingStrategy] = None
    ):
        self.api_client = api_client
        self.request_strategy = request_strategy
        self.error_strategy = error_strategy or StandardErrorHandlingStrategy()
    
    def process(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIProcessingContext[T]:
        """
        Template method implementing the standard API processing workflow.
        
        This method defines the algorithm structure and calls hook methods
        that can be overridden by subclasses.
        """
        context = APIProcessingContext[T](
            endpoint=endpoint,
            params=params,
            data=data,
            headers=headers,
            metadata=metadata
        )
        
        try:
            # Step 1: Validate inputs
            context.add_step("Validating inputs")
            validation_errors = self._validate_inputs(context)
            if validation_errors:
                context.errors.extend(validation_errors)
                return context
            
            # Step 2: Preprocess request
            context.add_step("Preprocessing request")
            self._preprocess_request(context)
            
            # Step 3: Execute API call
            context.add_step("Executing API call")
            self._execute_api_call(context)
            
            if not context.success:
                return context
            
            # Step 4: Postprocess response
            context.add_step("Postprocessing response")
            self._postprocess_response(context)
            
            # Step 5: Transform to domain model
            context.add_step("Transforming to domain model")
            self._transform_to_domain_model(context)
            
            # Step 6: Validate results
            context.add_step("Validating results")
            self._validate_results(context)
            
            # Step 7: Finalize processing
            context.add_step("Finalizing processing")
            self._finalize_processing(context)
            
        except Exception as e:
            context.add_error(f"Unexpected error in processing: {str(e)}")
            context.success = False
        finally:
            # Step 8: Cleanup
            context.add_step("Cleanup")
            self._cleanup(context)
        
        return context
    
    # Hook methods that can be overridden by subclasses
    
    def _validate_inputs(self, context: APIProcessingContext[T]) -> List[str]:
        """
        Hook method: Validate input parameters.
        
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        if not context.endpoint:
            errors.append("Endpoint is required")
        
        # Override in subclasses for specific validation
        return errors
    
    def _preprocess_request(self, context: APIProcessingContext[T]) -> None:
        """
        Hook method: Preprocess request before API call.
        
        Apply request strategy, add default parameters, etc.
        """
        # Apply request strategy if configured
        if self.request_strategy:
            request_params = {
                "method": "GET",
                "url": f"{self.api_client.base_url}/{context.endpoint}",
                "params": context.params,
                "data": context.data,
                "headers": context.headers
            }
            processed_params = self.request_strategy.process_request(request_params)
            
            context.params = processed_params.get("params", context.params)
            context.data = processed_params.get("data", context.data)
            context.headers = processed_params.get("headers", context.headers)
        
        # Override in subclasses for custom preprocessing
    
    def _execute_api_call(self, context: APIProcessingContext[T]) -> None:
        """
        Template method: Execute the actual API call with retry logic.
        
        This implements the standard retry logic and should not be overridden.
        """
        attempt = 0
        max_retries = getattr(self.api_client, 'max_retries', 3)
        
        while attempt <= max_retries:
            try:
                with self.api_client as client:
                    response = client.get(
                        context.endpoint,
                        params=context.params
                    )
                
                if response.success:
                    context.raw_response = {
                        "success": response.success,
                        "data": response.data,
                        "status_code": response.status_code,
                        "total_count": response.total_count,
                        "current_count": response.current_count
                    }
                    context.success = True
                    return
                else:
                    # Check if we should retry
                    if self.error_strategy.should_retry(
                        response.status_code, attempt, max_retries
                    ):
                        delay = self.error_strategy.get_retry_delay(attempt)
                        context.add_warning(
                            f"API call failed (attempt {attempt + 1}), retrying in {delay}s"
                        )
                        import time
                        time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        context.add_error(f"API call failed: {response.error}")
                        return
                        
            except Exception as e:
                if self.error_strategy.should_retry(500, attempt, max_retries):
                    delay = self.error_strategy.get_retry_delay(attempt)
                    context.add_warning(
                        f"API call exception (attempt {attempt + 1}), retrying in {delay}s: {str(e)}"
                    )
                    import time
                    time.sleep(delay)
                    attempt += 1
                    continue
                else:
                    context.add_error(f"API call exception: {str(e)}")
                    return
        
        context.add_error(f"API call failed after {max_retries + 1} attempts")
    
    def _postprocess_response(self, context: APIProcessingContext[T]) -> None:
        """
        Hook method: Postprocess raw API response.
        
        Clean up data, apply transformations, etc.
        """
        # Override in subclasses for custom postprocessing
        pass
    
    @abstractmethod
    def _transform_to_domain_model(self, context: APIProcessingContext[T]) -> None:
        """
        Abstract hook method: Transform response to domain model.
        
        Must be implemented by subclasses.
        """
        pass
    
    def _validate_results(self, context: APIProcessingContext[T]) -> None:
        """
        Hook method: Validate the transformed results.
        
        Check business rules, data integrity, etc.
        """
        if context.processed_data is None:
            context.add_error("No processed data available")
            context.success = False
        
        # Override in subclasses for specific validation
    
    def _finalize_processing(self, context: APIProcessingContext[T]) -> None:
        """
        Hook method: Finalize processing.
        
        Log results, update metrics, etc.
        """
        processing_time = context.processing_time_ms
        
        if context.success:
            logger.info(
                f"API processing completed successfully: {context.endpoint} "
                f"({processing_time:.2f}ms)"
            )
        else:
            logger.error(
                f"API processing failed: {context.endpoint} "
                f"({processing_time:.2f}ms) - Errors: {'; '.join(context.errors)}"
            )
    
    def _cleanup(self, context: APIProcessingContext[T]) -> None:
        """
        Hook method: Cleanup resources.
        
        Close connections, release locks, etc.
        """
        # Override in subclasses for custom cleanup
        pass


class BatchAPIProcessor(APIProcessorTemplate[List[T]]):
    """
    Specialized processor for batch API operations.
    
    Handles multiple API calls with parallel processing.
    """
    
    def __init__(
        self,
        api_client: BaseAPIClient,
        request_strategy: Optional[RequestStrategy] = None,
        error_strategy: Optional[ErrorHandlingStrategy] = None,
        max_concurrent: int = 5
    ):
        super().__init__(api_client, request_strategy, error_strategy)
        self.max_concurrent = max_concurrent
    
    async def process_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[APIProcessingContext[T]]:
        """
        Process multiple API requests concurrently.
        
        Args:
            requests: List of request dictionaries with keys:
                - endpoint, params, data, headers, metadata
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single(request_data: Dict[str, Any]) -> APIProcessingContext[T]:
            async with semaphore:
                return await self._async_process_single(request_data)
        
        tasks = [process_single(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _async_process_single(self, request_data: Dict[str, Any]) -> APIProcessingContext[T]:
        """Process single request asynchronously"""
        # Convert sync process to async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.process,
            request_data.get("endpoint"),
            request_data.get("params"),
            request_data.get("data"),
            request_data.get("headers"),
            request_data.get("metadata")
        )
    
    def _transform_to_domain_model(self, context: APIProcessingContext[List[T]]) -> None:
        """Transform batch response to list of domain models"""
        if not context.raw_response or not context.raw_response.get("success"):
            context.processed_data = []
            return
        
        # Extract data items from response
        response_data = context.raw_response.get("data")
        if hasattr(response_data, 'data') and isinstance(response_data.data, list):
            context.processed_data = response_data.data
        else:
            context.processed_data = []


class CachedAPIProcessor(APIProcessorTemplate[T]):
    """
    API processor with caching support.
    
    Implements caching layer to reduce API calls.
    """
    
    def __init__(
        self,
        api_client: BaseAPIClient,
        cache_ttl_seconds: int = 300,
        request_strategy: Optional[RequestStrategy] = None,
        error_strategy: Optional[ErrorHandlingStrategy] = None
    ):
        super().__init__(api_client, request_strategy, error_strategy)
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _preprocess_request(self, context: APIProcessingContext[T]) -> None:
        """Check cache before making API call"""
        super()._preprocess_request(context)
        
        # Generate cache key
        cache_key = self._generate_cache_key(context)
        context.metadata["cache_key"] = cache_key
        
        # Check cache
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            cache_time = cached_data.get("timestamp", 0)
            
            if (datetime.utcnow().timestamp() - cache_time) < self.cache_ttl_seconds:
                context.raw_response = cached_data["response"]
                context.success = True
                context.add_step("Retrieved from cache")
                context.metadata["from_cache"] = True
                return
        
        context.metadata["from_cache"] = False
    
    def _finalize_processing(self, context: APIProcessingContext[T]) -> None:
        """Store successful results in cache"""
        super()._finalize_processing(context)
        
        if context.success and not context.metadata.get("from_cache", False):
            cache_key = context.metadata.get("cache_key")
            if cache_key and context.raw_response:
                self._cache[cache_key] = {
                    "response": context.raw_response,
                    "timestamp": datetime.utcnow().timestamp()
                }
    
    def _generate_cache_key(self, context: APIProcessingContext[T]) -> str:
        """Generate cache key from request parameters"""
        import hashlib
        import json
        
        key_data = {
            "endpoint": context.endpoint,
            "params": context.params,
            "data": context.data
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the entire cache"""
        self._cache.clear()
    
    def clear_expired_cache(self):
        """Clear expired cache entries"""
        current_time = datetime.utcnow().timestamp()
        expired_keys = [
            key for key, data in self._cache.items()
            if (current_time - data.get("timestamp", 0)) >= self.cache_ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]