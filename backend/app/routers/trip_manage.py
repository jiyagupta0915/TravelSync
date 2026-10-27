"""
Trip management: deleting a trip.

  DELETE /api/trips/{trip_id}   permanently deletes the trip and everything attached to it

Login is required and the trip must belong to the logged-in user. This lives in its own
router so the existing trips.py (create / list) does not need to change.
"""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.database import get_db
from app.dependencies import require_current_user

router = APIRouter(prefix="/api/trips", tags=["trips"])

# Collections whose documents carry a `trip_id` field pointing at the trip.
# When the documents feature is added later, add its collections here.
CASCADE_COLLECTIONS = ("packing_lists", "saved_stays")


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, user: dict = Depends(require_current_user)):
    try:
        object_id = ObjectId(trip_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid trip id.")

    db = get_db()
    try:
        trip = await db.trips.find_one({"_id": object_id, "user_id": user["_id"]}, {"_id": 1})
        if trip is None:
            raise HTTPException(status_code=404, detail="Trip not found.")

        # Children first, the trip last: if something fails half way, the trip is still
        # there and the user can simply press delete again.
        for name in CASCADE_COLLECTIONS:
            await db[name].delete_many({"trip_id": object_id})
        await db.trips.delete_one({"_id": object_id, "user_id": user["_id"]})
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Could not delete the trip right now. Please try again.")

    return {"deleted": True}