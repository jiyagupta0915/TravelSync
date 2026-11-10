from tests.test_groups import make_group


async def _setup(client, client_b):
    g = await make_group(client)
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    return g["id"]


async def test_author_can_soft_delete_and_history_shows_it(client, client_b, alice, bob):
    gid = await _setup(client, client_b)
    keep = (await client.post(f"/api/groups/{gid}/messages", json={"text": "keep me"})).json()["message"]
    gone = (await client.post(f"/api/groups/{gid}/messages", json={"text": "secret plan"})).json()["message"]
    assert gone["deleted"] is False

    assert (await client.delete(f"/api/groups/{gid}/messages/{gone['id']}")).status_code == 200

    for who in (client, client_b):
        messages = (await who.get(f"/api/groups/{gid}/messages")).json()["messages"]
        assert [m["id"] for m in messages] == [keep["id"], gone["id"]]        # same place in the history
        assert messages[0]["deleted"] is False and messages[0]["text"] == "keep me"
        assert messages[1]["deleted"] is True and messages[1]["text"] == ""   # the text is really gone


async def test_text_is_wiped_from_the_database(client, client_b, alice, bob):
    from app.database import get_db
    gid = await _setup(client, client_b)
    msg = (await client.post(f"/api/groups/{gid}/messages", json={"text": "secret plan"})).json()["message"]
    await client.delete(f"/api/groups/{gid}/messages/{msg['id']}")
    stored = await get_db().group_messages.find({}).to_list(10)
    assert all("secret plan" not in str(doc) for doc in stored)


async def test_only_the_author_can_delete(client, client_b, alice, bob):
    gid = await _setup(client, client_b)
    msg = (await client.post(f"/api/groups/{gid}/messages", json={"text": "mine"})).json()["message"]
    assert (await client_b.delete(f"/api/groups/{gid}/messages/{msg['id']}")).status_code == 403
    messages = (await client.get(f"/api/groups/{gid}/messages")).json()["messages"]
    assert messages[0]["deleted"] is False and messages[0]["text"] == "mine"


async def test_delete_is_idempotent_and_validates_ids(client, client_b, alice, bob):
    gid = await _setup(client, client_b)
    msg = (await client.post(f"/api/groups/{gid}/messages", json={"text": "bye"})).json()["message"]
    assert (await client.delete(f"/api/groups/{gid}/messages/{msg['id']}")).status_code == 200
    assert (await client.delete(f"/api/groups/{gid}/messages/{msg['id']}")).status_code == 200   # again: still fine
    assert (await client.delete(f"/api/groups/{gid}/messages/garbage")).status_code == 404
    assert (await client.delete(f"/api/groups/{gid}/messages/{'a' * 24}")).status_code == 404


async def test_outsiders_and_other_groups_cannot_delete(client, client_b, alice, bob):
    g1 = await make_group(client)                       # bob is NOT in this group
    msg = (await client.post(f"/api/groups/{g1['id']}/messages", json={"text": "hi"})).json()["message"]
    assert (await client_b.delete(f"/api/groups/{g1['id']}/messages/{msg['id']}")).status_code == 404
    g2 = await make_group(client, name="Second trip")   # a real message id used with the wrong group
    assert (await client.delete(f"/api/groups/{g2['id']}/messages/{msg['id']}")).status_code == 404