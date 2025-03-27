"""
Redis serialization utilities.

This module provides serialization and deserialization functions for Redis cache
data. It handles standard Python types and provides special handling for common
complex types like datetime, UUID, etc.
"""

import json
import uuid
import datetime
from decimal import Decimal
from typing import Any, Dict, Union

from app.libs.redis.errors import RedisSerializationError


class RedisSerializer:
    """
    Serializer for Redis cache data.
    
    This class provides methods to serialize Python objects to JSON for Redis storage
    and deserialize JSON from Redis back to Python objects.
    """
    
    @staticmethod
    def serialize(data: Dict[str, Any]) -> str:
        """
        Serialize data to JSON string.
        
        Args:
            data: Dictionary to serialize
            
        Returns:
            JSON string representation
            
        Raises:
            RedisSerializationError: If serialization fails
        """
        try:
            return json.dumps(data, default=RedisSerializer._default_serializer)
        except Exception as e:
            raise RedisSerializationError(f"Failed to serialize data: {str(e)}")
    
    @staticmethod
    def deserialize(data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Deserialize JSON string to Python object.
        
        Args:
            data: JSON string or bytes to deserialize
            
        Returns:
            Deserialized Python dictionary
            
        Raises:
            RedisSerializationError: If deserialization fails
        """
        try:
            # Handle bytes input
            if isinstance(data, bytes):
                data = data.decode('utf-8')
                
            return json.loads(data)
        except Exception as e:
            raise RedisSerializationError(f"Failed to deserialize data: {str(e)}")
    
    @staticmethod
    def _default_serializer(obj: Any) -> Any:
        """
        Handle special types during serialization.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serializable representation of the object
            
        Raises:
            TypeError: If the object type is not supported
        """
        # Handle datetime
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
            
        # Handle UUID
        if isinstance(obj, uuid.UUID):
            return str(obj)
            
        # Handle Decimal
        if isinstance(obj, Decimal):
            return float(obj)
            
        # Handle sets
        if isinstance(obj, set):
            return list(obj)
            
        # Handle bytes
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
            
        raise TypeError(f"Type {type(obj).__name__} not serializable")