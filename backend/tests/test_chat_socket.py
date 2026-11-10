from contextlib import asynccontextmanager

import pytest
from starlette.testclient import TestClient, WebSocketDisconnect

from app.main import app
from app.services.chat_hub import ChatHub
from tests.conftest import GOOD_PASSWORD, ORIGIN


# ---------------------------------------------------------------- the hub on its own (fake sockets)
class FakeWS:
    def __init__(self, fail=False):
        self.sent, self.closed_with, self.fail = [], None, fail

    async def send_json(self, data):
        if self.fail:
            raise RuntimeError("socket is dead")
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed_with = code


async def test_hub_sets_is_me_per_connection():
    hub, mine, theirs = ChatHub(), FakeWS(), FakeWS()
    hub.add("g1", mine, "u1")
    hub.add("g1", theirs, "u2")
    await hub.broadcast_message("g1", {"id": "m1", "text": "hi"}, "u1")
    assert mine.sent[0]["message"]["is_me"] is True
    assert theirs.sent[0]["message"]["is_me"] is False


async def test_hub_only_reaches_the_right_group_and_drops_dead_sockets():
    hub, other_group, dead, alive = ChatHub(), FakeWS(), FakeWS(fail=True), FakeWS()
    hub.add("g2", other_group, "u3")
    hub.add("g1", dead, "u1")
    hub.add("g1", alive, "u2")
    await hub.broadcast_message("g1", {"id": "m1", "text": "hi"}, "u2")
    assert other_group.sent == [] and len(alive.sent) == 1
    await hub.broadcast_message("g1", {"id": "m2", "text": "again"}, "u2")   # dead one was removed, no error
    assert len(alive.sent) == 2

async def test_hub_broadcast_deleted_reaches_only_that_group():
    hub, here, elsewhere = ChatHub(), FakeWS(), FakeWS()
    hub.add("g1", here, "u1")
    hub.add("g2", elsewhere, "u2")
    await hub.broadcast_deleted("g1", "m1")
    assert here.sent == [{"type": "message_deleted", "id": "m1"}]
    assert elsewhere.sent == []

async def test_hub_close_user_and_close_group():
    hub, a, b = ChatHub(), FakeWS(), FakeWS()
    hub.add("g1", a, "u1")
    hub.add("g1", b, "u2")
    await hub.close_user("g1", "u1")
    assert a.closed_with == 1008 and b.closed_with is None
    await hub.close_group("g1")
    assert b.closed_with == 1008


# ---------------------------------------------------------------- the real endpoint
@pytest.fixture
def api(monkeypatch):
    @asynccontextmanager
    async def no_lifespan(_app):      # the tests use the fake database, so don't connect to a real one
        yield

    monkeypatch.setattr(app.router, "lifespan_context", no_lifespan)
    with TestClient(app, headers={"origin": ORIGIN}) as client:
        yield client


def login_as(api, email, name):
    r = api.post("/api/auth/signup", json={"name": name, "email": email, "password": GOOD_PASSWORD})
    assert r.status_code == 201, r.text
    cookie = {"cookie": f"access_token={api.cookies.get('access_token')}"}
    api.cookies.clear()
    return cookie


def test_message_is_pushed_live_to_members_only(api):
    alice = login_as(api, "alice@example.com", "Alice Traveller")
    bob = login_as(api, "bob@example.com", "Bob Wanderer")
    carol = login_as(api, "carol@example.com", "Carol Outsider")
    group = api.post("/api/groups", json={"name": "Goa Gang"}, headers=alice).json()["group"]
    api.post("/api/groups/join", json={"invite_code": group["invite_code"]}, headers=bob)
    url = f"/api/groups/{group['id']}/ws"

    with api.websocket_connect(url, headers={**alice, "origin": ORIGIN}) as ws_alice, \
         api.websocket_connect(url, headers={**bob, "origin": ORIGIN}) as ws_bob:
        r = api.post(f"/api/groups/{group['id']}/messages", json={"text": "Beach or hills?"}, headers=alice)
        assert r.status_code == 201
        for_bob, for_alice = ws_bob.receive_json(), ws_alice.receive_json()
        assert for_bob["type"] == "message" and for_bob["message"]["text"] == "Beach or hills?"
        assert for_bob["message"]["author"] == "Alice Traveller" and for_bob["message"]["is_me"] is False
        assert for_alice["message"]["is_me"] is True
        assert for_bob["message"]["id"] == r.json()["message"]["id"]
        assert "user_id" not in for_bob["message"]

    # not allowed in: outsider, no login, wrong origin
    for headers in ({**carol, "origin": ORIGIN}, {"origin": ORIGIN}, {**alice, "origin": "https://evil.example"}):
        with pytest.raises(WebSocketDisconnect):
            with api.websocket_connect(url, headers=headers):
                pass


def test_leaving_the_group_closes_the_socket(api):
    alice = login_as(api, "alice@example.com", "Alice Traveller")
    bob = login_as(api, "bob@example.com", "Bob Wanderer")
    group = api.post("/api/groups", json={"name": "Goa Gang"}, headers=alice).json()["group"]
    api.post("/api/groups/join", json={"invite_code": group["invite_code"]}, headers=bob)
    with api.websocket_connect(f"/api/groups/{group['id']}/ws", headers={**bob, "origin": ORIGIN}) as ws_bob:
        assert api.delete(f"/api/groups/{group['id']}/members/me", headers=bob).status_code == 200
        with pytest.raises(WebSocketDisconnect):
            ws_bob.receive_json()

def test_deleting_a_message_is_pushed_live(api):
    alice = login_as(api, "alice@example.com", "Alice Traveller")
    bob = login_as(api, "bob@example.com", "Bob Wanderer")
    group = api.post("/api/groups", json={"name": "Goa Gang"}, headers=alice).json()["group"]
    api.post("/api/groups/join", json={"invite_code": group["invite_code"]}, headers=bob)
    with api.websocket_connect(f"/api/groups/{group['id']}/ws", headers={**bob, "origin": ORIGIN}) as ws_bob:
        msg = api.post(f"/api/groups/{group['id']}/messages", json={"text": "oops"}, headers=alice).json()["message"]
        assert ws_bob.receive_json()["message"]["id"] == msg["id"]
        assert api.delete(f"/api/groups/{group['id']}/messages/{msg['id']}", headers=alice).status_code == 200
        assert ws_bob.receive_json() == {"type": "message_deleted", "id": msg["id"]}