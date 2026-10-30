from datetime import date, datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import require_current_user
from app.models.limits import MAX_TRIP_LENGTH_DAYS
from app.models.packing import GenerateRequest, SetDatesRequest, UpdateItemsRequest
from app.routers.trips import get_owned_trip as _get_owned_trip
from app.services.packing_engine import REGION_CLIMATE, build_checklist, fetch_weather_summary

router = APIRouter(prefix="/api/trips/{trip_id}/packing-list", tags=["packing"])


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

    doc = await db.packing_lists.find_one({"trip_id": ObjectId(trip_id)})
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

    await db.packing_lists.update_one({"trip_id": object_id}, {"$set": doc}, upsert=True)
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

    result = await db.packing_lists.update_one(
        {"trip_id": object_id}, {"$set": {"items": items, "updated_at": now}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No packing list generated yet.")

    existing["items"] = items
    existing["updated_at"] = now
    return {"packing_list": _serialize(existing)}


@router.put("/dates")
async def set_trip_dates(
    trip_id: str, payload: SetDatesRequest, user: dict = Depends(require_current_user)
):
    """Attach travel dates to a trip so packing (and later, health) can use real forecasts."""
    db = get_db()
    trip = await _get_owned_trip(trip_id, user, db)

    try:
        start = date.fromisoformat(payload.start_date)
        end = date.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Dates must be valid dates in YYYY-MM-DD format.")

    if end < start:
        raise HTTPException(status_code=422, detail="The end date cannot be earlier than the start date.")
    if (end - start).days + 1 > MAX_TRIP_LENGTH_DAYS:
        raise HTTPException(status_code=422, detail=f"A trip can span at most {MAX_TRIP_LENGTH_DAYS} days.")
    today = date.today()
    if start < today - timedelta(days=5 * 365) or end > today + timedelta(days=3 * 365):
        raise HTTPException(status_code=422, detail="Please choose dates within the next three years.")

    await db.trips.update_one(
        {"_id": trip["_id"], "user_id": user["_id"]},
        {"$set": {"start_date": start.isoformat(), "end_date": end.isoformat()}},
    )
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}
