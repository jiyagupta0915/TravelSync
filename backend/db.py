import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    db_name = os.getenv("MONGODB_DB", "travelsync")
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    _client.admin.command("ping")
    _db = _client[db_name]
    _db.users.create_index("email", unique=True)
    _db.trips.create_index([("user_id", 1), ("created_at", -1)])
    return _db


def database_status():
    try:
        db = get_db()
        db.command("ping")
        return True, db.name
    except PyMongoError:
        return False, None
