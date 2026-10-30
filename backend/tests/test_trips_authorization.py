"""Two-user authorization checks: one user must never read or change another user's private records."""

import pytest

from tests.conftest import create_trip

PRIVATE_GETS = [
    "/api/trips", "/api/trips/{id}", "/api/trips/{id}/packing-list", "/api/trips/{id}/stays/saved",
    "/api/users/me", "/api/users/me/settings",
]


async def test_every_private_endpoint_rejects_anonymous(client, alice):
    trip = await create_trip(client)
    anon_paths = [(m, p.format(id=trip["id"])) for m, p in [
        ("GET", "/api/trips"), ("POST", "/api/trips"), ("GET", "/api/trips/{id}"), ("DELETE", "/api/trips/{id}"),
        ("GET", "/api/trips/{id}/packing-list"), ("POST", "/api/trips/{id}/packing-list"),
        ("PATCH", "/api/trips/{id}/packing-list"), ("PUT", "/api/trips/{id}/packing-list/dates"),
        ("GET", "/api/trips/{id}/stays"), ("GET", "/api/trips/{id}/stays/saved"), ("POST", "/api/trips/{id}/stays/saved"),
        ("DELETE", "/api/trips/{id}/stays/saved/abcdefgh12345678"),
        ("GET", "/api/users/me"), ("PATCH", "/api/users/me"), ("GET", "/api/users/me/settings"), ("PUT", "/api/users/me/settings"),
        ("POST", "/api/auth/change-password"),
    ]]
    from tests.conftest import make_client
    async with make_client() as anon:
        for method, path in anon_paths:
            r = await anon.request(method, path, json={})
            assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


async def test_trip_list_is_scoped_to_owner(client, client_b, alice, bob):
    await create_trip(client, "Goa")
    await create_trip(client_b, "Manali")
    mine = (await client.get("/api/trips")).json()["trips"]
    theirs = (await client_b.get("/api/trips")).json()["trips"]
    assert [t["destination"] for t in mine] == ["Goa"]
    assert [t["destination"] for t in theirs] == ["Manali"]


async def test_cannot_read_modify_or_delete_another_users_trip(client, client_b, alice, bob):
    trip = await create_trip(client, "Goa")
    tid = trip["id"]
    await client.post(f"/api/trips/{tid}/packing-list", json={})

    # bob tries every route against alice's trip id -> always 404 (existence is not revealed)
    attempts = [
        ("GET", f"/api/trips/{tid}"), ("DELETE", f"/api/trips/{tid}"),
        ("GET", f"/api/trips/{tid}/packing-list"), ("POST", f"/api/trips/{tid}/packing-list"),
        ("PATCH", f"/api/trips/{tid}/packing-list"), ("PUT", f"/api/trips/{tid}/packing-list/dates"),
        ("GET", f"/api/trips/{tid}/stays"), ("GET", f"/api/trips/{tid}/stays/saved"),
        ("POST", f"/api/trips/{tid}/stays/saved"), ("DELETE", f"/api/trips/{tid}/stays/saved/abcdefgh12345678"),
    ]
    bodies = {
        "PATCH": {"items": []}, "PUT": {"start_date": "2026-12-01", "end_date": "2026-12-03"},
        "POST": {"stay_key": "abcdefgh12345678", "activities": []},
    }
    for method, path in attempts:
        r = await client_b.request(method, path, json=bodies.get(method, {}))
        assert r.status_code == 404, f"{method} {path} -> {r.status_code} {r.text}"

    # ...and alice's data is untouched
    assert (await client.get(f"/api/trips/{tid}")).status_code == 200
    assert (await client.get(f"/api/trips/{tid}/packing-list")).status_code == 200


async def test_client_supplied_user_id_is_ignored(client, client_b, alice, bob):
    r = await client_b.post("/api/trips", json={"destination": "Goa", "user_id": alice["id"], "role": "admin"})
    assert r.status_code == 201
    assert r.json()["trip"]["user_id"] == bob["id"]
    assert (await client.get("/api/trips")).json()["trips"] == []


async def test_invalid_trip_id_is_400(client, alice):
    assert (await client.get("/api/trips/not-an-object-id")).status_code == 400
    assert (await client.get("/api/trips/64b64b64b64b64b64b64b64b")).status_code == 404


