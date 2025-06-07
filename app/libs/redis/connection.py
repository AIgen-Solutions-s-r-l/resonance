"""
Redis connection manager.

This module provides a connection manager for Redis that handles connection
pooling, health checks, and automatic reconnection.
"""

import asyncio
import time
from typing import Optional, Any, Dict
from app.log.logging import logger

import redis.asyncio as redis
from redis.exceptions import RedisError as RedisBaseError

from app.core.config import settings
from app.libs.redis.circuit_breaker import CircuitBreaker
from app.libs.redis.errors import (
    RedisConnectionError,
    RedisCircuitBreakerOpenError
)


class RedisConnectionManager:
    """
    Redis connection manager.
    
    This class manages Redis connections, including connection pooling,
    health checks, and automatic reconnection.
    """
    
    def __init__(
        self,
        host: str = settings.redis_host,
        port: int = settings.redis_port,
        db: int = settings.redis_db,
        password: Optional[str] = settings.redis_password,
        max_connections: int = 10,
        connection_timeout: float = 2.0,
        health_check_interval: int = 30,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize the Redis connection manager.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password (if required)
            max_connections: Maximum number of connections in the pool
            connection_timeout: Connection timeout in seconds
            health_check_interval: Health check interval in seconds
            circuit_breaker: Circuit breaker instance (created if not provided)
        """
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._max_connections = max_connections
        self._connection_timeout = connection_timeout
        self._health_check_interval = health_check_interval
        
        # Initialize circuit breaker if not provided
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        
        # Connection state
        self._client: Optional[redis.Redis] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Redis connection manager initialized for "
            f"{host}:{port}/{db} with {max_connections} max connections"
        )
    
    async def initialize(self) -> bool:
        """
        Initialize the Redis connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create Redis client
            self._client = await self._create_redis_client()
            
            # Test connection
            await self._client.ping()
            
            # Start health check task
            self._start_health_check()
            
            logger.info("Redis connection initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")
            self._client = None
            return False
    
    async def get_redis(self) -> redis.Redis:
        """
        Get the Redis client.
        
        Returns:
            Redis client
            
        Raises:
            RedisCircuitBreakerOpenError: If circuit breaker is open
            Exception: If Redis client is not initialized
        """
        # Check if Redis is initialized
        if self._client is None:
            raise ValueError("Redis client not initialized")
        
        # Check if circuit breaker allows operation
        if not await self._circuit_breaker.is_allowed():
            raise RedisCircuitBreakerOpenError("Circuit breaker is open")
        
        return self._client
    
    async def close(self) -> None:
        """Close the Redis connection."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
    
    def _start_health_check(self) -> None:
        """Start the health check task."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.debug("Redis health check task started")
    
    async def _health_check_loop(self) -> None:
        """Perform periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._client:
                    # Perform ping to check health
                    await self._client.ping()
                    
                    # Record success
                    await self._circuit_breaker.record_success()
                    logger.debug("Redis health check successful")
                    
            except asyncio.CancelledError:
                # Task was cancelled
                logger.debug("Redis health check task cancelled")
                break
                
            except Exception as e:
                logger.error(f"Redis health check failed: {str(e)}")
                
                # Record failure in circuit breaker
                await self._circuit_breaker.record_failure()
                
                # Attempt reconnection
                success = await self._try_reconnect()
                if success:
                    logger.info("Redis reconnection successful")
                else:
                    logger.error("Redis reconnection failed")
    
    async def _try_reconnect(self) -> bool:
        """
        Try to reconnect to Redis.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        try:
            # Close existing client if any
            if self._client:
                await self._client.close()
            
            # Create new client
            self._client = await self._create_redis_client()
            
            # Test connection
            await self._client.ping()
            
            logger.info("Successfully reconnected to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reconnect to Redis: {str(e)}")
            self._client = None
            
            # Record failure in circuit breaker
            await self._circuit_breaker.record_failure()
            
            return False
    
    async def _create_redis_client(self) -> redis.Redis:
        """
        Create a new Redis client.
        
        Returns:
            Redis client
            
        Raises:
            RedisConnectionError: If connection fails
        """
        try:
            # Create connection URL
            redis_url = f"redis://"
            
            # Add password if provided
            if self._password:
                redis_url += f":{self._password}@"
                
            # Add host, port, and database
            redis_url += f"{self._host}:{self._port}/{self._db}"
            
            # Create Redis client with connection pooling
            client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self._max_connections,
                socket_timeout=self._connection_timeout,
                socket_connect_timeout=self._connection_timeout,
                health_check_interval=self._health_check_interval
            )
            
            return client
            
        except Exception as e:
            logger.error(f"Error creating Redis client: {str(e)}")
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")