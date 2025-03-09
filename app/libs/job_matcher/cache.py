"""
Caching mechanism for job matcher.

This module provides caching functionality for job matching results.
"""

import asyncio
from time import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger


class ResultsCache:
    """Cache for job matching results."""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            ttl: Cache TTL in seconds
            max_size: Maximum number of entries in cache
        """
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
        logger.info(f"Initialized job matcher cache with TTL={ttl}s, max_size={max_size}")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None if not found or expired
        """
        start_time = time()
        async with self._lock:
            if key in self._cache:
                results, timestamp = self._cache[key]
                # Check if cache entry has expired
                if time() - timestamp <= self._ttl:
                    logger.debug(f"Cache hit for key: {key}")
                    elapsed = time() - start_time
                    logger.debug(f"Cache retrieval took {elapsed:.6f}s")
                    return results
                
                # Cache entry has expired
                logger.debug(f"Cache entry expired for key: {key}")
                del self._cache[key]
        
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    async def set(self, key: str, results: Dict[str, Any]) -> None:
        """
        Store results in cache.
        
        Args:
            key: Cache key
            results: Results to cache
        """
        start_time = time()
        async with self._lock:
            self._cache[key] = (results, time())
            logger.debug(f"Stored results in cache with key: {key}")
            
            # Cleanup cache if it gets too large
            if len(self._cache) > self._max_size:
                logger.info(f"Cache cleanup triggered (size={len(self._cache)})")
                # Remove oldest entries
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
                to_remove = len(self._cache) // 2  # Remove half of the entries
                
                for k, _ in sorted_items[:to_remove]:
                    del self._cache[k]
                
                logger.info(f"Removed {to_remove} oldest cache entries")
        
        elapsed = time() - start_time
        logger.debug(f"Cache storage took {elapsed:.6f}s")
    
    async def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        key_parts = []
        
        # Add positional args
        for arg in args:
            if arg is not None:
                key_parts.append(str(arg))
        
        # Add keyword args
        for k, v in sorted(kwargs.items()):
            if v is not None:
                if isinstance(v, list):
                    v = sorted(v)
                key_parts.append(f"{k}_{v}")
        
        key = "_".join(str(part) for part in key_parts)
        logger.trace(f"Generated cache key: {key}")
        return key


# Singleton instance
cache = ResultsCache()