"""
Circuit breaker implementation.

This module implements the circuit breaker pattern to prevent repeated failures
when Redis is unavailable. It automatically stops operation attempts after a
threshold of failures is reached, and allows retries after a timeout period.
"""

import asyncio
import enum
import time
from typing import Optional
from loguru import logger


class CircuitState(enum.Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failing state, requests are blocked
    HALF_OPEN = "half_open" # Testing state, single request allowed to test recovery


class CircuitBreaker:
    """
    Circuit breaker implementation.
    
    The circuit breaker prevents cascade failures by automatically stopping
    operation attempts after a threshold of failures. It will attempt recovery
    after a timeout period.
    """
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 30):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Seconds before trying to close the circuit again
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Circuit breaker initialized with failure_threshold={failure_threshold}, "
            f"reset_timeout={reset_timeout}s"
        )
    
    async def is_allowed(self) -> bool:
        """
        Check if the operation is allowed.
        
        Returns:
            True if the operation should be allowed, False if it should be blocked
        """
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                # Always allow when circuit is closed
                return True
                
            elif self.state == CircuitState.OPEN:
                # Check if reset timeout has elapsed
                if (self.last_failure_time is not None and 
                        time.time() - self.last_failure_time >= self.reset_timeout):
                    # Transition to half-open
                    logger.info(
                        f"Circuit breaker transitioning from OPEN to HALF_OPEN after "
                        f"{self.reset_timeout}s timeout"
                    )
                    self.state = CircuitState.HALF_OPEN
                    return True
                else:
                    # Still open
                    return False
                    
            elif self.state == CircuitState.HALF_OPEN:
                # Allow exactly one request to test if the system is back to normal
                return True
                
            # Should never get here, but just in case
            return False
    
    async def record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Successful test, circuit can close
                logger.info("Circuit breaker closed after successful test")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_failure_time = None
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
    
    async def record_failure(self) -> None:
        """Record a failed operation."""
        async with self._lock:
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Test failed, circuit reopens
                logger.warning("Circuit breaker reopened after failed test")
                self.state = CircuitState.OPEN
                
            elif self.state == CircuitState.CLOSED:
                # Increment failure count
                self.failure_count += 1
                
                # Check threshold
                if self.failure_count >= self.failure_threshold:
                    logger.warning(
                        f"Circuit breaker opened after {self.failure_count} failures"
                    )
                    self.state = CircuitState.OPEN