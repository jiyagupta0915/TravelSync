from datetime import date, datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.database import get_db
from app.dependencies import require_current_user
from app.models.packing import GenerateRequest, SetDatesRequest, UpdateItemsRequest
from app.services.packing_engine import REGION_CLIMATE, build_checklist, fetch_weather_summary

router = APIRouter(prefix="/api/trips/{trip_id}/packing-list", tags=["packing"])


async def _get_owned_trip(trip_id: str, user: dict, db) -> dict:
    try:
        object_id = ObjectId(trip_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid trip id.")

    trip = await db.trips.find_one({"_id": object_id, "user_id": user["_id"]})
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    doc["trip_id"] = str(doc["trip_id"])
    for key in ("generated_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


@router.get("")
async def get_packing_list(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    await _get_owned_trip(trip_id, user, db)

    try:
        doc = await db.packing_lists.find_one({"trip_id": ObjectId(trip_id)})
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not load packing list: {exc}")

    if doc is None:
        raise HTTPException(status_code=404, detail="No packing list generated yet.")
    return {"packing_list": _serialize(doc)}


@router.post("", status_code=201)
async def generate_packing_list(
    trip_id: str, payload: GenerateRequest, user: dict = Depends(require_current_user)
):
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)
    object_id = ObjectId(trip_id)

    existing = await db.packing_lists.find_one({"trip_id": object_id})
    if existing is not None and not payload.regenerate:
        raise HTTPException(
            status_code=409,
            detail="A packing list already exists for this trip. Pass regenerate=true to overwrite.",
        )

    tier, condition, weather_summary = "climate", None, None
    start_date, end_date = trip.get("start_date"), trip.get("end_date")

    if start_date and end_date:
        weather = await fetch_weather_summary(trip["latitude"], trip["longitude"], start_date, end_date)
        if weather is not None:
            tier = "forecast"
            condition = weather["condition"]
            weather_summary = (
                f"{weather['avg_min_temp']}-{weather['avg_max_temp']}°C, "
                f"{weather['avg_rain_probability']}% rain chance"
            )

    if condition is None:
        condition = REGION_CLIMATE.get(trip.get("region"), "mild")

    new_items = build_checklist(trip.get("duration"), condition, payload.activities)

    if existing is not None:
        # Merge: keep packed state and any custom items, replace rule-suggested ones.
        kept = [item for item in existing["items"] if item.get("packed") or item.get("source") == "custom"]
        kept_names = {item["name"] for item in kept}
        merged = kept + [item for item in new_items if item["name"] not in kept_names]
    else:
        merged = new_items

    now = datetime.now(timezone.utc)
    doc = {
        "trip_id": object_id,
        "tier": tier,
        "weather_summary": weather_summary,
        "items": merged,
        "generated_at": existing["generated_at"] if existing else now,
        "updated_at": now,
    }

    try:
        await db.packing_lists.update_one({"trip_id": object_id}, {"$set": doc}, upsert=True)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not save packing list: {exc}")

    return {"packing_list": _serialize(doc)}


@router.patch("")
async def update_packing_list(
    trip_id: str, payload: UpdateItemsRequest, user: dict = Depends(require_current_user)
):
    db = get_db()
    await _get_owned_trip(trip_id, user, db)
    object_id = ObjectId(trip_id)

    existing = await db.packing_lists.find_one({"trip_id": object_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="No packing list generated yet.")

    now = datetime.now(timezone.utc)
    items = [item.model_dump() for item in payload.items]

    try:
        await db.packing_lists.update_one(
            {"trip_id": object_id}, {"$set": {"items": items, "updated_at": now}}
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not update packing list: {exc}")

    existing["items"] = items
    existing["updated_at"] = now
    return {"packing_list": _serialize(existing)}


@router.put("/dates")
async def set_trip_dates(
    trip_id: str, payload: SetDatesRequest, user: dict = Depends(require_current_user)
):
    """Attach travel dates to a trip so packing (and later, health) can use real forecasts."""
    db = get_db()
    await _get_owned_trip(trip_id, user, db)

    try:
        date.fromisoformat(payload.start_date)
        date.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format.")

    try:
        await db.trips.update_one(
            {"_id": ObjectId(trip_id)},
            {"$set": {"start_date": payload.start_date, "end_date": payload.end_date}},
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not save trip dates: {exc}")

    return {"start_date": payload.start_date, "end_date": payload.end_date}