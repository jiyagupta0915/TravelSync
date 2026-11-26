"""
Start the TravelSync backend on port 5001 with a throw-away in-memory database
(mongomock-motor from requirements-dev.txt), so benchmarks can run without
MongoDB. All data is lost when the server stops.

Run from the backend folder:
    python evaluation/run_server_inmemory.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import app.database as database_module  # noqa: E402
import app.main as main_module  # noqa: E402


async def connect_in_memory():
    database_module.database.client = AsyncMongoMockClient()
    database_module.database.db = database_module.database.client["travelsync"]
    await database_module.ensure_indexes()


database_module.connect_to_mongo = connect_in_memory
main_module.connect_to_mongo = connect_in_memory

if __name__ == "__main__":
    uvicorn.run(main_module.app, host="127.0.0.1", port=5001)