# ------------------------------------------------------------------ trip validation
@pytest.mark.parametrize("payload", [
    {"destination": "Goa", "duration": 0}, {"destination": "Goa", "duration": 31}, {"destination": "Goa", "duration": 2.5},
    {"destination": "Goa", "budget": 0}, {"destination": "Goa", "budget": -5}, {"destination": "Goa", "budget": 10**9},
    {"destination": "Goa", "traveller_type": "Alien"}, {"destination": "Goa", "source": "hacker"},
    {"destination": "Goa", "budget": "lots"},
])
async def test_trip_create_rejects_invalid_values(client, alice, payload):
    r = await client.post("/api/trips", json=payload)
    assert r.status_code == 422, r.text
    assert (await client.get("/api/trips")).json()["trips"] == []


async def test_trip_create_unknown_or_empty_destination(client, alice):
    assert (await client.post("/api/trips", json={"destination": "Atlantis"})).status_code == 400
    assert (await client.post("/api/trips", json={"destination": "   "})).status_code == 400


async def test_trip_create_ok_and_case_insensitive_destination(client, alice):
    r = await client.post("/api/trips", json={"destination": "gOa", "duration": 5, "budget": 15000.5, "traveller_type": "Couple"})
    assert r.status_code == 201
    trip = r.json()["trip"]
    assert trip["destination"] == "Goa" and trip["duration"] == 5 and trip["budget"] == 15000.5 and trip["status"] == "upcoming"


# ------------------------------------------------------------------ profile / settings field protection
async def test_profile_update_persists_and_rejects_protected_fields(client, alice):
    ok = await client.patch("/api/users/me", json={"name": "  Alice  B ", "home_city": "Amritsar"})
    assert ok.status_code == 200 and ok.json()["user"]["name"] == "Alice B"
    assert (await client.get("/api/auth/me")).json()["user"]["home_city"] == "Amritsar"

    for bad in [{"email": "evil@example.com"}, {"role": "admin"}, {"password_hash": "x"}, {"token_version": 99}, {"_id": "1"}, {"id": "1"}]:
        r = await client.patch("/api/users/me", json=bad)
        assert r.status_code == 422, bad
    assert (await client.get("/api/users/me")).json()["user"]["email"] == "alice@example.com"

    assert (await client.patch("/api/users/me", json={})).status_code == 422
    assert (await client.patch("/api/users/me", json={"name": ""})).status_code == 422
    cleared = await client.patch("/api/users/me", json={"home_city": ""})
    assert cleared.json()["user"]["home_city"] == ""


async def test_profile_is_per_user(client, client_b, alice, bob):
    await client.patch("/api/users/me", json={"name": "Alice Changed"})
    assert (await client_b.get("/api/users/me")).json()["user"]["name"] == "Bob Wanderer"


async def test_settings_roundtrip_and_validation(client, alice):
    body = {"default_traveller_type": "Family", "default_duration_days": 7, "default_budget_inr": 45000}
    assert (await client.put("/api/users/me/settings", json=body)).json()["settings"] == body
    assert (await client.get("/api/users/me/settings")).json()["settings"] == body
    assert (await client.get("/api/auth/me")).json()["user"]["settings"] == body
    for bad in [{"default_duration_days": 0}, {"default_duration_days": 99}, {"default_budget_inr": -1},
                {"default_traveller_type": "Dog"}, {"unknown": 1}]:
        assert (await client.put("/api/users/me/settings", json=bad)).status_code == 422, bad
    assert (await client.get("/api/users/me/settings")).json()["settings"] == body      # failed saves changed nothing
    assert (await client.put("/api/users/me/settings", json={})).json()["settings"] == {}


# ------------------------------------------------------------------ deletion / related records
async def test_delete_trip_removes_children_but_not_other_users_data(client, client_b, alice, bob):
    t1 = await create_trip(client, "Goa")
    t2 = await create_trip(client_b, "Goa")
    await client.post(f"/api/trips/{t1['id']}/packing-list", json={})
    await client_b.post(f"/api/trips/{t2['id']}/packing-list", json={})
    assert (await client.delete(f"/api/trips/{t1['id']}")).json() == {"deleted": True}
    assert (await client.get(f"/api/trips/{t1['id']}/packing-list")).status_code == 404
    assert (await client.delete(f"/api/trips/{t1['id']}")).status_code == 404
    assert (await client_b.get(f"/api/trips/{t2['id']}/packing-list")).status_code == 200


# ------------------------------------------------------------------ public endpoints stay public + bounded
async def test_public_endpoints_still_public():
    from tests.conftest import make_client
    async with make_client() as anon:
        assert (await anon.get("/api/health")).status_code == 200
        assert (await anon.get("/api/features")).status_code == 200
        assert (await anon.get("/api/destinations/search?q=goa")).status_code == 200
        assert (await anon.get("/api/places/Goa")).status_code == 200
        assert (await anon.get("/api/destinations/search?q=" + "a" * 500)).status_code == 422
