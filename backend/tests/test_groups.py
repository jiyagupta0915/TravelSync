import pytest

from tests.conftest import GOOD_PASSWORD, create_trip, make_client, signup


async def make_group(c, name="Goa Gang"):
    r = await c.post("/api/groups", json={"name": name, "description": "Winter trip"})
    assert r.status_code == 201, r.text
    return r.json()["group"]


async def third_user():
    c = make_client()
    await signup(c, "carol@example.com", "Carol Outsider")
    return c


async def test_create_join_list_and_member_names_only(client, client_b, alice, bob):
    g = await make_group(client)
    assert g["is_owner"] and g["member_count"] == 1 and len(g["invite_code"]) >= 6
    r = await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    assert r.status_code == 200 and r.json()["group"]["member_count"] == 2
    assert (await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})).json()["already_member"] is True
    detail = (await client_b.get(f"/api/groups/{g['id']}")).json()["group"]
    assert {m["name"] for m in detail["members"]} == {"Alice Traveller", "Bob Wanderer"}
    assert "email" not in str(detail).lower() and "@" not in str(detail)           # no emails to other members
    assert len((await client_b.get("/api/groups")).json()["groups"]) == 1


async def test_validation_and_bad_invite(client, alice):
    assert (await client.post("/api/groups", json={"name": "x"})).status_code == 422
    assert (await client.post("/api/groups", json={"name": "Ok name", "description": "d" * 301})).status_code == 422
    assert (await client.post("/api/groups/join", json={"invite_code": "NOPE1234"})).status_code == 404
    assert (await client.post("/api/groups/join", json={"invite_code": "bad code!"})).status_code == 422


async def test_non_member_cannot_touch_group_anything(client, client_b, alice, bob):
    g = await make_group(client)
    sid = (await client.post(f"/api/groups/{g['id']}/suggestions", json={"destination": "Goa"})).json()["suggestion"]["id"]
    gid = g["id"]
    attempts = [
        ("GET", f"/api/groups/{gid}", None), ("DELETE", f"/api/groups/{gid}", None),
        ("GET", f"/api/groups/{gid}/messages", None), ("POST", f"/api/groups/{gid}/messages", {"text": "hi"}),
        ("GET", f"/api/groups/{gid}/suggestions", None), ("POST", f"/api/groups/{gid}/suggestions", {"destination": "Goa"}),
        ("PUT", f"/api/groups/{gid}/suggestions/{sid}/vote", None), ("DELETE", f"/api/groups/{gid}/suggestions/{sid}", None),
        ("POST", f"/api/groups/{gid}/decide", {"suggestion_id": sid}), ("DELETE", f"/api/groups/{gid}/members/me", None),
        ("DELETE", f"/api/groups/{gid}/decision", None),
    ]
    for method, path, body in attempts:
        r = await client_b.request(method, path, json=body)
        assert r.status_code == 404, f"{method} {path} -> {r.status_code}"
    assert (await client.get(f"/api/groups/{gid}/suggestions")).json()["suggestions"][0]["votes"] == 0


async def test_anonymous_rejected(client, alice):
    g = await make_group(client)
    async with make_client() as anon:
        for method, path in [("GET", "/api/groups"), ("POST", "/api/groups"), ("GET", f"/api/groups/{g['id']}"),
                             ("POST", f"/api/groups/{g['id']}/messages"), ("GET", "/api/notifications"),
                             ("GET", "/api/bookings"), ("POST", "/api/bookings")]:
            assert (await anon.request(method, path, json={})).status_code == 401, path


