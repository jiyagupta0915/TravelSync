import pytest

from tests.conftest import create_trip

BASE = {"kind": "hotel", "title": "Beach Resort", "provider": "Booked directly", "reference": "ABC123",
        "start_date": "2026-12-10", "end_date": "2026-12-14", "amount_inr": 18000, "notes": "Late check-in"}


async def test_booking_crud_and_persistence(client, alice):
    trip = await create_trip(client)
    r = await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})
    assert r.status_code == 201
    b = r.json()["booking"]
    assert b["kind"] == "hotel" and b["reference"] == "ABC123" and b["start_date"] == "2026-12-10"
    assert (await client.get("/api/bookings")).json()["bookings"][0]["id"] == b["id"]
    assert len((await client.get("/api/bookings", params={"trip_id": trip["id"]})).json()["bookings"]) == 1
    upd = await client.put(f"/api/bookings/{b['id']}", json={**BASE, "title": "Beach Resort & Spa", "amount_inr": 20000})
    assert upd.json()["booking"]["title"] == "Beach Resort & Spa"
    assert (await client.get("/api/bookings")).json()["bookings"][0]["amount_inr"] == 20000
    assert (await client.delete(f"/api/bookings/{b['id']}")).json() == {"deleted": True}
    assert (await client.get("/api/bookings")).json()["bookings"] == []


@pytest.mark.parametrize("patch", [
    {"kind": "spaceship"}, {"title": ""}, {"title": "   "}, {"title": "x" * 101}, {"amount_inr": -1}, {"amount_inr": 10**10},
    {"start_date": "2026-12-14", "end_date": "2026-12-10"}, {"start_date": "not-a-date"}, {"notes": "n" * 501}, {"reference": "r" * 61},
])
async def test_booking_validation(client, alice, patch):
    trip = await create_trip(client)
    r = await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"], **patch})
    assert r.status_code == 422, patch
    assert (await client.get("/api/bookings")).json()["bookings"] == []


async def test_bookings_are_private_and_tied_to_own_trips(client, client_b, alice, bob):
    ta = await create_trip(client)
    tb = await create_trip(client_b)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": ta["id"]})).json()["booking"]["id"]

    # bob cannot attach a booking to alice's trip, nor see/modify/delete alice's booking
    assert (await client_b.post("/api/bookings", json={**BASE, "trip_id": ta["id"]})).status_code == 404
    assert (await client_b.get("/api/bookings", params={"trip_id": ta["id"]})).status_code == 404
    assert (await client_b.get("/api/bookings")).json()["bookings"] == []
    assert (await client_b.put(f"/api/bookings/{bid}", json=BASE)).status_code == 404
    assert (await client_b.delete(f"/api/bookings/{bid}")).status_code == 404
    assert (await client.get("/api/bookings")).json()["bookings"][0]["id"] == bid
    # a user_id smuggled in the body is ignored
    r = await client_b.post("/api/bookings", json={**BASE, "trip_id": tb["id"], "user_id": alice["id"]})
    assert r.status_code == 201 and len((await client.get("/api/bookings")).json()["bookings"]) == 1


async def test_deleting_trip_deletes_its_bookings_and_counts_show_in_trips(client, alice, fake_db):
    trip = await create_trip(client)
    await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})
    assert (await client.get("/api/trips")).json()["trips"][0]["booking_count"] == 1
    await client.delete(f"/api/trips/{trip['id']}")
    assert await fake_db.bookings.count_documents({}) == 0


async def test_invalid_ids(client, alice):
    assert (await client.put("/api/bookings/xyz", json=BASE)).status_code == 400
    assert (await client.delete("/api/bookings/xyz")).status_code == 400
    assert (await client.get("/api/bookings", params={"trip_id": "short"})).status_code == 422
