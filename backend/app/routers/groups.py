"""
Collaborative Travel Hub: travel groups, group chat, destination suggestions and voting.

Authorization model - every route below requires a logged-in user, and every route on /{group_id}/... additionally
requires that user to be a MEMBER of that group. Non-members get 404 (the group's existence is not revealed).
Nested records (messages, suggestions, votes) are always looked up together with their group_id, so a suggestion
id from another group can never be used through this group. Owner-only actions: decide, delete group, remove
someone else's suggestion. Emails are never shown to other members - only display names.

Chat is persisted and fetched by polling (the frontend asks for new messages every few seconds); it is not a
websocket connection.
"""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.dependencies import require_current_user
from app.models.group import DecideRequest, GroupCreate, JoinGroup, MessageCreate, SuggestionCreate
from app.services.notifications import notify, object_id_or_none
from app.services.places_service import get_top_places
from app.services.recommendation_engine import DF

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
    cursor = db.groups.find({"member_ids": user["_id"]}).sort("created_at", -1)
    return {"groups": [
        {"id": str(g["_id"]), "name": g["name"], "description": g.get("description", ""), "member_count": len(g["member_ids"]),
         "is_owner": g["owner_id"] == user["_id"], "created_at": _iso(g.get("created_at"))}
        async for g in cursor
    ]}


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
    for name in ("group_messages", "group_suggestions", "group_votes"):
        await db[name].delete_many({"group_id": group["_id"]})
    await db.groups.delete_one({"_id": group["_id"], "owner_id": user["_id"]})
    return {"deleted": True}


@router.delete("/{group_id}/members/me")
async def leave_group(group_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    if group["owner_id"] == user["_id"]:
        raise HTTPException(status_code=409, detail="The owner can't leave the group. Delete the group instead.")
    await db.groups.update_one({"_id": group["_id"]}, {"$pull": {"member_ids": user["_id"]}})
    await db.group_votes.delete_many({"group_id": group["_id"], "user_id": user["_id"]})
    return {"left": True}


# ------------------------------------------------------------------ chat (polling)
@router.get("/{group_id}/messages")
async def list_messages(group_id: str, after: str | None = Query(None, max_length=40), user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    query: dict = {"group_id": group["_id"]}
    if after:
        try:
            query["created_at"] = {"$gt": datetime.fromisoformat(after).replace(tzinfo=None)}
        except ValueError:
            raise HTTPException(status_code=422, detail="'after' must be an ISO timestamp.")
    docs = [d async for d in db.group_messages.find(query).sort("created_at", -1).limit(100)]
    docs.reverse()
    names = await _names(db, {d["user_id"] for d in docs})
    return {"messages": [
        {"id": str(d["_id"]), "text": d["text"], "created_at": d["created_at"].replace(tzinfo=timezone.utc).isoformat(),
         "author": names.get(d["user_id"], "Former member"), "is_me": d["user_id"] == user["_id"]}
        for d in docs
    ]}


@router.post("/{group_id}/messages", status_code=201)
async def post_message(group_id: str, payload: MessageCreate, user: dict = Depends(require_current_user)):
    group = await get_member_group(group_id, user)
    doc = {"group_id": group["_id"], "user_id": user["_id"], "text": payload.text, "created_at": datetime.now(timezone.utc)}
    result = await get_db().group_messages.insert_one(doc)
    return {"message": {"id": str(result.inserted_id), "text": doc["text"], "created_at": doc["created_at"].isoformat(),
                        "author": user["name"], "is_me": True}}


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
    return {"suggestions": await _serialize_suggestions(db, group, user)}


@router.delete("/{group_id}/suggestions/{suggestion_id}/vote")
async def remove_vote(group_id: str, suggestion_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    suggestion = await _get_group_suggestion(db, group, suggestion_id)
    if group.get("decided_suggestion_id"):
        raise HTTPException(status_code=409, detail="The group has already decided; voting is closed.")
    await db.group_votes.delete_one({"group_id": group["_id"], "user_id": user["_id"], "suggestion_id": suggestion["_id"]})
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
    return {"group": await _serialize_group(db, group, user), "suggestions": await _serialize_suggestions(db, group, user)}


@router.delete("/{group_id}/decision")
async def reopen_voting(group_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    group = await get_member_group(group_id, user)
    _require_owner(group, user)
    await db.groups.update_one({"_id": group["_id"], "owner_id": user["_id"]}, {"$unset": {"decided_suggestion_id": ""}})
    group.pop("decided_suggestion_id", None)
    return {"group": await _serialize_group(db, group, user)}


