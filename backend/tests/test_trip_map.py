import httpx
import pytest

from app.config import settings
from app.core.rate_limit import FailureLimiter
from app.services import map_service
from tests.conftest import create_trip, make_client


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(map_service, "live_lookups", FailureLimiter(max_failures=20, window_seconds=3600))


@pytest.fixture
def matrix(monkeypatch):
    """Fakes Geoapify's Route Matrix. Records every request so tests can check what was (not) sent."""
    state = {"calls": [], "status": 200}
    original = httpx.AsyncClient.post

    async def fake_post(self, url, *args, **kwargs):
        if not str(url).startswith("https://"):   # the ASGI test client's own requests to our API pass through
            return await original(self, url, *args, **kwargs)
        state["calls"].append({"url": str(url), "params": kwargs.get("params"), "json": kwargs.get("json")})
        if state["status"] != 200:
            return httpx.Response(state["status"], text="nope", request=httpx.Request("POST", str(url)))
        n = len(kwargs["json"]["targets"])
        cells = [{"source_index": 0, "target_index": i, "distance": 12_000 + i * 1000, "time": 1500 + i * 60} for i in range(n)]
        cells[-1] = {"source_index": 0, "target_index": n - 1, "distance": None, "time": None}   # one place with no road route
        return httpx.Response(200, json={"sources_to_targets": [cells]}, request=httpx.Request("POST", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(settings, "geoapify_api_key", "SECRETKEY123")
    return state


async def test_map_returns_center_places_and_saved_stays(client, alice):
    trip = await create_trip(client, "Manali")
    r = await client.get(f"/api/trips/{trip['id']}/map")
    assert r.status_code == 200
    data = r.json()
    assert data["destination"] == "Manali"
    assert -90 < data["center"]["lat"] < 90 and -180 < data["center"]["lon"] < 180
    assert 1 <= len(data["places"]) <= 5
    assert [p["rank"] for p in data["places"]] == list(range(1, len(data["places"]) + 1))
    assert all({"name", "category", "lat", "lon"} <= set(p) for p in data["places"])
    assert any(p["lat"] is not None for p in data["places"])
    assert data["saved_stays"] == []


async def test_map_includes_saved_stays_with_coordinates(client, alice, fake_db):
    from bson import ObjectId
    trip = await create_trip(client, "Manali")
    stay = {"key": "abc12345abc12345", "name": "Hotel <b>X</b>", "type": "hotel", "type_label": "Hotel", "stars": 3,
            "address": "Mall Road", "lat": 32.24, "lon": 77.19, "price_low_inr": 1500, "price_high_inr": 2500,
            "price_unit": "room", "website": None, "maps_url": "https://maps.example/x", "secret_internal": "no"}
    bad = {**stay, "key": "bad00000bad00000", "lat": None}
    for s in (stay, bad):
        await fake_db.saved_stays.insert_one({"trip_id": ObjectId(trip["id"]), "stay_key": s["key"], "stay": s, "saved_at": 0})
    data = (await client.get(f"/api/trips/{trip['id']}/map")).json()
    assert [s["key"] for s in data["saved_stays"]] == ["abc12345abc12345"]   # the one without coordinates is skipped
    assert "secret_internal" not in data["saved_stays"][0]


async def test_map_is_private_and_needs_login(client, client_b, alice, bob):
    trip = await create_trip(client)
    assert (await client_b.get(f"/api/trips/{trip['id']}/map")).status_code == 404
    assert (await client.get("/api/trips/not-an-id/map")).status_code == 400
    async with make_client() as anon:
        assert (await anon.get(f"/api/trips/{trip['id']}/map")).status_code == 401
        assert (await anon.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})).status_code == 401


async def test_distances_are_computed_rounded_and_cached(client, alice, matrix):
    trip = await create_trip(client, "Manali")
    r = await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.61391, "lon": 77.20902})
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "geoapify"
    assert data["distances"]["destination"]["km"] == 12.0 and data["distances"]["destination"]["minutes"] == 25
    assert any(k.startswith("place:") for k in data["distances"])
    assert "SECRETKEY123" not in r.text

    # the user's exact position never leaves our server: Geoapify only gets the 2-decimal rounded point
    sent = matrix["calls"][0]
    assert sent["json"]["sources"] == [{"location": [77.21, 28.61]}] and sent["json"]["mode"] == "drive"

    # same ~1 km spot again: served from the cache, no second paid call (even from a tiny GPS wobble)
    again = await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6144, "lon": 77.2081})
    assert again.json()["source"] == "cache" and again.json()["distances"] == data["distances"]
    assert len(matrix["calls"]) == 1


async def test_a_target_without_a_road_route_is_simply_left_out(client, alice, matrix):
    trip = await create_trip(client, "Manali")
    data = (await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})).json()
    last_target = len(matrix["calls"][0]["json"]["targets"]) - 1
    ids = ["destination"] + [f"place:{i}" for i in range(1, 6)]
    assert ids[last_target] not in data["distances"] and len(data["distances"]) == last_target


@pytest.mark.parametrize("status,reason", [(500, "service_error"), (429, "daily_limit")])
async def test_geoapify_problems_fall_back_instead_of_failing(client, alice, matrix, status, reason):
    matrix["status"] = status
    trip = await create_trip(client, "Manali")
    r = await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})
    assert r.status_code == 200 and r.json() == {"source": "unavailable", "reason": reason, "distances": {}}
    # failures are never cached
    matrix["status"] = 200
    assert (await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})).json()["source"] == "geoapify"


async def test_distances_unavailable_without_api_key(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "geoapify_api_key", "")
    trip = await create_trip(client, "Manali")
    r = await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})
    assert r.status_code == 200 and r.json()["reason"] == "not_configured"


async def test_live_lookups_are_rate_limited_per_user(client, alice, matrix, monkeypatch):
    monkeypatch.setattr(map_service, "live_lookups", FailureLimiter(max_failures=2, window_seconds=3600))
    trip = await create_trip(client, "Manali")
    kinds = []
    for i in range(4):   # four different places, so none is a cache hit
        r = await client.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 20.0 + i, "lon": 77.0})
        kinds.append(r.json().get("reason") or r.json()["source"])
    assert kinds == ["geoapify", "geoapify", "rate_limited", "rate_limited"]
    assert len(matrix["calls"]) == 2


@pytest.mark.parametrize("body", [{"lat": 91, "lon": 77}, {"lat": 28, "lon": 181}, {"lat": "x", "lon": 77}, {"lat": 28}])
async def test_distances_validate_the_location(client, alice, matrix, body):
    trip = await create_trip(client, "Manali")
    assert (await client.post(f"/api/trips/{trip['id']}/map/distances", json=body)).status_code == 422
    assert matrix["calls"] == []


async def test_distances_are_private(client, client_b, alice, bob, matrix):
    trip = await create_trip(client)
    assert (await client_b.post(f"/api/trips/{trip['id']}/map/distances", json={"lat": 28.6, "lon": 77.2})).status_code == 404
    assert matrix["calls"] == []