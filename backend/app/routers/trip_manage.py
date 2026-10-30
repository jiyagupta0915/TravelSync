"""
Trip management: deleting a trip.

  DELETE /api/trips/{trip_id}   permanently deletes the trip and everything attached to it

Login is required and the trip must belong to the logged-in user.
"""
from fastapi import APIRouter, Depends

from app.database import get_db
from app.dependencies import require_current_user
from app.routers.trips import get_owned_trip

router = APIRouter(prefix="/api/trips", tags=["trips"])

# Collections whose documents carry a `trip_id` field pointing at the trip.
CASCADE_COLLECTIONS = ("packing_lists", "saved_stays", "bookings")


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await get_owned_trip(trip_id, user, db)

    # Children first, the trip last: if something fails half way, the trip is still there and the
    # user can simply press delete again (the handlers are idempotent). Group suggestions that were
    # turned into this trip are independent records and are intentionally left alone.
    for name in CASCADE_COLLECTIONS:
        await db[name].delete_many({"trip_id": trip["_id"]})
    await db.trips.delete_one({"_id": trip["_id"], "user_id": user["_id"]})
    return {"deleted": True}
