"""
Collaborative Travel Hub: travel groups, group chat, destination suggestions and voting.

Authorization model - every route below requires a logged-in user, and every route on /{group_id}/... additionally
requires that user to be a MEMBER of that group. Non-members get 404 (the group's existence is not revealed).
Nested records (messages, suggestions, votes) are always looked up together with their group_id, so a suggestion
id from another group can never be used through this group. Owner-only actions: decide, delete group, remove
someone else's suggestion. Emails are never shown to other members - only display names.

Chat is persisted in MongoDB. New messages are pushed live over a WebSocket (/{group_id}/ws, receive-only, see
app/services/chat_hub.py); the frontend falls back to polling GET /messages whenever the socket is not connected.
A new destination suggestion is also posted into the chat as a "suggestion" message (a card), and every change to
suggestions, votes or the decision sends a small "suggestions_changed" event so open pages refresh straight away.

Unread messages: group_reads holds, per member and group, the newest message they have seen (set when they open the
chat). Everything newer that someone else wrote and that is not deleted counts as unread.

Read receipts: the same record also holds `seen_id`, the newest message that existed when the member last had the
chat open (joining a group sets last_read_id but not seen_id, because joining is not opening the chat). A message
counts as seen by a member when their seen_id is at or after it. GET /{group_id}/reads lists this for the other
members, and a "read" socket event keeps open chats up to date.
"""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database import get_db
from app.dependencies import require_current_user, user_from_token
from app.models.group import DecideRequest, GroupCreate, JoinGroup, MessageCreate, SuggestionCreate
from app.services.notifications import notify, object_id_or_none
from app.services.places_service import get_top_places
from app.services.recommendation_engine import DF
from app.services.chat_hub import hub

router = APIRouter(prefix="/api/groups", tags=["groups"])

MAX_MEMBERS = 20
MAX_GROUPS_PER_USER = 30
MAX_SUGGESTIONS = 30


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else None


async def _names(db, user_ids) -> dict:
    cursor = db.users.find({"_id": {"$in": list(user_ids)}}, {"name": 1})
    return {doc["_id"]: (doc.get("name") or "Traveller") async for doc in cursor}


async def get_member_group(group_id: str, user: dict) -> dict:
    oid = object_id_or_none(group_id)
    if oid is None:
        raise HTTPException(status_code=400, detail="Invalid group id.")
    group = await get_db().groups.find_one({"_id": oid, "member_ids": user["_id"]})
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group


def _message_out(doc: dict, author: str) -> dict:
    """A chat message as the API returns it (without `is_me`, which depends on who is looking)."""
    deleted = bool(doc.get("deleted_at"))
    kind = doc.get("kind", "text")
    out = {"id": str(doc["_id"]), "text": "" if deleted else doc["text"], "kind": kind,
           "created_at": doc["created_at"].replace(tzinfo=timezone.utc).isoformat(), "author": author, "deleted": deleted}
    if kind == "suggestion" and not deleted:
        out["suggestion"] = doc.get("suggestion")
    return out


async def _suggestions_changed(group: dict) -> None:
    """Tells everyone with the group page open to reload suggestions, votes and the decision."""
    await hub.broadcast_event(str(group["_id"]), {"type": "suggestions_changed"})


async def _unread_counts(db, user: dict, group_ids: list) -> dict:
    """{group _id: number of messages from other members that this user has not seen yet}."""
    reads = {r["group_id"]: r.get("last_read_id")
             async for r in db.group_reads.find({"user_id": user["_id"], "group_id": {"$in": group_ids}})}
    counts = {}
    for gid in group_ids:
        query = {"group_id": gid, "user_id": {"$ne": user["_id"]}, "deleted_at": {"$exists": False}}
        if reads.get(gid) is not None:
            query["_id"] = {"$gt": reads[gid]}
        counts[gid] = await db.group_messages.count_documents(query)
    return counts


