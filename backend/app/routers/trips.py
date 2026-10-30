from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import require_current_user
from app.models.trip import TripCreate
from app.services.recommendation_engine import DF

router = APIRouter(prefix="/api/trips", tags=["trips"])


async def enrich_trips(db, trips: list[dict], user: dict) -> list[dict]:
    """Adds `booking_count` and `companions` (display names of the other members of the trip's group, only while
    the viewer is still a member of that group) to serialized trips."""
    if not trips:
        return trips
    trip_ids = [ObjectId(t["id"]) for t in trips]
    counts = {}
    async for row in db.bookings.aggregate([{"$match": {"user_id": user["_id"], "trip_id": {"$in": trip_ids}}},
                                            {"$group": {"_id": "$trip_id", "n": {"$sum": 1}}}]):
        counts[str(row["_id"])] = row["n"]
    group_ids = list({t["group_id"] for t in trips if t.get("group_id")})
    companions: dict = {}
    if group_ids:
        groups = [g async for g in db.groups.find({"_id": {"$in": [ObjectId(g) for g in group_ids]}, "member_ids": user["_id"]})]
        names = {u["_id"]: u.get("name", "Traveller") async for u in db.users.find(
            {"_id": {"$in": list({m for g in groups for m in g["member_ids"]})}}, {"name": 1})}
        for g in groups:
            companions[str(g["_id"])] = [names.get(m, "Traveller") for m in g["member_ids"] if m != user["_id"]]
    for t in trips:
        t["booking_count"] = counts.get(t["id"], 0)
        t["companions"] = companions.get(t.get("group_id"), []) if t.get("group_id") else []
    return trips


def serialize_trip(trip: dict) -> dict:
    trip = dict(trip)
    trip["id"] = str(trip.pop("_id"))
    trip["user_id"] = str(trip["user_id"])
    if trip.get("group_id"):
        trip["group_id"] = str(trip["group_id"])
    if isinstance(trip.get("created_at"), datetime):
        trip["created_at"] = trip["created_at"].isoformat()
    return trip



async def get_owned_trip(trip_id: str, user: dict, db=None) -> dict:
    """The one place that proves a trip belongs to the logged-in user (404 for both 'missing' and 'not yours')."""
    try:
        object_id = ObjectId(trip_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid trip id.")

    database = db if db is not None else get_db()

    trip = await database.trips.find_one({
        "_id": object_id,
        "user_id": user["_id"]
    })

    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    return trip


@router.get("")
async def get_trips(user: dict = Depends(require_current_user)):
    cursor = get_db().trips.find({"user_id": user["_id"]}).sort("created_at", -1)
    trips = [serialize_trip(trip) async for trip in cursor]
    return {"trips": await enrich_trips(get_db(), trips, user)}


@router.get("/{trip_id}")
async def get_trip(trip_id: str, user: dict = Depends(require_current_user)):
    trip = serialize_trip(await get_owned_trip(trip_id, user))
    return {"trip": (await enrich_trips(get_db(), [trip], user))[0]}


@router.post("", status_code=201)
async def create_trip(payload: TripCreate, user: dict = Depends(require_current_user)):
    destination = payload.destination
    if not destination:
        raise HTTPException(status_code=400, detail="Destination is required.")

    destination_row = DF[DF["Destination"].str.lower() == destination.lower()].head(1)
    if destination_row.empty:
        raise HTTPException(status_code=400, detail="Please choose a destination from the available suggestions.")
    row = destination_row.iloc[0]

    trip = {
        "user_id": user["_id"],                      # always the session user, never a client value
        "destination": row["Destination"],
        "state": row["State"],
        "region": row["Region"],
        "latitude": float(row["Latitude"]),
        "longitude": float(row["Longitude"]),
        "duration": payload.duration,
        "budget": payload.budget,
        "traveller_type": payload.traveller_type,
        "source": payload.source or "known-destination",
        "created_at": datetime.now(timezone.utc),
        "status": "upcoming",
    }
    if payload.group_id:
        from app.routers.groups import get_member_group      # membership is verified, never assumed
        group = await get_member_group(payload.group_id, user)
        trip["group_id"] = group["_id"]
    result = await get_db().trips.insert_one(trip)
    trip["_id"] = result.inserted_id
    return {"trip": (await enrich_trips(get_db(), [serialize_trip(trip)], user))[0]}
