import httpx
import pytest

from tests.conftest import create_trip


async def test_generate_persists_and_survives_reload(client, alice):
    trip = await create_trip(client)
    r = await client.post(f"/api/trips/{trip['id']}/packing-list", json={"activities": ["beach"]})
    assert r.status_code == 201
    names = [i["name"] for i in r.json()["packing_list"]["items"]]
    assert "Swimwear" in names

    # check an item off + add a custom item, then "refresh" (fresh GET)
    items = r.json()["packing_list"]["items"]
    items[0]["packed"] = True
    items.append({"id": "c1", "category": "Activity", "name": "  Frisbee  ", "quantity": 2, "packed": False, "source": "custom"})
    assert (await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": items})).status_code == 200
    again = (await client.get(f"/api/trips/{trip['id']}/packing-list")).json()["packing_list"]["items"]
    assert again[0]["packed"] is True and again[-1]["name"] == "Frisbee"


async def test_generate_twice_conflicts_unless_regenerate_and_regenerate_keeps_user_data(client, alice):
    trip = await create_trip(client)
    await client.post(f"/api/trips/{trip['id']}/packing-list", json={})
    assert (await client.post(f"/api/trips/{trip['id']}/packing-list", json={})).status_code == 409
    items = (await client.get(f"/api/trips/{trip['id']}/packing-list")).json()["packing_list"]["items"]
    items[0]["packed"] = True
    items.append({"id": "c9", "category": "Documents", "name": "Visa letter", "quantity": 1, "packed": False, "source": "custom"})
    await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": items})
    regen = await client.post(f"/api/trips/{trip['id']}/packing-list", json={"regenerate": True})
    assert regen.status_code == 201
    out = regen.json()["packing_list"]["items"]
    assert any(i["name"] == "Visa letter" for i in out) and any(i["packed"] for i in out)


@pytest.mark.parametrize("bad_item", [
    {"id": "x1", "category": "Clothing", "name": "", "quantity": 1},
    {"id": "x1", "category": "Clothing", "name": "x" * 81, "quantity": 1},
    {"id": "x1", "category": "Clothing", "name": "Socks", "quantity": 0},
    {"id": "x1", "category": "Clothing", "name": "Socks", "quantity": 1000},
    {"id": "x1", "category": "Weapons", "name": "Socks", "quantity": 1},
    {"id": "bad id!", "category": "Clothing", "name": "Socks", "quantity": 1},
])
async def test_patch_rejects_invalid_items_and_leaves_list_unchanged(client, alice, bad_item):
    trip = await create_trip(client)
    created = (await client.post(f"/api/trips/{trip['id']}/packing-list", json={})).json()["packing_list"]["items"]
    r = await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": [bad_item]})
    assert r.status_code == 422
    assert (await client.get(f"/api/trips/{trip['id']}/packing-list")).json()["packing_list"]["items"] == created


async def test_patch_rejects_duplicate_ids_and_too_many_items(client, alice):
    trip = await create_trip(client)
    await client.post(f"/api/trips/{trip['id']}/packing-list", json={})
    dup = [{"id": "a", "category": "Clothing", "name": "A"}, {"id": "a", "category": "Clothing", "name": "B"}]
    assert (await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": dup})).status_code == 422
    many = [{"id": f"i{n}", "category": "Clothing", "name": "x"} for n in range(201)]
    assert (await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": many})).status_code == 422


async def test_patch_without_existing_list_is_404(client, alice):
    trip = await create_trip(client)
    assert (await client.patch(f"/api/trips/{trip['id']}/packing-list", json={"items": []})).status_code == 404


@pytest.mark.parametrize("start,end,status", [
    ("2026-12-10", "2026-12-12", 200),
    ("2026-12-12", "2026-12-10", 422),          # end before start
    ("2026-13-01", "2026-13-02", 422),          # not a date
    ("12/10/2026", "12/12/2026", 422),          # wrong format
    ("2026-12-01", "2027-06-30", 422),          # longer than 90 days
    ("1990-01-01", "1990-01-03", 422),          # far past
    ("2090-01-01", "2090-01-03", 422),          # far future
])
async def test_trip_dates_validation(client, alice, start, end, status):
    trip = await create_trip(client)
    r = await client.put(f"/api/trips/{trip['id']}/packing-list/dates", json={"start_date": start, "end_date": end})
    assert r.status_code == status, r.text
    trips = (await client.get("/api/trips")).json()["trips"]
    if status == 200:
        assert trips[0]["start_date"] == start and trips[0]["end_date"] == end
    else:
        assert "start_date" not in trips[0]          # a rejected update changed nothing


async def test_forecast_provider_failure_falls_back_to_climate_tier(client, alice, external_http):
    trip = await create_trip(client)
    await client.put(f"/api/trips/{trip['id']}/packing-list/dates", json={"start_date": "2026-12-10", "end_date": "2026-12-12"})

    async def failing_get(self, url, params):
        assert "open-meteo" in url                      # proves the real forecast call was attempted
        raise httpx.ConnectTimeout("open-meteo down")

    external_http(failing_get)
    r = await client.post(f"/api/trips/{trip['id']}/packing-list", json={})
    assert r.status_code == 201
    assert r.json()["packing_list"]["tier"] == "climate"          # honest fallback, not a pretend forecast


async def test_forecast_tier_used_when_provider_answers(client, alice, monkeypatch):
    from app.routers import packing as packing_router
    trip = await create_trip(client)
    await client.put(f"/api/trips/{trip['id']}/packing-list/dates", json={"start_date": "2026-12-10", "end_date": "2026-12-12"})

    async def fake_weather(*a, **k):
        return {"condition": "rainy", "avg_min_temp": 20.0, "avg_max_temp": 27.0, "avg_rain_probability": 80.0}

    monkeypatch.setattr(packing_router, "fetch_weather_summary", fake_weather)
    r = await client.post(f"/api/trips/{trip['id']}/packing-list", json={})
    pl = r.json()["packing_list"]
    assert pl["tier"] == "forecast" and any(i["name"] == "Umbrella" for i in pl["items"])
