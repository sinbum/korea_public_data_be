"""
Advanced retry strategies for API clients.

Implements sophisticated retry logic with exponential backoff, jitter, and custom conditions.
"""

import asyncio
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, Type, Union, Callable, Any
from dataclasses import dataclass
from enum import Enum

from ...shared.exceptions import (
    KoreanPublicAPIError, 
    APIServerError, 
    APITimeoutError, 
    APIRateLimitError,
    NetworkError
)

logger = logging.getLogger(__name__)


class RetryCondition(Enum):
    """Conditions for retry decisions"""
    ALWAYS = "always"
    NEVER = "never"
    ON_SERVER_ERROR = "on_server_error"
    ON_TIMEOUT = "on_timeout"
    ON_RATE_LIMIT = "on_rate_limit"
    ON_NETWORK_ERROR = "on_network_error"
    CUSTOM = "custom"


@dataclass
class RetryState:
    """State information for retry operations"""
    attempt: int
    total_attempts: int
    last_exception: Optional[Exception]
    elapsed_time: float
    backoff_time: float


class RetryStrategy(ABC):
    """Abstract base class for retry strategies"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    @abstractmethod
    def should_retry(self, state: RetryState, exception: Exception) -> bool:
        """Determine if operation should be retried"""
        pass
    
    @abstractmethod
    def calculate_delay(self, state: RetryState) -> float:
        """Calculate delay before next retry attempt"""
        pass
    
    def add_jitter(self, delay: float) -> float:
        """Add jitter to delay to avoid thundering herd"""
        if not self.jitter:
            return delay
        
        # Add ±20% jitter
        jitter_range = delay * 0.2
        return delay + random.uniform(-jitter_range, jitter_range)


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy with jitter"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        retry_conditions: Optional[list] = None
    ):
        super().__init__(max_attempts, base_delay, max_delay, jitter)
        self.multiplier = multiplier
        self.retry_conditions = retry_conditions or [
            RetryCondition.ON_SERVER_ERROR,
            RetryCondition.ON_TIMEOUT,
            RetryCondition.ON_NETWORK_ERROR
        ]
    
    def should_retry(self, state: RetryState, exception: Exception) -> bool:
        """Check if exception meets retry conditions"""
        if state.attempt >= self.max_attempts:
            return False
        
        # Check specific retry conditions
        for condition in self.retry_conditions:
            if self._matches_condition(condition, exception):
                return True
        
        return False
    
    def _matches_condition(self, condition: RetryCondition, exception: Exception) -> bool:
        """Check if exception matches retry condition"""
        if condition == RetryCondition.ALWAYS:
            return True
        elif condition == RetryCondition.NEVER:
            return False
        elif condition == RetryCondition.ON_SERVER_ERROR:
            return isinstance(exception, APIServerError) and exception.is_retryable
        elif condition == RetryCondition.ON_TIMEOUT:
            return isinstance(exception, APITimeoutError)
        elif condition == RetryCondition.ON_RATE_LIMIT:
            return isinstance(exception, APIRateLimitError)
        elif condition == RetryCondition.ON_NETWORK_ERROR:
            return isinstance(exception, NetworkError)
        
        return False
    
    def calculate_delay(self, state: RetryState) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_delay * (self.multiplier ** (state.attempt - 1))
        delay = min(delay, self.max_delay)
        return self.add_jitter(delay)


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        increment: float = 1.0,
        jitter: bool = True
    ):
        super().__init__(max_attempts, base_delay, max_delay, jitter)
        self.increment = increment
    
    def should_retry(self, state: RetryState, exception: Exception) -> bool:
        """Always retry until max attempts (for testing)"""
        return state.attempt < self.max_attempts
    
    def calculate_delay(self, state: RetryState) -> float:
        """Calculate linear backoff delay"""
        delay = self.base_delay + (self.increment * (state.attempt - 1))
        delay = min(delay, self.max_delay)
        return self.add_jitter(delay)


class AdaptiveRetryStrategy(RetryStrategy):
    """Adaptive retry strategy that adjusts based on error patterns"""
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 120.0,
        jitter: bool = True
    ):
        super().__init__(max_attempts, base_delay, max_delay, jitter)
        self.success_rate_window = 10
        self.recent_results = []  # Track recent success/failure
    
    def should_retry(self, state: RetryState, exception: Exception) -> bool:
        """Adaptive retry based on recent success rate and exception type"""
        if state.attempt >= self.max_attempts:
            return False
        
        # Always retry on specific exceptions
        if isinstance(exception, (APIServerError, NetworkError, APITimeoutError)):
            return True
        
        # For rate limiting, use adaptive backoff
        if isinstance(exception, APIRateLimitError):
            return state.attempt < 2  # Limited retries for rate limits
        
        return False
    
    def calculate_delay(self, state: RetryState) -> float:
        """Calculate adaptive delay based on error type and history"""
        base_delay = self.base_delay
        
        # Longer delays for rate limiting
        if isinstance(state.last_exception, APIRateLimitError):
            if hasattr(state.last_exception, 'retry_after') and state.last_exception.retry_after:
                base_delay = max(state.last_exception.retry_after, base_delay)
            else:
                base_delay = base_delay * 5  # Conservative rate limit backoff
        
        # Exponential backoff for other errors
        delay = base_delay * (2 ** (state.attempt - 1))
        delay = min(delay, self.max_delay)
        
        return self.add_jitter(delay)
    
    def record_result(self, success: bool):
        """Record operation result for adaptive behavior"""
        self.recent_results.append(success)
        if len(self.recent_results) > self.success_rate_window:
            self.recent_results.pop(0)


class RetryExecutor:
    """Executes operations with retry logic"""
    
    def __init__(self, strategy: RetryStrategy):
        self.strategy = strategy
    
    def execute_sync(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation"
    ) -> Any:
        """Execute operation with synchronous retry logic"""
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, self.strategy.max_attempts + 1):
            try:
                result = operation()
                
                # Record success if strategy supports it
                if hasattr(self.strategy, 'record_result'):
                    self.strategy.record_result(True)
                
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                elapsed_time = time.time() - start_time
                
                state = RetryState(
                    attempt=attempt,
                    total_attempts=self.strategy.max_attempts,
                    last_exception=e,
                    elapsed_time=elapsed_time,
                    backoff_time=0
                )
                
                if not self.strategy.should_retry(state, e):
                    logger.error(f"{operation_name} failed permanently on attempt {attempt}: {e}")
                    break
                
                if attempt < self.strategy.max_attempts:
                    delay = self.strategy.calculate_delay(state)
                    logger.warning(
                        f"{operation_name} failed on attempt {attempt}, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
        
        # Record failure if strategy supports it
        if hasattr(self.strategy, 'record_result'):
            self.strategy.record_result(False)
        
        # Re-raise the last exception
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"{operation_name} failed without exception")
    
    async def execute_async(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation"
    ) -> Any:
        """Execute operation with asynchronous retry logic"""
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, self.strategy.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                
                # Record success if strategy supports it
                if hasattr(self.strategy, 'record_result'):
                    self.strategy.record_result(True)
                
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                elapsed_time = time.time() - start_time
                
                state = RetryState(
                    attempt=attempt,
                    total_attempts=self.strategy.max_attempts,
                    last_exception=e,
                    elapsed_time=elapsed_time,
                    backoff_time=0
                )
                
                if not self.strategy.should_retry(state, e):
                    logger.error(f"{operation_name} failed permanently on attempt {attempt}: {e}")
                    break
                
                if attempt < self.strategy.max_attempts:
                    delay = self.strategy.calculate_delay(state)
                    logger.warning(
                        f"{operation_name} failed on attempt {attempt}, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
        
        # Record failure if strategy supports it
        if hasattr(self.strategy, 'record_result'):
            self.strategy.record_result(False)
        
        # Re-raise the last exception
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"{operation_name} failed without exception")


# Convenience functions for common retry strategies
def exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0
) -> ExponentialBackoffStrategy:
    """Create exponential backoff strategy with common defaults"""
    return ExponentialBackoffStrategy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier
    )


def aggressive_retry() -> AdaptiveRetryStrategy:
    """Create aggressive retry strategy for unreliable services"""
    return AdaptiveRetryStrategy(
        max_attempts=5,
        base_delay=0.5,
        max_delay=30.0
    )


def conservative_retry() -> ExponentialBackoffStrategy:
    """Create conservative retry strategy for stable services"""
    return ExponentialBackoffStrategy(
        max_attempts=2,
        base_delay=2.0,
        max_delay=10.0,
        retry_conditions=[RetryCondition.ON_SERVER_ERROR]
    )