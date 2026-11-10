from tests.test_groups import make_group


async def test_load_older_messages_in_pages(client, client_b, alice, bob):
    g = await make_group(client)
    gid = g["id"]
    await client_b.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    for i in range(60):
        await client.post(f"/api/groups/{gid}/messages", json={"text": f"msg {i}"})

    first = (await client_b.get(f"/api/groups/{gid}/messages")).json()
    assert [m["text"] for m in first["messages"]] == [f"msg {i}" for i in range(10, 60)]   # newest 50, oldest first
    assert first["has_more"] is True

    older = (await client_b.get(f"/api/groups/{gid}/messages", params={"before": first["messages"][0]["id"]})).json()
    assert [m["text"] for m in older["messages"]] == [f"msg {i}" for i in range(10)]
    assert older["has_more"] is False
    assert all(m["is_me"] is False for m in older["messages"])


async def test_before_must_be_a_valid_id_and_members_only(client, client_b, alice, bob):
    g = await make_group(client)
    gid = g["id"]
    assert (await client.get(f"/api/groups/{gid}/messages", params={"before": "garbage"})).status_code == 422
    assert (await client_b.get(f"/api/groups/{gid}/messages", params={"before": "a" * 24})).status_code == 404   # bob isn't a member