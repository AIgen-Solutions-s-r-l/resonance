"""
Tests for the Redis serialization module.
"""

import pytest
import uuid
import datetime
from decimal import Decimal
from app.libs.redis.serialization import RedisSerializer
from app.libs.redis.errors import RedisSerializationError


class TestRedisSerializer:
    """Test suite for the RedisSerializer class."""

    def test_serialize_basic_types(self):
        """Test serializing basic Python types."""
        # Test with various basic types
        data = {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        # Serialize
        serialized = RedisSerializer.serialize(data)
        
        # Verify it's a string (JSON)
        assert isinstance(serialized, str)
        
        # Deserialize and verify
        deserialized = RedisSerializer.deserialize(serialized)
        assert deserialized == data

    def test_serialize_complex_types(self):
        """Test serializing complex Python types that require special handling."""
        # Create test data with complex types
        now = datetime.datetime.now()
        today = datetime.date.today()
        unique_id = uuid.uuid4()
        decimal_value = Decimal("3.14159265359")
        
        data = {
            "datetime": now,
            "date": today,
            "uuid": unique_id,
            "decimal": decimal_value
        }
        
        # Serialize
        serialized = RedisSerializer.serialize(data)
        
        # Deserialize and verify
        deserialized = RedisSerializer.deserialize(serialized)
        
        # Check types and values
        assert isinstance(deserialized["datetime"], str)
        assert isinstance(deserialized["date"], str)
        assert isinstance(deserialized["uuid"], str)
        assert isinstance(deserialized["decimal"], float)
        
        # Verify values are preserved (with appropriate conversions)
        assert deserialized["datetime"] == now.isoformat()
        assert deserialized["date"] == today.isoformat()
        assert deserialized["uuid"] == str(unique_id)
        assert deserialized["decimal"] == float(decimal_value)

    def test_serialize_nested_complex_types(self):
        """Test serializing nested structures with complex types."""
        now = datetime.datetime.now()
        unique_id = uuid.uuid4()
        
        data = {
            "user": {
                "id": unique_id,
                "created_at": now,
                "profile": {
                    "preferences": {
                        "theme": "dark",
                        "notifications": [
                            {"type": "email", "enabled": True},
                            {"type": "push", "enabled": False}
                        ]
                    }
                }
            }
        }
        
        # Serialize
        serialized = RedisSerializer.serialize(data)
        
        # Deserialize and verify
        deserialized = RedisSerializer.deserialize(serialized)
        
        # Check structure is preserved
        assert "user" in deserialized
        assert "profile" in deserialized["user"]
        assert "preferences" in deserialized["user"]["profile"]
        assert "notifications" in deserialized["user"]["profile"]["preferences"]
        
        # Check complex types
        assert deserialized["user"]["id"] == str(unique_id)
        assert deserialized["user"]["created_at"] == now.isoformat()

    def test_serialize_error_handling(self):
        """Test error handling for non-serializable objects."""
        # Create a non-serializable object (a function)
        data = {
            "function": lambda x: x * 2
        }
        
        # Attempt to serialize should raise error
        with pytest.raises(RedisSerializationError):
            RedisSerializer.serialize(data)

    def test_deserialize_error_handling(self):
        """Test error handling for invalid JSON during deserialization."""
        # Invalid JSON string
        invalid_json = '{"key": "value", invalid}'
        
        # Attempt to deserialize should raise error
        with pytest.raises(RedisSerializationError):
            RedisSerializer.deserialize(invalid_json)

    def test_deserialize_type_handling(self):
        """Test deserialization with different input types."""
        # Test with string
        json_str = '{"key": "value"}'
        result = RedisSerializer.deserialize(json_str)
        assert result == {"key": "value"}
        
        # Test with bytes
        json_bytes = b'{"key": "value"}'
        result = RedisSerializer.deserialize(json_bytes)
        assert result == {"key": "value"}