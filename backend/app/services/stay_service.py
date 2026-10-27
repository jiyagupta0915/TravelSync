"""
Smart Stay Recommendations.

Pipeline for one trip:
  1. Anchor  - the destination's top-5 places (coordinates from the places CSV). If none have
               coordinates yet, we fall back to the destination centre.
  2. Fetch   - accommodation near the anchor from the Geoapify Places API (OpenStreetMap data).
               Cached in MongoDB for a week per destination, so the free credits last.
  3. Score   - every stay gets a 0-100 match score from four explainable parts:
                 location 40%   average distance to the top-5 places (Haversine)
                 budget   30%   estimated price per person vs the trip's nightly stay budget
                 traveller 20%  how well the stay type suits Family / Couple / Friends / Solo
                 quality  10%   star rating (when OpenStreetMap has it) + listing completeness
  4. Explain - each stay carries plain-English reasons so the UI can show *why* it was picked.

No machine learning here on purpose: the scoring is transparent and easy to defend.

PRICES ARE ESTIMATES. Neither Geoapify nor OpenStreetMap provides live prices or availability.
We estimate a price band from the stay type + star rating, scaled by how expensive the
destination is, and always label it "estimate" in the UI.
"""

import hashlib
import logging
import math
import re
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from app.config import settings
from app.services.places_service import _load_places, get_top_places
from app.services.recommendation_engine import DF

# httpx logs full request URLs at INFO level; our URL contains the API key, so keep that quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("travelsync.stays")

PLACES_URL = "https://api.geoapify.com/v2/places"
ACCOMMODATION_CATEGORIES = ",".join(
    f"accommodation.{kind}" for kind in ("hotel", "hostel", "guest_house", "apartment", "motel", "chalet", "hut")
)
SEARCH_RADII_KM = (8, 20, 40)   # widen the search for small towns with few listings
MIN_STAYS_WANTED = 8
FETCH_LIMIT = 60
CACHE_TTL = timedelta(days=7)
MAX_RESULTS = 18
MAX_SAVED_STAYS = 10
MAX_PLACE_DISTANCE_FROM_CENTRE_KM = 150   # ignore obviously wrong place coordinates

STAY_SHARE_OF_BUDGET = 0.45     # share of the all-in trip budget we assume goes on accommodation
WEIGHTS = {"location": 0.40, "budget": 0.30, "traveller": 0.20, "quality": 0.10}

TYPE_LABELS = {
    "hotel": "Hotel", "hostel": "Hostel", "guest_house": "Guest house", "apartment": "Apartment",
    "motel": "Motel", "chalet": "Chalet", "hut": "Hut", "other": "Stay",
}

# Typical price (INR per room per night, per bed for hostels) in an average-cost destination.
BASE_PRICE_BY_TYPE = {
    "hostel": 500, "guest_house": 1300, "hut": 1000, "apartment": 2200,
    "motel": 1500, "chalet": 2500, "hotel": 1800, "other": 1500,
}
BASE_PRICE_BY_STARS = {1: 900, 2: 1400, 3: 2400, 4: 5000, 5: 9500}
PEOPLE_PER_ROOM = {"Solo": 1, "Couple": 2, "Friends": 2, "Family": 3}

TRAVELLER_PHRASE = {"Family": "families", "Couple": "couples", "Friends": "groups of friends", "Solo": "solo travellers"}

# How well each stay type suits each traveller type (0-1).
TRAVELLER_FIT = {
    "Solo":    {"hostel": 1.0, "guest_house": 0.85, "hut": 0.6, "motel": 0.6, "apartment": 0.6, "chalet": 0.5, "hotel": 0.7, "hotel_good": 0.55, "other": 0.6},
    "Couple":  {"hostel": 0.45, "guest_house": 0.85, "hut": 0.6, "motel": 0.6, "apartment": 0.8, "chalet": 0.95, "hotel": 0.7, "hotel_good": 0.9, "other": 0.6},
    "Friends": {"hostel": 0.9, "guest_house": 0.85, "hut": 0.7, "motel": 0.6, "apartment": 0.95, "chalet": 0.85, "hotel": 0.75, "hotel_good": 0.8, "other": 0.6},
    "Family":  {"hostel": 0.3, "guest_house": 0.75, "hut": 0.4, "motel": 0.6, "apartment": 0.95, "chalet": 0.85, "hotel": 0.75, "hotel_good": 0.95, "other": 0.6},
}

