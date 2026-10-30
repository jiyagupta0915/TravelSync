"""
Bookings & tickets - a personal record of reservations the user has made ELSEWHERE (hotel, flight, train, bus,
activity, other). TravelSync does not sell, make or confirm bookings: `reference` is whatever confirmation number
the user typed in. Every record belongs to one user and to one of that user's trips.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.dependencies import require_current_user
from app.models.booking import BookingCreate, BookingUpdate
from app.routers.trips import get_owned_trip
from app.services.notifications import object_id_or_none

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def serialize_booking(doc: dict) -> dict:
    out = {
        "id": str(doc["_id"]), "trip_id": str(doc["trip_id"]), "kind": doc["kind"], "title": doc["title"],
        "provider": doc.get("provider", ""), "reference": doc.get("reference", ""),
        "start_date": doc.get("start_date"), "end_date": doc.get("end_date"),
        "amount_inr": doc.get("amount_inr"), "notes": doc.get("notes", ""),
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else None,
    }
    return out


def _fields(payload) -> dict:
    data = payload.model_dump(exclude={"trip_id"})
    for key in ("start_date", "end_date"):
        if isinstance(data.get(key), date):
            data[key] = data[key].isoformat()
    return data


async def _get_owned_booking(booking_id: str, user: dict) -> dict:
    oid = object_id_or_none(booking_id)
    if oid is None:
        raise HTTPException(status_code=400, detail="Invalid booking id.")
    doc = await get_db().bookings.find_one({"_id": oid, "user_id": user["_id"]})
    if doc is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return doc


@router.get("")
async def list_bookings(trip_id: str | None = Query(None, min_length=24, max_length=24), user: dict = Depends(require_current_user)):
    query: dict = {"user_id": user["_id"]}
    if trip_id:
        trip = await get_owned_trip(trip_id, user)
        query["trip_id"] = trip["_id"]
    cursor = get_db().bookings.find(query).sort("created_at", -1)
    return {"bookings": [serialize_booking(d) async for d in cursor]}


@router.post("", status_code=201)
async def create_booking(payload: BookingCreate, user: dict = Depends(require_current_user)):
    trip = await get_owned_trip(payload.trip_id, user)          # you can only attach bookings to your own trips
    doc = {**_fields(payload), "user_id": user["_id"], "trip_id": trip["_id"], "created_at": datetime.now(timezone.utc)}
    result = await get_db().bookings.insert_one(doc)
    doc["_id"] = result.inserted_id
    return {"booking": serialize_booking(doc)}


@router.put("/{booking_id}")
async def update_booking(booking_id: str, payload: BookingUpdate, user: dict = Depends(require_current_user)):
    doc = await _get_owned_booking(booking_id, user)
    changes = _fields(payload)
    await get_db().bookings.update_one({"_id": doc["_id"], "user_id": user["_id"]}, {"$set": changes})
    doc.update(changes)
    return {"booking": serialize_booking(doc)}


@router.delete("/{booking_id}")
async def delete_booking(booking_id: str, user: dict = Depends(require_current_user)):
    doc = await _get_owned_booking(booking_id, user)
    await get_db().bookings.delete_one({"_id": doc["_id"], "user_id": user["_id"]})
    return {"deleted": True}


