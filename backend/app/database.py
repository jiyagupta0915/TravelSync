"""
MongoDB connection lifecycle, built on Motor (the async PyMongo driver).

The client itself is created eagerly at startup but does not eagerly
open a socket - Motor connects lazily on first real operation. We do
attempt one index-creation call during startup as a connectivity probe;
if MongoDB is unreachable at boot time we log a warning and let the app
continue serving requests (each request re-attempts the connection and
fails gracefully with a 503, rather than crashing the whole process).
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger("travelsync.database")


class _Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


database = _Database()


async def connect_to_mongo() -> None:
    database.client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    database.db = database.client[settings.mongodb_db]
    try:
        await database.db.users.create_index("email", unique=True)
        await database.db.trips.create_index([("user_id", 1), ("created_at", -1)])
        await database.db.packing_lists.create_index("trip_id", unique=True)
    except PyMongoError as exc:
        logger.warning("Could not verify MongoDB indexes at startup: %s", exc)


async def close_mongo_connection() -> None:
    if database.client is not None:
        database.client.close()


def get_db() -> AsyncIOMotorDatabase:
    if database.db is None:
        raise RuntimeError("Database has not been initialised. Was startup skipped?")
    return database.db


async def database_status() -> tuple[bool, str | None]:
    try:
        if database.client is None:
            return False, None
        await database.client.admin.command("ping")
        return True, settings.mongodb_db
    except PyMongoError:
        return False, None
