import httpx
import pytest

from app.config import settings
from tests.conftest import create_trip

VALID = {
    "preferences": {"Mountain": 1, "Beach": 0, "Nature": 1, "Adventure": 1, "Culture": 0, "Relaxation": 0, "Nightlife": 0,
                    "Spiritual": 0, "Trekking": 0, "Photography": 0, "Food": 0, "Heritage": 0},
    "importance": {"Mountain": 3, "Beach": 0, "Nature": 2, "Adventure": 3, "Culture": 0, "Relaxation": 0, "Nightlife": 0,
                   "Spiritual": 0, "Trekking": 0, "Photography": 0, "Food": 0, "Heritage": 0},
    "traveller_type": "Friends", "duration": 5, "budget": 20000, "start_lat": 28.61, "start_lon": 77.2,
    "max_distance_km": 2000, "top_n": 6,
}


async def test_recommend_happy_path_unchanged_contract(client):
    r = await client.post("/api/recommend", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["recommendations"]) and set(body["rules"]) == {"duration", "budget", "distance"}
    first = body["recommendations"][0]
    assert {"Destination", "State", "final_score", "distance_km", "estimated_trip_budget_inr"} <= set(first)
    scores = [x["final_score"] for x in body["recommendations"]]
    assert scores == sorted(scores, reverse=True)                      # ranking preserved


@pytest.mark.parametrize("patch", [
    {"duration": 0}, {"duration": 31}, {"budget": 0}, {"budget": -10}, {"budget": 10**10}, {"max_distance_km": 0},
    {"max_distance_km": 10001}, {"start_lat": 95}, {"start_lon": 200}, {"top_n": 0}, {"top_n": 11}, {"duration": "five"},
])
async def test_recommend_rejects_out_of_range_inputs(client, patch):
    r = await client.post("/api/recommend", json={**VALID, **patch})
    assert r.status_code == 422, (patch, r.text)


async def test_recommend_rejects_bad_preference_values_and_traveller(client):
    bad = {**VALID, "importance": {**VALID["importance"], "Mountain": 99}}
    assert (await client.post("/api/recommend", json=bad)).status_code == 422
    assert (await client.post("/api/recommend", json={**VALID, "traveller_type": "Alien"})).status_code == 400


async def test_recommend_requires_start_when_distance_given(client):
    body = {k: v for k, v in VALID.items() if k not in ("start_lat", "start_lon")}
    r = await client.post("/api/recommend", json=body)
    assert r.status_code == 400 and "Starting location" in r.json()["error"]


async def test_recommend_engine_failure_is_generic_500(client, monkeypatch):
    from app.routers import recommend as rec
    monkeypatch.setattr(rec, "recommend_destinations", lambda **k: (_ for _ in ()).throw(RuntimeError("/srv/secret/path")))
    r = await client.post("/api/recommend", json=VALID)
    assert r.status_code == 500 and "secret" not in r.text


# ------------------------------------------------------------------ stays: provider failures + honest labelling
async def test_stays_without_api_key_is_clear_503(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "geoapify_api_key", "")
    trip = await create_trip(client)
    r = await client.get(f"/api/trips/{trip['id']}/stays")
    assert r.status_code == 503 and "GEOAPIFY_API_KEY" in r.json()["error"]


@pytest.mark.parametrize("behaviour,status,fragment", [
    ("timeout", 504, "too long"),
    ("connect", 502, "Couldn't reach"),
    (429, 503, "busy"),
    (401, 503, "isn't configured"),
    (500, 502, "ran into a problem"),
    ("badjson", 502, "unexpected"),
])
async def test_stays_provider_failures_map_to_clean_errors(client, alice, monkeypatch, external_http, behaviour, status, fragment):
    monkeypatch.setattr(settings, "geoapify_api_key", "test-key-not-real")
    trip = await create_trip(client)

    async def fake_get(self, url, params):
        if behaviour == "timeout":
            raise httpx.ReadTimeout("slow")
        if behaviour == "connect":
            raise httpx.ConnectError("dns")
        if behaviour == "badjson":
            return httpx.Response(200, content=b"<html>nope</html>", request=httpx.Request("GET", url))
        return httpx.Response(behaviour, json={"message": "x"}, request=httpx.Request("GET", url))

    external_http(fake_get)
    r = await client.get(f"/api/trips/{trip['id']}/stays")
    assert r.status_code == status and fragment in r.json()["error"]
    assert "test-key-not-real" not in r.text


async def test_stays_success_labels_prices_as_estimates_and_save_roundtrip(client, client_b, alice, bob, monkeypatch, external_http):
    monkeypatch.setattr(settings, "geoapify_api_key", "test-key-not-real")
    trip = await create_trip(client)

    def feature(name, i):
        return {"properties": {"name": name, "lat": 15.5 + i * 0.001, "lon": 73.8, "categories": ["accommodation.hotel"],
                               "address_line2": "Goa"}}

    async def fake_get(self, url, params):
        feats = [feature(f"Hotel {i}", i) for i in range(10)]
        return httpx.Response(200, json={"features": feats}, request=httpx.Request("GET", url))

    external_http(fake_get)
    r = await client.get(f"/api/trips/{trip['id']}/stays")
    assert r.status_code == 200
    data = r.json()
    assert data["price_basis"] == "estimate" and data["availability"] == "not_checked"
    assert "not live rates" in data["disclaimer"]
    assert all(s["price_is_estimate"] is True for s in data["stays"])

    key = data["stays"][0]["key"]
    assert (await client.post(f"/api/trips/{trip['id']}/stays/saved", json={"stay_key": key})).status_code == 201
    assert len((await client.get(f"/api/trips/{trip['id']}/stays/saved")).json()["saved"]) == 1
    assert (await client_b.get(f"/api/trips/{trip['id']}/stays/saved")).status_code == 404       # not bob's trip
    assert (await client.post(f"/api/trips/{trip['id']}/stays/saved", json={"stay_key": "short"})).status_code == 422
    assert (await client.delete(f"/api/trips/{trip['id']}/stays/saved/{key}")).status_code == 200


# ------------------------------------------------------------------ travel health labelling
async def test_travel_health_labels_data_honestly(client):
    r = await client.get("/api/travel-health/Goa?month=6")
    assert r.status_code == 200
    body = r.json()
    labels = body["data_labels"]
    assert labels["historical_is_synthetic"] is body["is_synthetic"]
    if body["is_synthetic"]:
        assert "Synthetic" in labels["historical_outbreaks"] and any("DEMO DATA" in c for c in body["caveats"])
    alerts = body["current_alerts"]
    assert alerts["is_live_feed"] is False and alerts["source_type"] == "manually_curated_list"
    assert alerts["verified"] is False                                   # last_reviewed is null in the bundled file
    assert "not a live feed" in " ".join(alerts["notes"])
    assert "not a live feed" in labels["current_alerts"]


async def test_travel_health_errors(client):
    assert (await client.get("/api/travel-health/Atlantis")).status_code == 404
    assert (await client.get("/api/travel-health/Goa?month=13")).status_code == 422


async def test_travel_health_internal_error_not_leaked(client, monkeypatch):
    from app.routers import travel_health as th
    monkeypatch.setattr(th, "get_state_profile", lambda *a, **k: (_ for _ in ()).throw(KeyError("/data/idsp.csv")))
    r = await client.get("/api/travel-health/Goa")
    assert r.status_code == 500 and "idsp" not in r.text
