"""
Trip map data.

  GET  /api/trips/{trip_id}/map             everything the map needs for one trip, in one light call
  POST /api/trips/{trip_id}/map/distances   driving distance/time from the user's location to the trip's places

The map call returns the destination centre, the top-5 places WITH coordinates, and the stays the user shortlisted.
It never calls Geoapify, so opening the map costs no API credits. (Live stay suggestions are a separate, optional
request the page makes only when the user switches that layer on.)

The distances call is only made after the user presses "Show my location" (see services/map_service.py for how its
cost and privacy are kept small). Login is required and the trip must belong to the logged-in user for both.
"""
from fastapi import APIRouter, Depends

from app.database import get_db
from app.dependencies import require_current_user
from app.models.map import OriginRequest
from app.routers.trips import get_owned_trip
from app.services.map_service import drive_distances
from app.services.places_service import get_top_places
from app.services.stay_service import build_anchor, list_saved_stays

router = APIRouter(prefix="/api/trips/{trip_id}/map", tags=["map"])


def _valid_point(lat, lon) -> bool:
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and -90 <= lat <= 90 and -180 <= lon <= 180


async def _places_and_saved(trip: dict, db) -> tuple[list[dict], list[dict]]:
    # build_anchor already drops wrong geocodes that sit far away from the destination.
    located = {p["rank"]: p for p in build_anchor(trip)["places"]}
    places = []
    for place in get_top_places(trip["destination"], 5):
        spot = located.get(place["rank"], {})
        places.append({
            "rank": place["rank"],
            "name": place["place_name"],
            "category": place["category"],
            "rating": place["rating"],
            "duration_hrs": place["duration_hrs"],
            "description": place["description"],
            "lat": spot.get("lat"),
            "lon": spot.get("lon"),
        })

    saved = []
    for stay in await list_saved_stays(db, trip):
        if _valid_point(stay.get("lat"), stay.get("lon")):
            saved.append({k: stay.get(k) for k in (
                "key", "name", "type", "type_label", "stars", "address", "lat", "lon",
                "price_low_inr", "price_high_inr", "price_unit", "website", "maps_url",
            )})
    return places, saved


@router.get("")
async def get_trip_map(trip_id: str, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await get_owned_trip(trip_id, user, db)
    places, saved = await _places_and_saved(trip, db)
    return {
        "trip_id": str(trip["_id"]),
        "destination": trip["destination"],
        "center": {"lat": trip["latitude"], "lon": trip["longitude"]},
        "places": places,
        "saved_stays": saved,
    }


@router.post("/distances")
async def get_trip_distances(trip_id: str, payload: OriginRequest, user: dict = Depends(require_current_user)):
    db = get_db()
    trip = await get_owned_trip(trip_id, user, db)
    places, saved = await _places_and_saved(trip, db)

    targets = [("destination", trip["latitude"], trip["longitude"])]
    targets += [(f"place:{p['rank']}", p["lat"], p["lon"]) for p in places if _valid_point(p["lat"], p["lon"])]
    targets += [(f"stay:{s['key']}", s["lat"], s["lon"]) for s in saved]
    return await drive_distances(db, user["_id"], payload.lat, payload.lon, targets)