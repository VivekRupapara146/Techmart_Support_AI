"""
MongoDB connection, managed via FastAPI lifespan events.

The client is created ONCE at app startup and reused for the life of the
process — creating a new client per-request would exhaust the connection
pool under load.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    _db = _client[settings.mongo_db_name]
    # Fail fast if Mongo isn't reachable, rather than discovering it on first request
    await _client.admin.command("ping")
    logger.info(f"Connected to MongoDB database '{settings.mongo_db_name}'")


async def close_mongo_connection() -> None:
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized — connect_to_mongo() must run first")
    return _db


async def is_db_healthy() -> bool:
    try:
        if _client is None:
            return False
        await _client.admin.command("ping")
        return True
    except Exception:
        return False