async def test_chat_roundtrip_and_after_filter(client, client_b, alice, bob):
    g = await make_group(client)
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    sent = (await client.post(f"/api/groups/{g['id']}/messages", json={"text": "  Beach or hills?  "})).json()["message"]
    assert sent["text"] == "Beach or hills?"
    msgs = (await client_b.get(f"/api/groups/{g['id']}/messages")).json()["messages"]
    assert [m["text"] for m in msgs] == ["Beach or hills?"] and msgs[0]["author"] == "Alice Traveller" and msgs[0]["is_me"] is False
    after = (await client_b.get(f"/api/groups/{g['id']}/messages", params={"after": msgs[-1]["created_at"]})).json()["messages"]
    assert after == []
    assert (await client.post(f"/api/groups/{g['id']}/messages", json={"text": "   "})).status_code == 422
    assert (await client.post(f"/api/groups/{g['id']}/messages", json={"text": "x" * 1001})).status_code == 422
    assert (await client.get(f"/api/groups/{g['id']}/messages", params={"after": "garbage"})).status_code == 422


async def test_suggest_vote_move_vote_and_decide(client, client_b, alice, bob):
    g = await make_group(client)
    gid = g["id"]
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})

    s1 = (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "goa", "note": "Beaches", "budget": 20000, "duration": 4, "preferences": ["Beach"]})).json()["suggestion"]
    assert s1["destination"] == "Goa" and s1["places"] and s1["budget"] == 20000
    s2 = (await client_b.post(f"/api/groups/{gid}/suggestions", json={"destination": "Manali"})).json()["suggestion"]
    assert (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "GOA"})).status_code == 409   # duplicate
    assert (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "Atlantis"})).status_code == 400
    assert (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "Goa", "budget": -1})).status_code == 422

    await client.put(f"/api/groups/{gid}/suggestions/{s1['id']}/vote")
    await client_b.put(f"/api/groups/{gid}/suggestions/{s1['id']}/vote")
    listing = (await client.get(f"/api/groups/{gid}/suggestions")).json()["suggestions"]
    assert listing[0]["destination"] == "Goa" and listing[0]["votes"] == 2 and listing[0]["voted_by_me"] is True

    # one vote per member: moving it takes it off the first
    moved = (await client_b.put(f"/api/groups/{gid}/suggestions/{s2['id']}/vote")).json()["suggestions"]
    by = {s["destination"]: s for s in moved}
    assert by["Goa"]["votes"] == 1 and by["Manali"]["votes"] == 1 and by["Manali"]["voted_by_me"] is True

    assert (await client_b.post(f"/api/groups/{gid}/decide", json={"suggestion_id": s1["id"]})).status_code == 403   # owner only
    done = await client.post(f"/api/groups/{gid}/decide", json={"suggestion_id": s1["id"]})
    assert done.status_code == 200 and done.json()["group"]["decided_suggestion_id"] == s1["id"]
    assert (await client_b.put(f"/api/groups/{gid}/suggestions/{s1['id']}/vote")).status_code == 409                # voting closed
    assert (await client.delete(f"/api/groups/{gid}/suggestions/{s1['id']}")).status_code == 409                    # chosen one stays
    assert (await client.delete(f"/api/groups/{gid}/decision")).status_code == 200
    assert (await client_b.put(f"/api/groups/{gid}/suggestions/{s1['id']}/vote")).status_code == 200


async def test_suggestion_from_another_group_cannot_be_used(client, client_b, alice, bob):
    g1, g2 = await make_group(client, "Group One"), await make_group(client, "Group Two")
    sid = (await client.post(f"/api/groups/{g1['id']}/suggestions", json={"destination": "Goa"})).json()["suggestion"]["id"]
    assert (await client.put(f"/api/groups/{g2['id']}/suggestions/{sid}/vote")).status_code == 404
    assert (await client.post(f"/api/groups/{g2['id']}/decide", json={"suggestion_id": sid})).status_code == 404
    assert (await client.delete(f"/api/groups/{g2['id']}/suggestions/{sid}")).status_code == 404


