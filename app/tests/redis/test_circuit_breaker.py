"""
Tests for the circuit breaker implementation.
"""

import asyncio
import pytest
import time
from app.libs.redis.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker instance for testing."""
    return CircuitBreaker(failure_threshold=3, reset_timeout=1)


@pytest.mark.asyncio
async def test_circuit_breaker_initial_state(circuit_breaker):
    """Test that circuit breaker starts in closed state."""
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    assert await circuit_breaker.is_allowed() is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold(circuit_breaker):
    """Test that circuit breaker opens after threshold failures."""
    # Record failures up to threshold
    for _ in range(3):
        await circuit_breaker.record_failure()
    
    # Circuit should be open now
    assert circuit_breaker.state == CircuitState.OPEN
    assert await circuit_breaker.is_allowed() is False


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout(circuit_breaker):
    """Test that circuit breaker transitions to half-open after timeout."""
    # Open the circuit
    for _ in range(3):
        await circuit_breaker.record_failure()
    
    assert circuit_breaker.state == CircuitState.OPEN
    
    # Wait for reset timeout
    await asyncio.sleep(1.1)
    
    # Should be allowed (half-open now)
    assert await circuit_breaker.is_allowed() is True
    assert circuit_breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_success(circuit_breaker):
    """Test that circuit breaker closes after successful operation in half-open state."""
    # Open the circuit
    for _ in range(3):
        await circuit_breaker.record_failure()
    
    # Wait for reset timeout and transition to half-open
    await asyncio.sleep(1.1)
    await circuit_breaker.is_allowed()
    
    # Record success, which should close the circuit
    await circuit_breaker.record_success()
    
    assert circuit_breaker.state == CircuitState.CLOSED
    assert await circuit_breaker.is_allowed() is True
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_reopens_on_failure_in_half_open(circuit_breaker):
    """Test that circuit breaker reopens on failure in half-open state."""
    # Open the circuit
    for _ in range(3):
        await circuit_breaker.record_failure()
    
    # Wait for reset timeout and transition to half-open
    await asyncio.sleep(1.1)
    await circuit_breaker.is_allowed()
    
    # Record failure, which should reopen the circuit
    await circuit_breaker.record_failure()
    
    assert circuit_breaker.state == CircuitState.OPEN
    assert await circuit_breaker.is_allowed() is False


@pytest.mark.asyncio
async def test_circuit_breaker_success_in_closed_state(circuit_breaker):
    """Test that success in closed state resets failure count."""
    # Record some failures, but not enough to open
    await circuit_breaker.record_failure()
    await circuit_breaker.record_failure()
    
    assert circuit_breaker.failure_count == 2
    
    # Record success
    await circuit_breaker.record_success()
    
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0