"""
Smart Stay Recommendations endpoint.

  GET    /api/trips/{trip_id}/stays                 ranked stays near the trip destination's top-5 places
  GET    /api/trips/{trip_id}/stays/saved           the stays the user added to this trip
  POST   /api/trips/{trip_id}/stays/saved           add a stay to the trip   {"stay_key": "..."}
  DELETE /api/trips/{trip_id}/stays/saved/{key}     remove a stay from the trip

Login is required and the trip must belong to the logged-in user (same rule as packing).
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.database import get_db
from app.dependencies import require_current_user
from app.models.stay import SaveStayRequest
from app.services.stay_service import (
    StayError, build_stay_recommendations, list_saved_stays, remove_saved_stay, save_stay,
)

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


@router.get("/saved")
async def get_saved_stays(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)
    try:
        return {"saved": await list_saved_stays(db, trip)}
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Could not load your saved stays right now.")


@router.post("/saved", status_code=201)
async def add_saved_stay(trip_id: str, payload: SaveStayRequest, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)
    try:
        return {"stay": await save_stay(db, trip, payload.stay_key)}
    except StayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.user_message)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Could not save this stay right now. Please try again.")


@router.delete("/saved/{stay_key}")
async def delete_saved_stay(trip_id: str, stay_key: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)
    try:
        removed = await remove_saved_stay(db, trip, stay_key)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Could not remove this stay right now. Please try again.")
    if not removed:
        raise HTTPException(status_code=404, detail="That stay isn't saved on this trip.")
    return {"removed": True}