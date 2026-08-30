from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.database import get_db
from app.dependencies import require_current_user
from app.models.trip import TripCreate
from app.services.recommendation_engine import DF

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("")
async def get_trips(user: dict = Depends(require_current_user)):
    try:
        db = get_db()
        cursor = db.trips.find({"user_id": user["_id"]}).sort("created_at", -1)
        trips = [trip async for trip in cursor]
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not load trips: {exc}")

    for trip in trips:
        trip["id"] = str(trip.pop("_id"))
        trip["user_id"] = str(trip["user_id"])
        if isinstance(trip.get("created_at"), datetime):
            trip["created_at"] = trip["created_at"].isoformat()
    return {"trips": trips}


@router.post("", status_code=201)
async def create_trip(payload: TripCreate, user: dict = Depends(require_current_user)):
    destination = payload.destination.strip()
    if not destination:
        raise HTTPException(status_code=400, detail="Destination is required.")

    destination_row = DF[DF["Destination"].str.lower() == destination.lower()].head(1)
    if destination_row.empty:
        raise HTTPException(
            status_code=400, detail="Please choose a destination from the available suggestions."
        )
    row = destination_row.iloc[0]

    duration_value = payload.duration
    budget_value = payload.budget
    if duration_value is not None and not 1 <= duration_value <= 30:
        raise HTTPException(status_code=400, detail="Trip duration must be between 1 and 30 days.")
    if budget_value is not None and budget_value <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0.")

    trip = {
        "user_id": user["_id"],
        "destination": row["Destination"],
        "state": row["State"],
        "region": row["Region"],
        "latitude": float(row["Latitude"]),
        "longitude": float(row["Longitude"]),
        "duration": duration_value,
        "budget": budget_value,
        "traveller_type": payload.traveller_type,
        "source": payload.source or "known-destination",
        "created_at": datetime.now(timezone.utc),
        "status": "upcoming",
    }

    try:
        db = get_db()
        result = await db.trips.insert_one(trip)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not save trip: {exc}")

    trip["id"] = str(result.inserted_id)
    trip.pop("_id", None)
    trip["user_id"] = str(trip["user_id"])
    trip["created_at"] = trip["created_at"].isoformat()
    return {"trip": trip}