_MEDIAN_DAILY_BUDGET = float(DF["Avg_Daily_Budget_INR"].median())
_DAILY_BUDGET_BY_DESTINATION = {
    str(name).strip().lower(): float(value)
    for name, value in zip(DF["Destination"], DF["Avg_Daily_Budget_INR"])
}


class StayError(Exception):
    """An error whose message is safe to show to the end user."""

    def __init__(self, user_message: str, status_code: int = 502):
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code


# ---------------------------------------------------------------- small helpers
def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _round100(value: float) -> int:
    return int(round(value / 100.0) * 100)


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"yes", "true", "wlan", "wifi", "wired", "free"}


def _parse_stars(*values):
    for value in values:
        match = re.search(r"\d(?:\.\d)?", str(value)) if value not in (None, "") else None
        if match:
            stars = float(match.group())
            if 1 <= stars <= 5:
                return stars
    return None

def make_stay_key(name: str, lat: float, lon: float) -> str:
    """A stable id for one stay (same hotel -> same key), used to save/remove it on a trip."""
    raw = f"{name.strip().lower()}|{round(float(lat), 4)}|{round(float(lon), 4)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

def _clean_url(value) -> str | None:
    url = str(value or "").strip()
    if not url or " " in url:
        return None
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


# ---------------------------------------------------------------- 1. anchor (top-5 places)
def build_anchor(trip: dict) -> dict:
    """Coordinates of the destination's top-5 places, plus the point we search around."""
    names = [p["place_name"] for p in get_top_places(trip["destination"], 5)]
    df = _load_places()
    subset = df[df["Destination_Key"] == trip["destination"].strip().lower()]

    places = []
    for rank, name in enumerate(names, start=1):
        lat = lon = None
        if "Latitude" in subset.columns:
            row = subset[subset["Place_Name"] == name].head(1)
            if not row.empty and pd.notna(row.iloc[0]["Latitude"]) and pd.notna(row.iloc[0]["Longitude"]):
                lat, lon = float(row.iloc[0]["Latitude"]), float(row.iloc[0]["Longitude"])
                # Guard against a wrong geocode far away from the destination.
                if _haversine_km(trip["latitude"], trip["longitude"], lat, lon) > MAX_PLACE_DISTANCE_FROM_CENTRE_KM:
                    lat = lon = None
        places.append({"rank": rank, "name": name, "lat": lat, "lon": lon})

    located = [p for p in places if p["lat"] is not None]
    if located:
        lat = sum(p["lat"] for p in located) / len(located)
        lon = sum(p["lon"] for p in located) / len(located)
        basis = "top_places"
    else:
        lat, lon, basis = trip["latitude"], trip["longitude"], "destination_centre"
    return {"lat": lat, "lon": lon, "basis": basis, "places": places}


# ---------------------------------------------------------------- 2. fetch + cache
def _normalise(feature: dict) -> dict | None:
    """Turns one Geoapify feature into the small, stable shape we cache and score."""
    props = feature.get("properties") or {}
    name = (props.get("name") or "").strip()
    lat, lon = props.get("lat"), props.get("lon")
    if not name or lat is None or lon is None:
        return None                                  # unnamed OpenStreetMap entries are useless to show

    raw = (props.get("datasource") or {}).get("raw") or {}
    facilities = props.get("facilities") or {}
    categories = props.get("categories") or []
    kind = "other"
    for key in TYPE_LABELS:
        if f"accommodation.{key}" in categories:
            kind = key
            break

    contact = props.get("contact") or {}
    return {
        "name": name,
        "type": kind,
        "stars": _parse_stars(raw.get("stars"), (props.get("accommodation") or {}).get("stars"), props.get("stars")),
        "lat": float(lat),
        "lon": float(lon),
        "address": props.get("address_line2") or props.get("formatted") or "",
        "website": _clean_url(props.get("website") or contact.get("website") or raw.get("website") or raw.get("contact:website")),
        "phone": (contact.get("phone") or props.get("phone") or raw.get("phone") or raw.get("contact:phone") or None),
        "wifi": _truthy(facilities.get("internet_access", raw.get("internet_access"))),
        "ac": _truthy(facilities.get("air_conditioning", raw.get("air_conditioning"))),
    }


