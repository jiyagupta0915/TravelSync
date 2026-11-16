"""
Bookings & tickets - a record of reservations made ELSEWHERE (hotel, flight, train, bus, activity, other).
TravelSync does not sell, make or confirm bookings: `reference` is whatever confirmation number the user typed in.

Two scopes (a booking has exactly one):
  * personal - attached to one of the user's own trips. Only that user can see or change it.
  * group    - attached to a travel group. Every member can see it (and its files); only the member who added it,
               or the group owner, can edit it, attach/remove files, or delete it.

Files (PDF / PNG / JPEG / WebP, 5 MB, 5 per booking) are stored privately in MongoDB, see app/services/booking_files.py.
A group booking can also be posted into the group chat as a card (details only: never the confirmation number,
the amount or the files).
"""

from datetime import date, datetime, timezone

from urllib.parse import quote

from bson import Binary
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from app.database import get_db
from app.dependencies import require_current_user
from app.models.booking import BookingCreate, BookingUpdate
from app.routers.groups import _message_out, get_member_group
from app.routers.trips import get_owned_trip
from app.services.booking_files import (
    MAX_FILE_BYTES, MAX_FILES_PER_BOOKING, delete_bookings_cascade, detect_type, safe_filename,
)
from app.services.chat_hub import hub
from app.services.notifications import object_id_or_none

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


# --------------------------------------------------------------------------------------------- serialising
def _attachment_out(doc: dict) -> dict:
    return {"id": str(doc["_id"]), "filename": doc["filename"], "content_type": doc["content_type"], "size": doc["size"]}


async def _attachments_by_booking(db, booking_ids: list) -> dict:
    out: dict = {bid: [] for bid in booking_ids}
    if booking_ids:
        cursor = db.booking_files.find({"booking_id": {"$in": booking_ids}}, {"data": 0}).sort("created_at", 1)
        async for f in cursor:
            out[f["booking_id"]].append(_attachment_out(f))
    return out


def serialize_booking(doc: dict, *, attachments: list | None = None, group_name: str | None = None,
                      created_by: str | None = None, can_edit: bool = True) -> dict:
    return {
        "id": str(doc["_id"]), "scope": "group" if doc.get("group_id") else "personal",
        "trip_id": str(doc["trip_id"]) if doc.get("trip_id") else None,
        "group_id": str(doc["group_id"]) if doc.get("group_id") else None, "group_name": group_name,
        "kind": doc["kind"], "title": doc["title"],
        "provider": doc.get("provider", ""), "reference": doc.get("reference", ""),
        "start_date": doc.get("start_date"), "end_date": doc.get("end_date"),
        "amount_inr": doc.get("amount_inr"), "notes": doc.get("notes", ""),
        "created_by": created_by, "can_edit": can_edit, "attachments": attachments or [],
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else None,
    }


async def _serialize_many(db, docs: list[dict], user: dict) -> list[dict]:
    """Serialises bookings for `user`, with attachments, group names, author names and edit rights."""
    attachments = await _attachments_by_booking(db, [d["_id"] for d in docs])
    group_ids = {d["group_id"] for d in docs if d.get("group_id")}
    groups = {g["_id"]: g async for g in db.groups.find({"_id": {"$in": list(group_ids)}}, {"name": 1, "owner_id": 1})}
    author_ids = {d["user_id"] for d in docs if d.get("group_id")}
    authors = {u["_id"]: u.get("name") or "Traveller" async for u in db.users.find({"_id": {"$in": list(author_ids)}}, {"name": 1})}
    out = []
    for d in docs:
        g = groups.get(d.get("group_id"))
        is_group = bool(d.get("group_id"))
        can_edit = d["user_id"] == user["_id"] or bool(g and g["owner_id"] == user["_id"])
        out.append(serialize_booking(
            d, attachments=attachments[d["_id"]], group_name=g["name"] if g else None,
            created_by=authors.get(d["user_id"], "Former member") if is_group else None, can_edit=can_edit))
    return out


