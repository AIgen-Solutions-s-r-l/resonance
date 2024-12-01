# app/core/mongodb.py

from typing import Optional, Any
from dataclasses import dataclass
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from loguru import logger

from app.core.config import Settings
from app.core.logging_config import get_logger_context


@dataclass
class MongoConfig:
	"""Configuration for MongoDB connection."""
	uri: str
	database: str
	timeout_ms: int = 5000


class MongoDBError(Exception):
	"""Base exception for MongoDB-related errors."""

	def __init__(self, message: str, context: dict[str, Any]) -> None:
		self.context = context
		super().__init__(message)


class MongoDBConnectionError(MongoDBError):
	"""Raised when MongoDB connection fails."""
	pass


class MongoDBClientWrapper:
	"""Wrapper for MongoDB client with async support."""

	def __init__(self, config: MongoConfig) -> None:
		"""
        Initialize MongoDB client wrapper.

        Args:
            config: MongoDB connection configuration
        """
		self.config = config
		self._client: Optional[AsyncIOMotorClient] = None
		self._db: Optional[AsyncIOMotorDatabase] = None
		self._collection: Optional[AsyncIOMotorCollection] = None

	async def initialize(self) -> None:
		"""
        Initialize MongoDB connection and verify it's working.

        Raises:
            MongoDBConnectionError: If connection fails
        """
		try:
			context = get_logger_context(
				action="mongodb_connect",
				host=self.config.uri.split("@")[-1],  # Safe way to log URI without credentials
				database=self.config.database
			)
			logger.info("Connecting to MongoDB", context)

			self._client = AsyncIOMotorClient(
				self.config.uri,
				serverSelectionTimeoutMS=self.config.timeout_ms
			)

			# Access the database
			self._db = self._client[self.config.database]

			# Get the collection
			self._collection = self._db.get_collection("resumes")

			# Verify connection
			await self._client.admin.command('ping')

			context["status"] = "connected"
			logger.success("Successfully connected to MongoDB", context)

		except Exception as e:
			context = get_logger_context(
				action="mongodb_connect",
				error=str(e),
				error_type=type(e).__name__
			)
			logger.error("Failed to connect to MongoDB", context)
			raise MongoDBConnectionError("Failed to connect to MongoDB", context) from e

	@property
	def client(self) -> AsyncIOMotorClient:
		"""Get MongoDB client instance."""
		if not self._client:
			raise MongoDBError(
				"MongoDB client not initialized",
				{"action": "get_client"}
			)
		return self._client

	@property
	def db(self) -> AsyncIOMotorDatabase:
		"""Get MongoDB database instance."""
		if not self._db:
			raise MongoDBError(
				"MongoDB database not initialized",
				{"action": "get_database"}
			)
		return self._db

	@property
	def collection(self) -> AsyncIOMotorCollection:
		"""Get MongoDB collection instance."""
		if not self._collection:
			raise MongoDBError(
				"MongoDB collection not initialized",
				{"action": "get_collection"}
			)
		return self._collection

	async def close(self) -> None:
		"""Close MongoDB connection."""
		if self._client:
			context = get_logger_context(action="mongodb_close")
			try:
				self._client.close()
				logger.info("MongoDB connection closed", context)
			except Exception as e:
				context["error"] = str(e)
				logger.error("Error closing MongoDB connection", context)


# Create singleton instance
def create_mongodb_client() -> MongoDBClientWrapper:
	"""
    Create MongoDB client instance with settings.

    Returns:
        Configured MongoDB client wrapper
    """
	settings = Settings()
	config = MongoConfig(
		uri=settings.mongodb_uri,
		database=settings.mongodb_database
	)
	return MongoDBClientWrapper(config)


mongodb = create_mongodb_client()

# Example usage:
# async def startup():
#     await mongodb.initialize()
#
# async def shutdown():
#     await mongodb.close()