async def _fetch_from_geoapify(lat: float, lon: float, radius_km: int) -> list[dict]:
    if not settings.geoapify_api_key:
        raise StayError("Stay search isn't set up yet (missing GEOAPIFY_API_KEY on the server).", 503)

    params = {
        "categories": ACCOMMODATION_CATEGORIES,
        "filter": f"circle:{lon},{lat},{radius_km * 1000}",
        "bias": f"proximity:{lon},{lat}",
        "limit": FETCH_LIMIT,
        "lang": "en",
        "apiKey": settings.geoapify_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            response = await client.get(PLACES_URL, params=params)
    except httpx.TimeoutException:
        raise StayError("The stay search took too long. Please try again.", 504)
    except httpx.HTTPError as exc:
        logger.warning("Could not reach Geoapify: %s", type(exc).__name__)
        raise StayError("Couldn't reach the stay search service. Please try again in a moment.", 502)

    if response.status_code != 200:
        logger.warning("Geoapify returned HTTP %s: %s", response.status_code, response.text[:300])
        if response.status_code == 429:
            raise StayError("The stay search is busy right now (free daily limit reached). Please try again later.", 503)
        if response.status_code in (400, 401, 403):
            raise StayError("The stay search isn't configured correctly on the server (check GEOAPIFY_API_KEY).", 503)
        raise StayError("The stay search ran into a problem. Please try again.", 502)

    try:
        features = response.json().get("features") or []
    except ValueError:
        raise StayError("The stay search returned an unexpected answer. Please try again.", 502)

    seen, stays = set(), []
    for feature in features:
        stay = _normalise(feature)
        if stay is None:
            continue
        key = (stay["name"].lower(), round(stay["lat"], 4), round(stay["lon"], 4))
        if key not in seen:
            seen.add(key)
            stays.append(stay)
    return stays


async def get_candidates(db, destination: str, anchor: dict) -> tuple[list[dict], str]:
    """Stays near the anchor. Served from the MongoDB cache when fresh, else fetched live."""
    key = f"{destination.strip().lower()}|{anchor['basis']}"
    cached = await db.stay_cache.find_one({"_id": key})
    if cached:
        fetched_at = cached.get("fetched_at")
        if isinstance(fetched_at, datetime):
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - fetched_at < CACHE_TTL and cached.get("stays"):
                return cached["stays"], "cache"

    stays: list[dict] = []
    for radius in SEARCH_RADII_KM:
        stays = await _fetch_from_geoapify(anchor["lat"], anchor["lon"], radius)
        if len(stays) >= MIN_STAYS_WANTED:
            break

    if stays:   # never cache an empty answer, so a one-off glitch can't stick for a week
        await db.stay_cache.replace_one(
            {"_id": key},
            {"_id": key, "stays": stays, "fetched_at": datetime.now(timezone.utc)},
            upsert=True,
        )
    return stays, "live"


# ---------------------------------------------------------------- 3. scoring
def _price_factor(destination: str) -> float:
    daily = _DAILY_BUDGET_BY_DESTINATION.get(destination.strip().lower(), _MEDIAN_DAILY_BUDGET)
    return min(1.5, max(0.75, daily / _MEDIAN_DAILY_BUDGET))


def _estimate_price(stay: dict, factor: float, people: int) -> dict:
    stars = stay["stars"]
    if stars and stay["type"] in ("hotel", "motel", "other"):
        base = BASE_PRICE_BY_STARS[int(round(stars))]
    else:
        base = BASE_PRICE_BY_TYPE[stay["type"]]
    mid = base * factor
    is_bed = stay["type"] == "hostel"
    return {
        "mid": mid,
        "low": _round100(mid * 0.75),
        "high": _round100(mid * 1.3),
        "unit": "bed" if is_bed else "room",
        "per_person": mid if is_bed else mid / max(1, people),
    }


def _nightly_budget_per_person(trip: dict) -> tuple[float, str]:
    daily = _DAILY_BUDGET_BY_DESTINATION.get(trip["destination"].strip().lower(), _MEDIAN_DAILY_BUDGET)
    if trip.get("budget") and trip.get("duration"):
        return STAY_SHARE_OF_BUDGET * float(trip["budget"]) / int(trip["duration"]), "your trip budget"
    return STAY_SHARE_OF_BUDGET * daily, "this destination's typical budget"


def _budget_score(ratio: float) -> tuple[float, str]:
    if ratio <= 1.0:
        return (1.0 if ratio >= 0.35 else 0.85), "within"
    if ratio <= 1.6:
        return 1.0 - (ratio - 1.0) * (0.7 / 0.6), ("slightly_above" if ratio <= 1.3 else "above")
    return 0.1, "above"


def _traveller_score(stay: dict, traveller_type: str | None) -> float:
    table = TRAVELLER_FIT.get(traveller_type or "")
    if table is None:
        return 0.7                                    # traveller type unknown: neutral
    kind = stay["type"]
    if kind == "hotel" and (stay["stars"] or 0) >= 3:
        kind = "hotel_good"
    return table[kind]


def _quality_score(stay: dict) -> float:
    base = (stay["stars"] / 5.0) if stay["stars"] else 0.45
    bonus = 0.1 * bool(stay["website"]) + 0.05 * bool(stay["phone"]) + 0.05 * bool(stay["wifi"])
    return min(1.0, base + bonus)


def _score_stay(stay: dict, trip: dict, anchor: dict, nightly_budget: float, factor: float) -> dict:
    targets = [(p["name"], p["lat"], p["lon"]) for p in anchor["places"] if p["lat"] is not None]
    if not targets:
        targets = [("the destination centre", anchor["lat"], anchor["lon"])]
    distances = [(name, _haversine_km(stay["lat"], stay["lon"], lat, lon)) for name, lat, lon in targets]
    avg_km = sum(d for _, d in distances) / len(distances)
    nearest_name, nearest_km = min(distances, key=lambda item: item[1])

    people = PEOPLE_PER_ROOM.get(trip.get("traveller_type") or "", 2)
    price = _estimate_price(stay, factor, people)
    budget_ratio = price["per_person"] / nightly_budget if nightly_budget else 1.0
    budget_score, budget_fit = _budget_score(budget_ratio)

    parts = {
        "location": math.exp(-avg_km / 4.0),
        "budget": budget_score,
        "traveller": _traveller_score(stay, trip.get("traveller_type")),
        "quality": _quality_score(stay),
    }
    score = sum(WEIGHTS[name] * value for name, value in parts.items())
    return {
        "stay": stay, "score": score, "parts": parts, "avg_km": avg_km,
        "nearest_name": nearest_name, "nearest_km": nearest_km,
        "price": price, "budget_fit": budget_fit,
    }


def _reasons(item: dict, trip: dict, anchor: dict, nightly_budget: float) -> list[str]:
    stay, reasons = item["stay"], []
    where = "your top places" if anchor["basis"] == "top_places" else "the destination centre"
    if item["avg_km"] <= 2.5:
        reasons.append(f"Very close to {where} (about {item['avg_km']:.1f} km on average)")
    else:
        reasons.append(f"About {item['avg_km']:.1f} km from {where} on average")

    if item["budget_fit"] == "within":
        reasons.append(f"Fits your stay budget (about ₹{_round100(nightly_budget):,} per person per night)")
    elif item["budget_fit"] == "slightly_above":
        reasons.append("Slightly above your stay budget")
    else:
        reasons.append("Above your stay budget")

    if item["parts"]["traveller"] >= 0.85 and trip.get("traveller_type") in TRAVELLER_PHRASE:
        reasons.append(f"Well suited to {TRAVELLER_PHRASE[trip['traveller_type']]}")

    if stay["stars"]:
        reasons.append(f"{stay['stars']:g}-star rated on OpenStreetMap")
    elif stay["wifi"]:
        reasons.append("Wi-Fi listed")
    elif stay["website"]:
        reasons.append("Has a website you can check")
    return reasons[:4]


# ---------------------------------------------------------------- 4. public entry point
async def build_stay_recommendations(db, trip: dict) -> dict:
    anchor = build_anchor(trip)
    candidates, source = await get_candidates(db, trip["destination"], anchor)
    if not candidates:
        raise StayError(f"We couldn't find any stays listed near {trip['destination']} yet. "
                        "OpenStreetMap coverage is thin in some small towns.", 404)

    nightly_budget, budget_basis = _nightly_budget_per_person(trip)
    factor = _price_factor(trip["destination"])

    scored = [_score_stay(stay, trip, anchor, nightly_budget, factor) for stay in candidates]
    scored.sort(key=lambda item: (-item["score"], item["avg_km"]))

    stays = []
    for rank, item in enumerate(scored[:MAX_RESULTS], start=1):
        stay, price = item["stay"], item["price"]
        stays.append({
            "key": make_stay_key(stay["name"], stay["lat"], stay["lon"]),
            "rank": rank,
            "name": stay["name"],
            "type": stay["type"],
            "type_label": TYPE_LABELS[stay["type"]],
            "stars": stay["stars"],
            "address": stay["address"],
            "website": stay["website"],
            "phone": stay["phone"],
            "wifi": stay["wifi"],
            "ac": stay["ac"],
            "lat": stay["lat"],
            "lon": stay["lon"],
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={stay['lat']},{stay['lon']}",
            "match_percent": round(item["score"] * 100),
            "avg_distance_km": round(item["avg_km"], 1),
            "nearest_place": item["nearest_name"],
            "nearest_place_km": round(item["nearest_km"], 1),
            "price_low_inr": price["low"],
            "price_high_inr": price["high"],
            "price_unit": price["unit"],
            "price_is_estimate": True,
            "budget_fit": item["budget_fit"],
            "reasons": _reasons(item, trip, anchor, nightly_budget),
        })
    saved_keys = [doc["stay_key"] async for doc in db.saved_stays.find({"trip_id": trip["_id"]}, {"stay_key": 1})]

    return {
        "destination": trip["destination"],
        "traveller_type": trip.get("traveller_type"),
        "anchor": {"basis": anchor["basis"], "places": anchor["places"]},
        "nightly_budget_per_person_inr": _round100(nightly_budget),
        "budget_basis": budget_basis,
        "source": source,
        "stays": stays,
        "saved_keys": saved_keys,
        "attribution": "Stay data © OpenStreetMap contributors, powered by Geoapify. Prices are estimates.",
    }



# ---------------------------------------------------------------- 5. saved stays (the trip's shortlist)
async def list_saved_stays(db, trip: dict) -> list[dict]:
    cursor = db.saved_stays.find({"trip_id": trip["_id"]}).sort("saved_at", 1)
    return [doc["stay"] async for doc in cursor]


async def save_stay(db, trip: dict, stay_key: str) -> dict:
    """Adds one of the currently recommended stays to the trip. Saving twice is harmless."""
    existing = await db.saved_stays.find_one({"trip_id": trip["_id"], "stay_key": stay_key})
    if existing:
        return existing["stay"]

    # Look the stay up on the server (served from the cache), never trust details from the browser.
    result = await build_stay_recommendations(db, trip)
    stay = next((item for item in result["stays"] if item["key"] == stay_key), None)
    if stay is None:
        raise StayError("That stay isn't in the current results any more. Please refresh the page.", 404)

    if await db.saved_stays.count_documents({"trip_id": trip["_id"]}) >= MAX_SAVED_STAYS:
        raise StayError(f"You can save up to {MAX_SAVED_STAYS} stays per trip. Remove one first.", 400)

    await db.saved_stays.update_one(
        {"trip_id": trip["_id"], "stay_key": stay_key},
        {"$setOnInsert": {"user_id": trip["user_id"], "stay": stay, "saved_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return stay


async def remove_saved_stay(db, trip: dict, stay_key: str) -> bool:
    result = await db.saved_stays.delete_one({"trip_id": trip["_id"], "stay_key": stay_key})
    return result.deleted_count > 0