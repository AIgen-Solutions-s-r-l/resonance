from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.log.logging import logger


try:
    logger.info(
        "Initializing MongoDB connection",
        event_type="mongodb_init",
        mongodb_uri=settings.mongodb,
        mongodb_database=settings.mongodb_database,
    )

    client = AsyncIOMotorClient(settings.mongodb, serverSelectionTimeoutMS=5000)

    database = client[settings.mongodb_database]
    collection_name = database.get_collection("resumes")

    user_collection = database.get_collection("user_operations")

    client.admin.command("ping")
    logger.info(
        "MongoDB connection established",
        event_type="mongodb_connected",
        mongodb_uri=settings.mongodb,
        database=settings.mongodb_database,
    )

except Exception as e:
    logger.error(
        "MongoDB connection failed",
        event_type="mongodb_error",
        error_type=type(e).__name__,
        error_details=str(e),
    )
    raise