def _fields(payload) -> dict:
    data = payload.model_dump(exclude={"trip_id", "group_id", "share_to_chat"})
    for key in ("start_date", "end_date"):
        if isinstance(data.get(key), date):
            data[key] = data[key].isoformat()
    return data


# --------------------------------------------------------------------------------------------- access rules
async def _get_booking(booking_id: str, user: dict, *, manage: bool = False) -> tuple[dict, dict | None]:
    """The booking and its group (None for personal ones). 404 unless the user may see it; 403 if `manage` and
    they may see but not change it. Personal bookings of other users and groups you are not in both look like 404."""
    oid = object_id_or_none(booking_id)
    if oid is None:
        raise HTTPException(status_code=400, detail="Invalid booking id.")
    db = get_db()
    doc = await db.bookings.find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if not doc.get("group_id"):
        if doc["user_id"] != user["_id"]:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return doc, None
    group = await db.groups.find_one({"_id": doc["group_id"], "member_ids": user["_id"]})
    if group is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if manage and doc["user_id"] != user["_id"] and group["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the member who added this booking, or the group owner, can change it.")
    return doc, group


# --------------------------------------------------------------------------------------------- chat card
async def _post_chat_card(db, group: dict, user: dict, doc: dict) -> None:
    """Posts a booking card into the group chat. Deliberately leaves out reference, amount and files."""
    card = {
        "id": str(doc["_id"]), "kind": doc["kind"], "title": doc["title"], "provider": doc.get("provider", ""),
        "start_date": doc.get("start_date"), "end_date": doc.get("end_date"),
    }
    message = {"group_id": group["_id"], "user_id": user["_id"], "kind": "booking", "booking": card,
               "text": f"Shared a booking: {doc['title']}", "created_at": datetime.now(timezone.utc)}
    result = await db.group_messages.insert_one(message)
    out = _message_out({**message, "_id": result.inserted_id}, user["name"])
    await hub.broadcast_message(str(group["_id"]), out, str(user["_id"]))


# --------------------------------------------------------------------------------------------- routes
@router.get("")
async def list_bookings(
    trip_id: str | None = Query(None, min_length=24, max_length=24),
    group_id: str | None = Query(None, min_length=24, max_length=24),
    user: dict = Depends(require_current_user),
):
    """No filter: the user's personal bookings plus the bookings of every group they are in."""
    db = get_db()
    if trip_id and group_id:
        raise HTTPException(status_code=422, detail="Filter by a trip or a group, not both.")
    if trip_id:
        trip = await get_owned_trip(trip_id, user)
        query: dict = {"user_id": user["_id"], "trip_id": trip["_id"]}
    elif group_id:
        group = await get_member_group(group_id, user)
        query = {"group_id": group["_id"]}
    else:
        member_of = [g["_id"] async for g in db.groups.find({"member_ids": user["_id"]}, {"_id": 1})]
        query = {"$or": [{"user_id": user["_id"], "group_id": {"$exists": False}}, {"group_id": {"$in": member_of}}]}
    docs = [d async for d in db.bookings.find(query).sort("created_at", -1)]
    return {"bookings": await _serialize_many(db, docs, user)}


@router.post("", status_code=201)
async def create_booking(payload: BookingCreate, user: dict = Depends(require_current_user)):
    db = get_db()
    doc = {**_fields(payload), "user_id": user["_id"], "created_at": datetime.now(timezone.utc)}
    group = None
    if payload.group_id:
        group = await get_member_group(payload.group_id, user)      # you can only add to groups you belong to
        doc["group_id"] = group["_id"]
    else:
        trip = await get_owned_trip(payload.trip_id, user)          # ...or to your own trips
        doc["trip_id"] = trip["_id"]
    result = await db.bookings.insert_one(doc)
    doc["_id"] = result.inserted_id
    if group and payload.share_to_chat:
        await _post_chat_card(db, group, user, doc)
    return {"booking": (await _serialize_many(db, [doc], user))[0]}


