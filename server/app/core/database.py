"""Database connection and Beanie ODM initialization for MongoDB."""

import logging
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.documents import ALL_MODELS

logger = logging.getLogger("uvicorn")

# Patch Motor 3.4+ missing append_metadata compatibility with Beanie
if not hasattr(AsyncIOMotorClient, "append_metadata"):
    AsyncIOMotorClient.append_metadata = lambda *args, **kwargs: None

# Global client reference
mongo_client: Optional[Any] = None


async def init_db(client: Optional[Any] = None, db_name: Optional[str] = None) -> None:
    """Initializes MongoDB connection and registers all Beanie Document models."""
    global mongo_client
    
    database_name = db_name or settings.MONGODB_DB_NAME

    if client is not None:
        mongo_client = client
        database = mongo_client[database_name]
        await init_beanie(database=database, document_models=ALL_MODELS)
        return

    # Attempt connecting to configured MongoDB URL
    try:
        candidate_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000,
        )
        # Verify connectivity with a quick ping
        await candidate_client.admin.command("ping")
        mongo_client = candidate_client
        database = mongo_client[database_name]
        await init_beanie(database=database, document_models=ALL_MODELS)
        logger.info(f"[DB] Successfully connected to live MongoDB database '{database_name}'.")
    except Exception as exc:
        logger.warning(
            f"[DB] Live MongoDB unreachable at '{settings.MONGODB_URL}' ({exc}). "
            "Falling back to in-memory mock client (mongomock_motor) with initial seeds."
        )
        try:
            import mongomock
            from mongomock_motor import AsyncMongoMockClient

            # Patch mongomock list_collection_names for Beanie 1.25+ compatibility
            _orig_list_colls = mongomock.database.Database.list_collection_names
            def _patched_list_colls(self, *args, **kwargs):
                valid_kwargs = {}
                if "filter" in kwargs:
                    valid_kwargs["filter"] = kwargs["filter"]
                return _orig_list_colls(self, *args, **valid_kwargs)
            mongomock.database.Database.list_collection_names = _patched_list_colls

            mongo_client = AsyncMongoMockClient()
            database = mongo_client[database_name]
            await init_beanie(database=database, document_models=ALL_MODELS)
            
            # Seed foundational demo users and rules in memory
            from app.core.seed import seed_database
            await seed_database()
            logger.info("[DB] In-memory database initialized and seeded successfully.")
        except Exception as mock_exc:
            logger.error(f"[DB] Failed to initialize mock MongoDB fallback: {mock_exc}")
            raise exc


async def close_db() -> None:
    """Closes the MongoDB client connection."""
    global mongo_client
    if mongo_client:
        try:
            mongo_client.close()
        except Exception:
            pass
        mongo_client = None

