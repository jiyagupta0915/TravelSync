"""
TravelSync API - FastAPI entrypoint.

Run with: uvicorn app.main:app --host 127.0.0.1 --port 5001 --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.error_handlers import register_error_handlers
from app.database import close_mongo_connection, connect_to_mongo
from app.routers import auth, destinations, meta, recommend, trips, packing, travel_health
from app.routers import places, stays

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(title="TravelSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(destinations.router)
app.include_router(recommend.router)
app.include_router(trips.router)
app.include_router(packing.router)
app.include_router(travel_health.router)
app.include_router(places.router)
app.include_router(stays.router)