@router.put("/{booking_id}")
async def update_booking(booking_id: str, payload: BookingUpdate, user: dict = Depends(require_current_user)):
    doc, _ = await _get_booking(booking_id, user, manage=True)
    changes = _fields(payload)
    await get_db().bookings.update_one({"_id": doc["_id"]}, {"$set": changes})
    doc.update(changes)
    return {"booking": (await _serialize_many(get_db(), [doc], user))[0]}


@router.delete("/{booking_id}")
async def delete_booking(booking_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    doc, group = await _get_booking(booking_id, user, manage=True)
    await delete_bookings_cascade(db, {"_id": doc["_id"]})
    if group:
        # Cards that were shared into the chat would now point at nothing: mark them deleted, like a deleted message.
        async for card in db.group_messages.find({"group_id": group["_id"], "kind": "booking", "booking.id": str(doc["_id"]),
                                                  "deleted_at": {"$exists": False}}, {"_id": 1}):
            await db.group_messages.update_one({"_id": card["_id"]}, {"$set": {"deleted_at": datetime.now(timezone.utc), "text": ""}})
            await hub.broadcast_deleted(str(group["_id"]), str(card["_id"]))
    return {"deleted": True}


@router.post("/{booking_id}/share")
async def share_booking_to_chat(booking_id: str, user: dict = Depends(require_current_user)):
    """Posts a (group) booking into its group's chat. Any member may share; it can be shared again later."""
    db = get_db()
    doc, group = await _get_booking(booking_id, user)
    if group is None:
        raise HTTPException(status_code=409, detail="Only group bookings can be shared to a group chat.")
    await _post_chat_card(db, group, user, doc)
    return {"shared": True}


# ---- files
@router.post("/{booking_id}/files", status_code=201)
async def upload_file(booking_id: str, file: UploadFile = File(...), user: dict = Depends(require_current_user)):
    db = get_db()
    doc, _ = await _get_booking(booking_id, user, manage=True)
    if await db.booking_files.count_documents({"booking_id": doc["_id"]}) >= MAX_FILES_PER_BOOKING:
        raise HTTPException(status_code=409, detail=f"A booking can have at most {MAX_FILES_PER_BOOKING} files. Remove one first.")
    data = await file.read(MAX_FILE_BYTES + 1)                       # never read more than the limit
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"That file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise HTTPException(status_code=422, detail="That file is empty.")
    kind = detect_type(data)
    if kind is None:
        raise HTTPException(status_code=415, detail="Only PDF, PNG, JPEG and WebP files can be attached.")
    content_type, ext = kind
    record = {"booking_id": doc["_id"], "uploaded_by": user["_id"], "filename": safe_filename(file.filename, ext),
              "content_type": content_type, "size": len(data), "data": Binary(data), "created_at": datetime.now(timezone.utc)}
    result = await db.booking_files.insert_one(record)
    return {"attachment": _attachment_out({**record, "_id": result.inserted_id})}


@router.get("/{booking_id}/files/{file_id}")
async def download_file(booking_id: str, file_id: str, download: bool = False, user: dict = Depends(require_current_user)):
    """Streams a file to anyone who may see the booking. `?download=1` forces a download instead of opening it."""
    doc, _ = await _get_booking(booking_id, user)
    fid = object_id_or_none(file_id)
    record = await get_db().booking_files.find_one({"_id": fid, "booking_id": doc["_id"]}) if fid else None
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    disposition = "attachment" if download else "inline"
    ascii_name = record["filename"].encode("ascii", "replace").decode().replace("?", "_")   # headers must be latin-1 safe
    return Response(
        content=bytes(record["data"]), media_type=record["content_type"],
        headers={"Content-Disposition": f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(record['filename'])}",
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{booking_id}/files/{file_id}")
async def delete_file(booking_id: str, file_id: str, user: dict = Depends(require_current_user)):
    doc, _ = await _get_booking(booking_id, user, manage=True)
    fid = object_id_or_none(file_id)
    result = await get_db().booking_files.delete_one({"_id": fid, "booking_id": doc["_id"]}) if fid else None
    if result is None or result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found.")
    return {"deleted": True}