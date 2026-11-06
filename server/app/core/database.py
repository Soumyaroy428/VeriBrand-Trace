"""Database connection and Beanie ODM initialization for MongoDB."""

from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.documents import ALL_MODELS

# Global client reference
mongo_client: Optional[AsyncIOMotorClient] = None


async def init_db(client: Optional[Any] = None, db_name: Optional[str] = None) -> None:
    """Initializes MongoDB connection and registers all Beanie Document models."""
    global mongo_client
    
    database_name = db_name or settings.MONGODB_DB_NAME

    if client is not None:
        mongo_client = client
    else:
        # Connect via configured connection string
        mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
        )

    database = mongo_client[database_name]
    await init_beanie(database=database, document_models=ALL_MODELS)


async def close_db() -> None:
    """Closes the MongoDB client connection."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        mongo_client = None
