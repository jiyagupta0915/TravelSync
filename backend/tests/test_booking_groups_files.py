"""Group bookings, private file attachments and sharing a booking into the group chat."""

import pytest

from tests.conftest import create_trip
from tests.test_groups import make_group, third_user

BASE = {"kind": "train", "title": "Rajdhani DEL → GOI", "provider": "IRCTC", "reference": "PNR123",
        "start_date": "2026-12-10", "end_date": "2026-12-11", "amount_inr": 4200, "notes": ""}
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 16


async def joined_group(client, client_b):
    g = await make_group(client)
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    return g


async def upload(c, bid, data=PDF, name="ticket.pdf", ctype="application/pdf"):
    return await c.post(f"/api/bookings/{bid}/files", files={"file": (name, data, ctype)})


async def group_booking(c, gid, **extra):
    r = await c.post("/api/bookings", json={**BASE, "group_id": gid, **extra})
    assert r.status_code == 201, r.text
    return r.json()["booking"]


# ------------------------------------------------------------------ scope rules
async def test_needs_exactly_one_of_trip_or_group(client, alice):
    trip = await create_trip(client)
    g = await make_group(client)
    assert (await client.post("/api/bookings", json=BASE)).status_code == 422
    assert (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"], "group_id": g["id"]})).status_code == 422
    assert (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"], "share_to_chat": True})).status_code == 422


async def test_group_booking_visible_to_members_only(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    b = await group_booking(client, g["id"])
    assert b["scope"] == "group" and b["group_name"] == "Goa Gang" and b["created_by"] == "Alice Traveller" and b["can_edit"]
    seen = (await client_b.get("/api/bookings")).json()["bookings"]
    assert [x["id"] for x in seen] == [b["id"]] and seen[0]["can_edit"] is False
    assert len((await client_b.get("/api/bookings", params={"group_id": g["id"]})).json()["bookings"]) == 1

    carol = await third_user()
    assert (await carol.get("/api/bookings")).json()["bookings"] == []
    assert (await carol.get("/api/bookings", params={"group_id": g["id"]})).status_code == 404
    assert (await carol.post("/api/bookings", json={**BASE, "group_id": g["id"]})).status_code == 404
    assert (await carol.delete(f"/api/bookings/{b['id']}")).status_code == 404
    await carol.aclose()


async def test_only_author_or_owner_can_change_group_booking(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    bobs = await group_booking(client_b, g["id"], title="Bob's hotel", kind="hotel")
    assert bobs["can_edit"] is True
    # the owner (alice) may manage bob's booking; a plain member may not manage the owner's
    assert (await client.put(f"/api/bookings/{bobs['id']}", json={**BASE, "title": "Renamed"})).status_code == 200
    alices = await group_booking(client, g["id"])
    assert (await client_b.put(f"/api/bookings/{alices['id']}", json=BASE)).status_code == 403
    assert (await client_b.delete(f"/api/bookings/{alices['id']}")).status_code == 403
    assert (await upload(client_b, alices["id"])).status_code == 403
    assert (await client.delete(f"/api/bookings/{bobs['id']}")).status_code == 200


async def test_personal_bookings_do_not_leak_into_group_view(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    trip = await create_trip(client)
    await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})
    assert (await client_b.get("/api/bookings")).json()["bookings"] == []
    assert (await client_b.get("/api/bookings", params={"group_id": g["id"]})).json()["bookings"] == []
    assert (await client.get("/api/bookings")).json()["bookings"][0]["scope"] == "personal"


async def test_leaving_group_removes_access(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    b = await group_booking(client, g["id"])
    await client_b.delete(f"/api/groups/{g['id']}/members/me")
    assert (await client_b.get("/api/bookings")).json()["bookings"] == []
    assert (await client_b.get(f"/api/bookings/{b['id']}/files/{'0' * 24}")).status_code == 404


# ------------------------------------------------------------------ files
@pytest.mark.parametrize("data,name,ctype", [(PDF, "t.pdf", "application/pdf"), (PNG, "t.png", "image/png"),
                                              (JPG, "t.jpeg", "image/jpeg"), (WEBP, "t.webp", "image/webp")])
async def test_upload_download_roundtrip(client, alice, data, name, ctype):
    trip = await create_trip(client)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    r = await upload(client, bid, data, name, "application/octet-stream")
    assert r.status_code == 201
    att = r.json()["attachment"]
    assert att["content_type"] == ctype and att["size"] == len(data)
    got = await client.get(f"/api/bookings/{bid}/files/{att['id']}")
    assert got.status_code == 200 and got.content == data and got.headers["content-type"].startswith(ctype)
    assert got.headers["x-content-type-options"] == "nosniff" and got.headers["content-disposition"].startswith("inline")
    assert (await client.get(f"/api/bookings/{bid}/files/{att['id']}", params={"download": 1})).headers["content-disposition"].startswith("attachment")
    listed = (await client.get("/api/bookings")).json()["bookings"][0]
    assert [a["id"] for a in listed["attachments"]] == [att["id"]] and "data" not in str(listed)


async def test_rejects_wrong_empty_and_oversized_files(client, alice, monkeypatch):
    trip = await create_trip(client)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    # the browser's claimed type and the file name are ignored: only the content counts
    assert (await upload(client, bid, b"<html><script>alert(1)</script></html>", "evil.pdf", "application/pdf")).status_code == 415
    assert (await upload(client, bid, b"MZ\x90\x00 exe", "run.png", "image/png")).status_code == 415
    assert (await upload(client, bid, b"", "empty.pdf")).status_code == 422
    from app.routers import bookings
    monkeypatch.setattr(bookings, "MAX_FILE_BYTES", 100)
    assert (await upload(client, bid, PDF + b"x" * 200)).status_code == 413
    assert (await client.get("/api/bookings")).json()["bookings"][0]["attachments"] == []


async def test_file_count_limit_and_name_sanitised(client, alice):
    trip = await create_trip(client)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    first = (await upload(client, bid, PDF, "../../etc/passwd.exe")).json()["attachment"]
    assert first["filename"] == "passwd.pdf"                      # path stripped, extension follows the real content
    from app.services.booking_files import safe_filename
    assert safe_filename('a"b\r\nc<>.exe', "pdf") == "abc.pdf" and safe_filename("..\\..\\x", "png") == "x.png"
    assert safe_filename(None, "jpg") == "ticket.jpg" and safe_filename("...", "pdf") == "ticket.pdf"
    for _ in range(4):
        assert (await upload(client, bid)).status_code == 201
    assert (await upload(client, bid)).status_code == 409


async def test_unicode_filename_downloads(client, alice):
    trip = await create_trip(client)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    att = (await upload(client, bid, PDF, "टिकट.pdf")).json()["attachment"]
    got = await client.get(f"/api/bookings/{bid}/files/{att['id']}")
    assert got.status_code == 200 and "filename*=UTF-8''" in got.headers["content-disposition"]


async def test_files_are_private(client, client_b, alice, bob):
    trip = await create_trip(client)
    bid = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    att = (await upload(client, bid)).json()["attachment"]
    url = f"/api/bookings/{bid}/files/{att['id']}"
    assert (await client_b.get(url)).status_code == 404
    assert (await client_b.delete(url)).status_code == 404
    assert (await upload(client_b, bid)).status_code == 404
    # a file id can't be used through a different booking
    other = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    assert (await client.get(f"/api/bookings/{other}/files/{att['id']}")).status_code == 404
    assert (await client.get(f"/api/bookings/{bid}/files/not-an-id")).status_code == 404


async def test_group_members_can_read_files(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    b = await group_booking(client, g["id"])
    att = (await upload(client, b["id"])).json()["attachment"]
    got = await client_b.get(f"/api/bookings/{b['id']}/files/{att['id']}")
    assert got.status_code == 200 and got.content == PDF
    assert (await client_b.delete(f"/api/bookings/{b['id']}/files/{att['id']}")).status_code == 403
    assert (await client.delete(f"/api/bookings/{b['id']}/files/{att['id']}")).status_code == 200
    assert (await client_b.get(f"/api/bookings/{b['id']}/files/{att['id']}")).status_code == 404


async def test_files_removed_with_booking_trip_and_group(client, client_b, alice, bob, fake_db):
    trip = await create_trip(client)
    b1 = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    await upload(client, b1)
    assert await fake_db.booking_files.count_documents({}) == 1
    await client.delete(f"/api/bookings/{b1}")
    assert await fake_db.booking_files.count_documents({}) == 0

    b2 = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    await upload(client, b2)
    await client.delete(f"/api/trips/{trip['id']}")
    assert await fake_db.booking_files.count_documents({}) == 0 and await fake_db.bookings.count_documents({}) == 0

    g = await joined_group(client, client_b)
    gb = await group_booking(client, g["id"])
    await upload(client, gb["id"])
    await client.delete(f"/api/groups/{g['id']}")
    assert await fake_db.booking_files.count_documents({}) == 0 and await fake_db.bookings.count_documents({}) == 0


# ------------------------------------------------------------------ chat share
async def test_share_to_chat_card_hides_private_details(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    b = await group_booking(client, g["id"], share_to_chat=True)
    msgs = (await client_b.get(f"/api/groups/{g['id']}/messages")).json()["messages"]
    assert len(msgs) == 1 and msgs[0]["kind"] == "booking" and msgs[0]["booking"]["title"] == BASE["title"]
    assert "PNR123" not in str(msgs) and "4200" not in str(msgs)
    # any member can share again; personal bookings cannot be shared
    assert (await client_b.post(f"/api/bookings/{b['id']}/share")).status_code == 200
    assert len((await client.get(f"/api/groups/{g['id']}/messages")).json()["messages"]) == 2
    trip = await create_trip(client)
    pb = (await client.post("/api/bookings", json={**BASE, "trip_id": trip["id"]})).json()["booking"]["id"]
    assert (await client.post(f"/api/bookings/{pb}/share")).status_code == 409


async def test_deleting_booking_removes_its_chat_cards(client, client_b, alice, bob):
    g = await joined_group(client, client_b)
    b = await group_booking(client, g["id"], share_to_chat=True)
    await client.delete(f"/api/bookings/{b['id']}")
    msgs = (await client_b.get(f"/api/groups/{g['id']}/messages")).json()["messages"]
    assert msgs[0]["deleted"] is True and "booking" not in msgs[0]
