"""
Checks that the backend can reach the database named in backend/.env, without starting the API.

    cd backend && python -m scripts.check_db

Prints only the host and database name (never the username, password or full URI).
Creates the app's indexes (idempotent, non-destructive) and reports the user count.
"""

import asyncio
import sys
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.database import INDEXES


async def main() -> int:
    host = urlparse(settings.mongodb_uri).hostname or "(unparseable URI)"
    print(f"Connecting to {host}, database '{settings.mongodb_db}' ...")
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=8000)
    try:
        await client.admin.command("ping")
        db = client[settings.mongodb_db]
        for collection, keys, options in INDEXES:
            await db[collection].create_index(keys, **options)
        users = await db.users.count_documents({})
        print(f"OK: connected, {len(INDEXES)} indexes ensured, {users} user(s) in 'users'.")
        return 0
    except Exception as exc:  # report the type only; driver messages can contain host details
        print(f"FAILED: {type(exc).__name__}. Check your IP allow-list, username/password and URI.")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))