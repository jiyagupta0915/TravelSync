"""
TravelSync API - FastAPI entrypoint.

Run with: uvicorn app.main:app --host 127.0.0.1 --port 5001 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_settings
from app.core.csrf import csrf_origin_middleware
from app.core.error_handlers import register_error_handlers
from app.database import close_mongo_connection, connect_to_mongo
from app.routers import (
    auth, bookings, destinations, groups, meta, notifications, packing, places, recommend, stays,
    travel_health, trip_manage, trips, users,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="TravelSync API",
    lifespan=lifespan,
    # The interactive docs are handy locally but are not exposed in production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    if request.url.path.startswith(("/api/auth", "/api/users")):
        response.headers["Cache-Control"] = "no-store"
    return response


# Middleware order: the last one added is the outermost. CORS must wrap CSRF so that even a
# blocked request still carries the CORS headers the browser needs to read the error.
app.middleware("http")(csrf_origin_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

register_error_handlers(app)

app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(destinations.router)
app.include_router(recommend.router)
app.include_router(trips.router)
app.include_router(trip_manage.router)
app.include_router(packing.router)
app.include_router(travel_health.router)
app.include_router(places.router)
app.include_router(stays.router)
app.include_router(groups.router)
app.include_router(bookings.router)
app.include_router(notifications.router)