async def test_removal_rules_and_leaving(client, client_b, alice, bob):
    g = await make_group(client)
    gid = g["id"]
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    sid = (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "Goa"})).json()["suggestion"]["id"]
    assert (await client_b.delete(f"/api/groups/{gid}/suggestions/{sid}")).status_code == 403    # not mine, not owner
    assert (await client.delete(f"/api/groups/{gid}/members/me")).status_code == 409                # owner can't leave
    await client_b.put(f"/api/groups/{gid}/suggestions/{sid}/vote")
    assert (await client_b.delete(f"/api/groups/{gid}/members/me")).json() == {"left": True}
    assert (await client_b.get(f"/api/groups/{gid}")).status_code == 404
    assert (await client.get(f"/api/groups/{gid}/suggestions")).json()["suggestions"][0]["votes"] == 0   # leaver's vote removed
    assert (await client_b.delete(f"/api/groups/{gid}")).status_code == 404


async def test_only_owner_deletes_group_and_everything_goes(client, client_b, alice, bob, fake_db):
    g = await make_group(client)
    gid = g["id"]
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    sid = (await client.post(f"/api/groups/{gid}/suggestions", json={"destination": "Goa"})).json()["suggestion"]["id"]
    await client_b.put(f"/api/groups/{gid}/suggestions/{sid}/vote")
    await client.post(f"/api/groups/{gid}/messages", json={"text": "hello"})
    assert (await client_b.delete(f"/api/groups/{gid}")).status_code == 403
    assert (await client.delete(f"/api/groups/{gid}")).status_code == 200
    for coll in ("groups", "group_messages", "group_suggestions", "group_votes"):
        assert await fake_db[coll].count_documents({}) == 0, coll


async def test_group_capacity(client, alice, fake_db):
    g = await make_group(client)
    from bson import ObjectId
    await fake_db.groups.update_one({"invite_code": g["invite_code"]}, {"$set": {"member_ids": [ObjectId() for _ in range(19)] + [ObjectId(alice["id"])]}})
    async with make_client() as c:
        await signup(c, "late@example.com", "Late Comer")
        r = await c.post("/api/groups/join", json={"invite_code": g["invite_code"]})
        assert r.status_code == 409 and "full" in r.json()["error"]


# ------------------------------------------------------------------ trips from group + notifications
async def test_trip_from_group_has_companions_and_membership_is_verified(client, client_b, alice, bob):
    g = await make_group(client)
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    trip = await create_trip(client_b, "Goa", group_id=g["id"], source="group-vote")
    assert trip["companions"] == ["Alice Traveller"]
    carol = await third_user()
    r = await carol.post("/api/trips", json={"destination": "Goa", "group_id": g["id"]})
    assert r.status_code == 404                                      # cannot attach a trip to a group you're not in
    await client_b.delete(f"/api/groups/{g['id']}/members/me")
    assert (await client_b.get("/api/trips")).json()["trips"][0]["companions"] == []     # left -> no longer shown
    await carol.aclose()


async def test_notifications_are_real_events_and_private(client, client_b, alice, bob):
    g = await make_group(client)
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    await client_b.post(f"/api/groups/{g['id']}/suggestions", json={"destination": "Manali"})
    mine = (await client.get("/api/notifications")).json()
    assert mine["unread_count"] == 2
    assert [n["kind"] for n in mine["notifications"]] == ["suggestion_added", "member_joined"]
    assert "Bob Wanderer" in mine["notifications"][1]["message"]
    assert (await client_b.get("/api/notifications")).json()["unread_count"] == 0          # actors aren't notified of themselves
    nid = mine["notifications"][0]["id"]
    assert (await client_b.post(f"/api/notifications/{nid}/read")).status_code == 404       # someone else's
    assert (await client.post(f"/api/notifications/{nid}/read")).status_code == 200
    assert (await client.get("/api/notifications")).json()["unread_count"] == 1
    assert (await client.post("/api/notifications/read-all")).json()["unread_count"] == 0
    assert (await client.post("/api/notifications/zzz/read")).status_code == 400
