"""
Smart Stay Recommendations endpoint.

  GET /api/trips/{trip_id}/stays    ranked stays near the trip destination's top-5 places

Login is required and the trip must belong to the logged-in user (same rule as packing).
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.database import get_db
from app.dependencies import require_current_user
from app.services.stay_service import StayError, build_stay_recommendations

router = APIRouter(prefix="/api/trips/{trip_id}/stays", tags=["stays"])


async def _get_owned_trip(trip_id: str, user: dict, db) -> dict:
    try:
        object_id = ObjectId(trip_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid trip id.")

    trip = await db.trips.find_one({"_id": object_id, "user_id": user["_id"]})
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip


@router.get("")
async def get_trip_stays(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)
    try:
        return await build_stay_recommendations(db, trip)
    except StayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.user_message)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Could not load stay data right now. Please try again.")