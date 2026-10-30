"""
MongoDB connection lifecycle, built on Motor (the async PyMongo driver).

Motor connects lazily. At startup we try to create the indexes; if MongoDB is unreachable
the app still boots and a background task keeps retrying until the indexes exist, so a
database that was down at boot time never leaves the app permanently without its unique
indexes. Requests made while the database is down fail with a clean 503 (see error_handlers).

Index creation is idempotent and non-destructive. If an index cannot be built (for example a
unique index over data that already contains duplicates) we log what to fix and carry on;
we never delete or rewrite user data to make an index build.
"""

import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.config import settings

logger = logging.getLogger("travelsync.database")


class DatabaseUnavailable(Exception):
    """Raised when the database client has not been initialised."""


class _Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None
    indexes_ready: bool = False
    index_task: asyncio.Task | None = None


database = _Database()


# (collection, keys, options). One place so docs/README and tests can list them.
INDEXES: list[tuple[str, list[tuple[str, int]], dict]] = [
    ("users", [("email", 1)], {"unique": True}),
    ("trips", [("user_id", 1), ("created_at", -1)], {}),
    ("packing_lists", [("trip_id", 1)], {"unique": True}),
    ("stay_cache", [("fetched_at", 1)], {"expireAfterSeconds": 7 * 24 * 60 * 60}),
    ("saved_stays", [("trip_id", 1), ("stay_key", 1)], {"unique": True}),
    ("password_resets", [("token_hash", 1)], {"unique": True}),
    ("password_resets", [("expires_at", 1)], {"expireAfterSeconds": 0}),
    ("groups", [("invite_code", 1)], {"unique": True}),
    ("groups", [("member_ids", 1), ("created_at", -1)], {}),
    ("group_suggestions", [("group_id", 1), ("created_at", -1)], {}),
    ("group_suggestions", [("group_id", 1), ("destination_key", 1)], {"unique": True}),
    ("group_messages", [("group_id", 1), ("created_at", 1)], {}),
    ("group_votes", [("group_id", 1), ("user_id", 1)], {"unique": True}),
    ("bookings", [("user_id", 1), ("trip_id", 1), ("created_at", -1)], {}),
    ("notifications", [("user_id", 1), ("created_at", -1)], {}),
]


async def ensure_indexes() -> bool:
    """Creates every index. Returns True when all of them exist."""
    if database.db is None:
        return False
    ok = True
    for collection, keys, options in INDEXES:
        try:
            await database.db[collection].create_index(keys, **options)
        except DuplicateKeyError:
            ok = False
            logger.error("Cannot build unique index on %s%s: existing duplicate data. Resolve the duplicates "
                         "manually (see README 'Database indexes'); no data was changed.", collection, keys)
        except PyMongoError as exc:
            ok = False
            logger.warning("Could not create index on %s%s: %s", collection, keys, type(exc).__name__)
    database.indexes_ready = ok
    return ok


async def _retry_indexes(delay_seconds: float = 5.0, max_delay: float = 60.0) -> None:
    while not await ensure_indexes():
        await asyncio.sleep(delay_seconds)
        delay_seconds = min(delay_seconds * 2, max_delay)


async def connect_to_mongo() -> None:
    database.client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    database.db = database.client[settings.mongodb_db]
    if not await ensure_indexes():
        database.index_task = asyncio.create_task(_retry_indexes())


async def close_mongo_connection() -> None:
    if database.index_task is not None:
        database.index_task.cancel()
        database.index_task = None
    if database.client is not None:
        database.client.close()


def get_db() -> AsyncIOMotorDatabase:
    if database.db is None:
        raise DatabaseUnavailable("Database has not been initialised.")
    return database.db


async def database_status() -> tuple[bool, str | None]:
    try:
        if database.client is None:
            return False, None
        await database.client.admin.command("ping")
        return True, settings.mongodb_db
    except PyMongoError:
        return False, None