async def _mark_read(db, group: dict, user: dict, opened: bool = True) -> None:
    """Remembers that this member is up to date with the group's newest message. `opened=True` (they have the chat
    open) also records it as seen, for read receipts, and tells the other members' open chats."""
    newest = [d async for d in db.group_messages.find({"group_id": group["_id"]}, {"_id": 1}).sort("_id", -1).limit(1)]
    newest_id = newest[0]["_id"] if newest else None
    key = {"group_id": group["_id"], "user_id": user["_id"]}
    before = await db.group_reads.find_one(key) if opened else None
    fields = {"last_read_id": newest_id, "read_at": datetime.now(timezone.utc)}
    if opened:
        fields["seen_id"] = newest_id
    await db.group_reads.update_one(key, {"$set": fields}, upsert=True)
    if opened and newest_id is not None and (before or {}).get("seen_id") != newest_id:
        await hub.broadcast_event(str(group["_id"]), {"type": "read", "user_id": str(user["_id"]), "seen_id": str(newest_id)},
                                  exclude_user=str(user["_id"]))


def _require_owner(group: dict, user: dict) -> None:
    if group["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the group owner can do that.")


async def _serialize_group(db, group: dict, user: dict) -> dict:
    names = await _names(db, group["member_ids"])
    return {
        "id": str(group["_id"]), "name": group["name"], "description": group.get("description", ""),
        "invite_code": group["invite_code"], "is_owner": group["owner_id"] == user["_id"],
        "member_count": len(group["member_ids"]), "created_at": _iso(group.get("created_at")),
        "decided_suggestion_id": str(group["decided_suggestion_id"]) if group.get("decided_suggestion_id") else None,
        "members": [
            {"id": str(uid), "name": names.get(uid, "Traveller"), "is_owner": uid == group["owner_id"], "is_me": uid == user["_id"]}
            for uid in group["member_ids"]
        ],
    }


# ------------------------------------------------------------------ groups
@router.get("")
async def list_groups(user: dict = Depends(require_current_user)):
    db = get_db()
    groups = [g async for g in db.groups.find({"member_ids": user["_id"]}).sort("created_at", -1)]
    unread = await _unread_counts(db, user, [g["_id"] for g in groups])
    return {"groups": [
        {"id": str(g["_id"]), "name": g["name"], "description": g.get("description", ""), "member_count": len(g["member_ids"]),
         "is_owner": g["owner_id"] == user["_id"], "created_at": _iso(g.get("created_at")), "unread_count": unread[g["_id"]]}
        for g in groups
    ]}


@router.get("/unread")
async def unread_messages(user: dict = Depends(require_current_user)):
    """Unread chat messages across all of the user's groups (for the sidebar badge). Declared before /{group_id}."""
    db = get_db()
    group_ids = [g["_id"] async for g in db.groups.find({"member_ids": user["_id"]}, {"_id": 1})]
    counts = await _unread_counts(db, user, group_ids)
    return {"total": sum(counts.values()), "groups": {str(gid): n for gid, n in counts.items() if n}}


@router.post("", status_code=201)
async def create_group(payload: GroupCreate, user: dict = Depends(require_current_user)):
    db = get_db()
    if await db.groups.count_documents({"member_ids": user["_id"]}) >= MAX_GROUPS_PER_USER:
        raise HTTPException(status_code=409, detail=f"You can be in at most {MAX_GROUPS_PER_USER} groups.")
    for _ in range(5):
        group = {"name": payload.name, "description": payload.description, "owner_id": user["_id"], "member_ids": [user["_id"]],
                 "invite_code": secrets.token_urlsafe(6), "created_at": datetime.now(timezone.utc)}
        try:
            result = await db.groups.insert_one(group)
        except DuplicateKeyError:
            continue
        group["_id"] = result.inserted_id
        return {"group": await _serialize_group(db, group, user)}
    raise HTTPException(status_code=503, detail="Could not create the group right now. Please try again.")


