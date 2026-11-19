"""
Trip management: deleting a trip.

  DELETE /api/trips/{trip_id}   permanently deletes the trip and everything attached to it

Login is required and the trip must belong to the logged-in user.
"""
from fastapi import APIRouter, Depends

from app.database import get_db
from app.dependencies import require_current_user
from app.services.booking_files import delete_bookings_cascade
from app.routers.trips import get_owned_trip

router = APIRouter(prefix="/api/trips", tags=["trips"])

# Collections whose documents carry a `trip_id` field pointing at the trip.
CASCADE_COLLECTIONS = ("packing_lists", "saved_stays")
from app.models.limits import MAX_DURATION_DAYS
from app.models.trip import TripUpdate
from app.routers.trips import check_trip_dates, enrich_trips, get_owned_trip, serialize_trip
from app.routers.packing import refresh_packing_list

@router.patch("/{trip_id}")
async def update_trip(trip_id: str, payload: TripUpdate, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await get_owned_trip(trip_id, user, db)
    sent = payload.model_fields_set
    sets, unsets = {}, {}

    if "budget" in sent:
        sets["budget"] = payload.budget
    if "duration" in sent:
        sets["duration"] = payload.duration
    if "start_date" in sent:
        if payload.start_date:
            sets["duration"] = check_trip_dates(payload.start_date, payload.end_date)  # dates win over a typed duration
            sets["start_date"] = payload.start_date.isoformat()
            sets["end_date"] = payload.end_date.isoformat()
        else:
            unsets = {"start_date": "", "end_date": ""}
    if not sets and not unsets:
        raise HTTPException(400, "Nothing to update.")

    op = {k: v for k, v in (("$set", sets), ("$unset", unsets)) if v}
    await db.trips.update_one({"_id": trip["_id"], "user_id": user["_id"]}, op)
    updated = await db.trips.find_one({"_id": trip["_id"]})

    # Days or dates change the packing advice, so refresh an existing list (packed/custom items are kept).
    if ({"duration", "start_date", "end_date"} & (set(sets) | set(unsets))) and \
            await db.packing_lists.find_one({"trip_id": trip["_id"]}, {"_id": 1}):
        await refresh_packing_list(db, updated)

    return {"trip": (await enrich_trips(db, [serialize_trip(updated)], user))[0]}

@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await get_owned_trip(trip_id, user, db)

    # Children first, the trip last: if something fails half way, the trip is still there and the
    # user can simply press delete again (the handlers are idempotent). Group suggestions that were
    # turned into this trip are independent records and are intentionally left alone.
    await delete_bookings_cascade(db, {"trip_id": trip["_id"], "user_id": user["_id"]})   # bookings + their uploaded files
    for name in CASCADE_COLLECTIONS:
        await db[name].delete_many({"trip_id": trip["_id"]})
    await db.trips.delete_one({"_id": trip["_id"], "user_id": user["_id"]})
    return {"deleted": True}
