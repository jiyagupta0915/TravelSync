"""
Test harness. MongoDB is replaced by mongomock-motor (an in-memory, API-compatible fake), so these tests
need no running database. They exercise the real FastAPI app through an ASGI client; only the database and
outbound HTTP/SMTP are faked.
"""

import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-1234567890")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

from app import database as db_module
from app.config import settings
from app.database import ensure_indexes
from app.main import app
from app.routers import auth as auth_router

ORIGIN = "http://localhost:5173"
GOOD_PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture(autouse=True)
async def fake_db():
    client = AsyncMongoMockClient()
    db_module.database.client = client
    db_module.database.db = client["travelsync_test"]
    await ensure_indexes()
    auth_router.login_limiter.clear()
    auth_router.recovery_limiter.clear()
    yield db_module.database.db
    db_module.database.db = None
    db_module.database.client = None


def make_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", headers={"Origin": ORIGIN})


@pytest.fixture
async def client():
    async with make_client() as c:
        yield c


@pytest.fixture
async def client_b():
    async with make_client() as c:
        yield c


async def signup(c: httpx.AsyncClient, email="alice@example.com", name="Alice Traveller", password=GOOD_PASSWORD):
    r = await c.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["user"]


@pytest.fixture
async def alice(client):
    return await signup(client, "alice@example.com", "Alice Traveller")


@pytest.fixture
async def bob(client_b):
    return await signup(client_b, "bob@example.com", "Bob Wanderer")


async def create_trip(c: httpx.AsyncClient, destination="Goa", **extra):
    r = await c.post("/api/trips", json={"destination": destination, "duration": 4, "budget": 20000, **extra})
    assert r.status_code == 201, r.text
    return r.json()["trip"]


@pytest.fixture
def smtp_configured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "noreply@travelsync.test")
    sent = []

    async def fake_send(to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})

    from app.routers import auth as auth_module
    monkeypatch.setattr(auth_module, "send_email", fake_send)
    return sent


@pytest.fixture
def external_http(monkeypatch):
    """Intercepts ONLY outbound calls to third-party hosts (Geoapify, Open-Meteo); the ASGI test client is untouched."""
    original = httpx.AsyncClient.get
    state = {"handler": None}

    async def patched(self, url, *args, **kwargs):
        if str(url).startswith("https://") and state["handler"] is not None:
            return await state["handler"](self, str(url), kwargs.get("params"))
        return await original(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "get", patched)

    def install(handler):
        state["handler"] = handler

    return install