@router.post("/join")
async def join_group(payload: JoinGroup, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await db.groups.find_one({"invite_code": payload.invite_code})
    if group is None:
        raise HTTPException(status_code=404, detail="That invite code doesn't match any group.")
    if user["_id"] in group["member_ids"]:
        return {"group": await _serialize_group(db, group, user), "already_member": True}
    if len(group["member_ids"]) >= MAX_MEMBERS:
        raise HTTPException(status_code=409, detail=f"This group is full ({MAX_MEMBERS} members).")
    if await db.groups.count_documents({"member_ids": user["_id"]}) >= MAX_GROUPS_PER_USER:
        raise HTTPException(status_code=409, detail=f"You can be in at most {MAX_GROUPS_PER_USER} groups.")
    updated = await db.groups.find_one_and_update(
        {"_id": group["_id"], f"member_ids.{MAX_MEMBERS - 1}": {"$exists": False}},   # re-check capacity atomically
        {"$addToSet": {"member_ids": user["_id"]}}, return_document=True,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail=f"This group is full ({MAX_MEMBERS} members).")
    await _mark_read(db, updated, user, opened=False)   # messages sent before they joined are history, not "unread"
    await _suggestions_changed(updated)                 # open group pages show the new member straight away
    others = [m for m in updated["member_ids"] if m != user["_id"]]
    await notify(db, others, "member_joined", f"{user['name']} joined {updated['name']}.", f"/groups/{updated['_id']}")
    return {"group": await _serialize_group(db, updated, user), "already_member": False}


@router.get("/{group_id}")
async def get_group(group_id: str, user: dict = Depends(require_current_user)):
    group = await get_member_group(group_id, user)
    return {"group": await _serialize_group(get_db(), group, user)}


@router.delete("/{group_id}")
async def delete_group(group_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    _require_owner(group, user)
    for name in ("group_messages", "group_suggestions", "group_votes", "group_reads"):
        await db[name].delete_many({"group_id": group["_id"]})
    await db.groups.delete_one({"_id": group["_id"], "owner_id": user["_id"]})
    await hub.close_group(str(group["_id"]))                       # in delete_group
    return {"deleted": True}


@router.delete("/{group_id}/members/me")
async def leave_group(group_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    if group["owner_id"] == user["_id"]:
        raise HTTPException(status_code=409, detail="The owner can't leave the group. Delete the group instead.")
    await db.groups.update_one({"_id": group["_id"]}, {"$pull": {"member_ids": user["_id"]}})
    await db.group_votes.delete_many({"group_id": group["_id"], "user_id": user["_id"]})
    await db.group_reads.delete_many({"group_id": group["_id"], "user_id": user["_id"]})
    await hub.close_user(str(group["_id"]), str(user["_id"]))      # in leave_group
    await _suggestions_changed(group)                              # their vote is gone and the member list changed
    return {"left": True}


# ------------------------------------------------------------------ chat
CHAT_PAGE_SIZE = 50


@router.get("/{group_id}/messages")
async def list_messages(
    group_id: str,
    after: str | None = Query(None, max_length=40),
    before: str | None = Query(None, max_length=40),
    user: dict = Depends(require_current_user),
):
    """Newest page by default. `after` = only messages newer than that timestamp (polling / catch-up).
    `before` = a message id: the page of messages older than it ("Load older messages"). `has_more` says
    whether even older messages exist."""
    db = get_db()
    group = await get_member_group(group_id, user)
    query: dict = {"group_id": group["_id"]}
    if after:
        try:
            query["created_at"] = {"$gt": datetime.fromisoformat(after).replace(tzinfo=None)}
        except ValueError:
            raise HTTPException(status_code=422, detail="'after' must be an ISO timestamp.")
    if before:
        before_id = object_id_or_none(before)
        if before_id is None:
            raise HTTPException(status_code=422, detail="'before' must be a message id.")
        query["_id"] = {"$lt": before_id}
    # Newest first by _id, not created_at: MongoDB timestamps only have millisecond precision, so messages sent in the
    # same millisecond would tie and could come back in the wrong order or be skipped at a page boundary.
    docs = [d async for d in db.group_messages.find(query).sort("_id", -1).limit(CHAT_PAGE_SIZE + 1)]
    has_more = len(docs) > CHAT_PAGE_SIZE
    docs = docs[:CHAT_PAGE_SIZE]
    docs.reverse()
    names = await _names(db, {d["user_id"] for d in docs})
    return {"has_more": has_more, "messages": [
        {**_message_out(d, names.get(d["user_id"], "Former member")), "is_me": d["user_id"] == user["_id"]} for d in docs
    ]}

@router.post("/{group_id}/read")
async def mark_chat_read(group_id: str, user: dict = Depends(require_current_user)):
    """Called by the chat while it is open and visible: everything sent so far counts as seen by this member."""
    group = await get_member_group(group_id, user)
    await _mark_read(get_db(), group, user)
    return {"read": True}


@router.get("/{group_id}/reads")
async def list_reads(group_id: str, user: dict = Depends(require_current_user)):
    """Read receipts: for every OTHER current member, the newest message they have seen (`seen_id`, or null if they
    have never opened the chat). A message with id <= seen_id has been seen by that member."""
    db = get_db()
    group = await get_member_group(group_id, user)
    others = [m for m in group["member_ids"] if m != user["_id"]]
    names = await _names(db, others)
    seen = {r["user_id"]: r.get("seen_id") async for r in db.group_reads.find({"group_id": group["_id"], "user_id": {"$in": others}})}
    return {"reads": [{"id": str(m), "name": names.get(m, "Traveller"), "seen_id": str(seen[m]) if seen.get(m) else None} for m in others]}


@router.post("/{group_id}/messages", status_code=201)
async def post_message(group_id: str, payload: MessageCreate, user: dict = Depends(require_current_user)):
    group = await get_member_group(group_id, user)
    doc = {"group_id": group["_id"], "user_id": user["_id"], "text": payload.text, "created_at": datetime.now(timezone.utc)}
    result = await get_db().group_messages.insert_one(doc)
    message = _message_out({**doc, "_id": result.inserted_id}, user["name"])
    await hub.broadcast_message(str(group["_id"]), message, str(user["_id"]))   # saved first, then pushed
    return {"message": {**message, "is_me": True}}

@router.delete("/{group_id}/messages/{message_id}")
async def delete_message(group_id: str, message_id: str, user: dict = Depends(require_current_user)):
    """Soft delete: the row stays (so history and ordering are unchanged) but its text is wiped and it is marked
    deleted. Only the author can do it. Deleting twice is harmless."""
    db = get_db()
    group = await get_member_group(group_id, user)
    oid = object_id_or_none(message_id)
    message = await db.group_messages.find_one({"_id": oid, "group_id": group["_id"]}) if oid else None
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    if message["user_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own messages.")
    if message.get("kind") == "suggestion":
        raise HTTPException(status_code=409, detail="This is a destination suggestion. Remove it from the ideas list instead.")
    if not message.get("deleted_at"):
        await db.group_messages.update_one(
            {"_id": oid}, {"$set": {"deleted_at": datetime.now(timezone.utc), "text": ""}})
        await hub.broadcast_deleted(str(group["_id"]), str(oid))
    return {"deleted": True}

@router.websocket("/{group_id}/ws")
async def chat_socket(ws: WebSocket, group_id: str):
    """Live push of new chat messages. Same rules as the HTTP routes: logged in + member of the group."""
    # Browsers always send Origin on a WebSocket handshake, and the CSRF middleware only covers HTTP, so check it here.
    if ws.headers.get("origin") not in settings.cors_origins:
        await ws.close(code=1008)
        return
    user = await user_from_token(ws.cookies.get(settings.cookie_name))
    if user is None:
        await ws.close(code=1008)
        return
    try:
        group = await get_member_group(group_id, user)
    except HTTPException:
        await ws.close(code=1008)
        return
    key = str(group["_id"])
    await ws.accept()
    hub.add(key, ws, str(user["_id"]))
    try:
        while True:
            await ws.receive_text()   # content is ignored (the client sends "ping" to keep the connection alive)
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(key, ws)


# ------------------------------------------------------------------ destination suggestions + voting
async def _serialize_suggestions(db, group: dict, user: dict) -> list[dict]:
    suggestions = [s async for s in db.group_suggestions.find({"group_id": group["_id"]})]
    votes = [v async for v in db.group_votes.find({"group_id": group["_id"]})]
    counts: dict = {}
    for v in votes:
        counts[v["suggestion_id"]] = counts.get(v["suggestion_id"], 0) + 1
    mine = next((v["suggestion_id"] for v in votes if v["user_id"] == user["_id"]), None)
    names = await _names(db, {s["proposed_by"] for s in suggestions})
    out = [{
        "id": str(s["_id"]), "destination": s["destination"], "state": s.get("state", ""), "note": s.get("note", ""),
        "budget": s.get("budget"), "duration": s.get("duration"), "preferences": s.get("preferences", []),
        "places": s.get("places", []), "proposed_by": names.get(s["proposed_by"], "Former member"),
        "proposed_by_me": s["proposed_by"] == user["_id"], "votes": counts.get(s["_id"], 0), "voted_by_me": s["_id"] == mine,
        "is_decision": group.get("decided_suggestion_id") == s["_id"], "created_at": _iso(s.get("created_at")),
    } for s in suggestions]
    out.sort(key=lambda s: (-s["votes"], s["created_at"] or ""))
    return out


@router.get("/{group_id}/suggestions")
async def list_suggestions(group_id: str, user: dict = Depends(require_current_user)):
    group = await get_member_group(group_id, user)
    return {"suggestions": await _serialize_suggestions(get_db(), group, user),
            "decided_suggestion_id": str(group["decided_suggestion_id"]) if group.get("decided_suggestion_id") else None}


@router.post("/{group_id}/suggestions", status_code=201)
async def add_suggestion(group_id: str, payload: SuggestionCreate, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    row = DF[DF["Destination"].str.lower() == payload.destination.lower()].head(1)
    if row.empty:
        raise HTTPException(status_code=400, detail="Please choose a destination from the available suggestions.")
    if await db.group_suggestions.count_documents({"group_id": group["_id"]}) >= MAX_SUGGESTIONS:
        raise HTTPException(status_code=409, detail=f"A group can have at most {MAX_SUGGESTIONS} suggestions.")
    destination = str(row.iloc[0]["Destination"])
    doc = {
        "group_id": group["_id"], "destination": destination, "destination_key": destination.lower(), "state": str(row.iloc[0]["State"]),
        "note": payload.note, "budget": payload.budget, "duration": payload.duration, "preferences": payload.preferences,
        "places": [p["place_name"] for p in get_top_places(destination, 3)],       # real data from the bundled places dataset
        "proposed_by": user["_id"], "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await db.group_suggestions.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=f"{destination} has already been suggested to this group.")
    others = [m for m in group["member_ids"] if m != user["_id"]]
    await notify(db, others, "suggestion_added", f"{user['name']} suggested {destination} in {group['name']}.", f"/groups/{group['_id']}")
    doc["_id"] = result.inserted_id
    # The suggestion also shows up in the chat as a card, so the group can talk about it right where it was shared.
    card = {
        "group_id": group["_id"], "user_id": user["_id"], "kind": "suggestion", "text": f"Suggested {destination}",
        "suggestion_id": result.inserted_id, "created_at": datetime.now(timezone.utc),
        "suggestion": {"id": str(result.inserted_id), "destination": destination, "state": doc["state"], "note": doc["note"],
                       "budget": doc["budget"], "duration": doc["duration"], "preferences": doc["preferences"], "places": doc["places"]},
    }
    card["_id"] = (await db.group_messages.insert_one(card)).inserted_id
    await hub.broadcast_message(str(group["_id"]), _message_out(card, user["name"]), str(user["_id"]))
    await _suggestions_changed(group)
    return {"suggestion": next(s for s in await _serialize_suggestions(db, group, user) if s["id"] == str(result.inserted_id))}


async def _get_group_suggestion(db, group: dict, suggestion_id: str) -> dict:
    oid = object_id_or_none(suggestion_id)
    suggestion = await db.group_suggestions.find_one({"_id": oid, "group_id": group["_id"]}) if oid else None
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    return suggestion


@router.put("/{group_id}/suggestions/{suggestion_id}/vote")
async def cast_vote(group_id: str, suggestion_id: str, user: dict = Depends(require_current_user)):
    """One vote per member per group. Voting again for another suggestion moves the vote."""
    db = get_db()
    group = await get_member_group(group_id, user)
    suggestion = await _get_group_suggestion(db, group, suggestion_id)
    if group.get("decided_suggestion_id"):
        raise HTTPException(status_code=409, detail="The group has already decided; voting is closed.")
    await db.group_votes.update_one(
        {"group_id": group["_id"], "user_id": user["_id"]},
        {"$set": {"suggestion_id": suggestion["_id"], "created_at": datetime.now(timezone.utc)}}, upsert=True,
    )
    await _suggestions_changed(group)
    return {"suggestions": await _serialize_suggestions(db, group, user)}


@router.delete("/{group_id}/suggestions/{suggestion_id}/vote")
async def remove_vote(group_id: str, suggestion_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    suggestion = await _get_group_suggestion(db, group, suggestion_id)
    if group.get("decided_suggestion_id"):
        raise HTTPException(status_code=409, detail="The group has already decided; voting is closed.")
    await db.group_votes.delete_one({"group_id": group["_id"], "user_id": user["_id"], "suggestion_id": suggestion["_id"]})
    await _suggestions_changed(group)
    return {"suggestions": await _serialize_suggestions(db, group, user)}


@router.delete("/{group_id}/suggestions/{suggestion_id}")
async def delete_suggestion(group_id: str, suggestion_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    suggestion = await _get_group_suggestion(db, group, suggestion_id)
    if suggestion["proposed_by"] != user["_id"] and group["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the person who suggested this, or the group owner, can remove it.")
    if group.get("decided_suggestion_id") == suggestion["_id"]:
        raise HTTPException(status_code=409, detail="This is the group's chosen destination and can't be removed.")
    await db.group_votes.delete_many({"group_id": group["_id"], "suggestion_id": suggestion["_id"]})
    await db.group_suggestions.delete_one({"_id": suggestion["_id"], "group_id": group["_id"]})
    # Its card in the chat is withdrawn too (soft delete, like any other message).
    card = await db.group_messages.find_one({"group_id": group["_id"], "suggestion_id": suggestion["_id"], "deleted_at": {"$exists": False}})
    if card is not None:
        await db.group_messages.update_one({"_id": card["_id"]}, {"$set": {"deleted_at": datetime.now(timezone.utc), "text": ""}})
        await hub.broadcast_deleted(str(group["_id"]), str(card["_id"]))
    await _suggestions_changed(group)
    return {"deleted": True}


@router.post("/{group_id}/decide")
async def decide(group_id: str, payload: DecideRequest, user: dict = Depends(require_current_user)):
    """The owner locks in the destination (normally the one with the most votes) and voting closes."""
    db = get_db()
    group = await get_member_group(group_id, user)
    _require_owner(group, user)
    suggestion = await _get_group_suggestion(db, group, payload.suggestion_id)
    await db.groups.update_one({"_id": group["_id"], "owner_id": user["_id"]}, {"$set": {"decided_suggestion_id": suggestion["_id"]}})
    group["decided_suggestion_id"] = suggestion["_id"]
    others = [m for m in group["member_ids"] if m != user["_id"]]
    await notify(db, others, "destination_decided", f"{group['name']} chose {suggestion['destination']}!", f"/groups/{group['_id']}")
    await _suggestions_changed(group)
    return {"group": await _serialize_group(db, group, user), "suggestions": await _serialize_suggestions(db, group, user)}


@router.delete("/{group_id}/decision")
async def reopen_voting(group_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    _require_owner(group, user)
    await db.groups.update_one({"_id": group["_id"], "owner_id": user["_id"]}, {"$unset": {"decided_suggestion_id": ""}})
    group.pop("decided_suggestion_id", None)
    await _suggestions_changed(group)
    return {"group": await _serialize_group(db, group, user)}


