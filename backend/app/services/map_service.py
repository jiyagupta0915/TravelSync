"""
Driving distances and times from the user's location to a trip's places (Geoapify Route Matrix API).

Cost control (Geoapify's free plan is 3,000 credits/day; one origin and N targets costs about N credits,
plus 1 credit per 500 km of each returned distance):
  * the origin is rounded to 2 decimals (about 1 km) before anything is sent or cached, which also protects privacy;
  * answers are cached for 24 h under a key made from the ROUNDED origin and the target coordinates only. The key
    holds no user id and no trip id, so the cache is never linked to an account;
  * each user may trigger a limited number of live (uncached) lookups per hour;
  * on ANY problem we answer "unavailable" (HTTP 200) and the page falls back to free straight-line distances.
"""
import hashlib
import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config import settings
from app.core.rate_limit import FailureLimiter

# httpx logs full request URLs at INFO level; our URL contains the API key, so keep that quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MATRIX_URL = "https://api.geoapify.com/v1/routematrix"
ORIGIN_DECIMALS = 2
MAX_TARGETS = 20

# Live (uncached) lookups per user per hour. Reusing FailureLimiter: it is just a sliding-window counter.
live_lookups = FailureLimiter(max_failures=20, window_seconds=60 * 60)


def _unavailable(reason: str) -> dict:
    return {"source": "unavailable", "reason": reason, "distances": {}}


def _cache_key(lat: float, lon: float, targets: list[tuple[str, float, float]]) -> str:
    parts = [f"{lat:.{ORIGIN_DECIMALS}f},{lon:.{ORIGIN_DECIMALS}f}"]
    parts += sorted(f"{tid}:{tlat:.4f},{tlon:.4f}" for tid, tlat, tlon in targets)
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def _parse(data: dict, targets: list[tuple[str, float, float]]) -> dict:
    rows = data.get("sources_to_targets") or []
    cells = rows[0] if rows and isinstance(rows[0], list) else []
    out = {}
    for position, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        index = cell.get("target_index", position)
        meters, seconds = cell.get("distance"), cell.get("time")
        if not isinstance(index, int) or not 0 <= index < len(targets):
            continue
        if not isinstance(meters, (int, float)) or not isinstance(seconds, (int, float)):
            continue   # no road route to this one: the page shows its straight-line distance instead
        out[targets[index][0]] = {"km": round(meters / 1000, 1), "minutes": max(1, round(seconds / 60))}
    return out


async def drive_distances(db, user_id, lat: float, lon: float, targets: list[tuple[str, float, float]]) -> dict:
    """targets: [(id, lat, lon)]. Returns {"source": "geoapify"|"cache"|"unavailable", "distances": {id: {km, minutes}}}."""
    targets = targets[:MAX_TARGETS]
    if not targets:
        return _unavailable("no_targets")
    if not settings.geoapify_api_key:
        return _unavailable("not_configured")

    lat, lon = round(lat, ORIGIN_DECIMALS), round(lon, ORIGIN_DECIMALS)
    key = _cache_key(lat, lon, targets)

    cached = await db.map_distance_cache.find_one({"_id": key})
    if cached and cached.get("distances"):
        return {"source": "cache", "distances": cached["distances"]}

    try:
        live_lookups.check(str(user_id))
    except HTTPException:
        return _unavailable("rate_limited")
    live_lookups.record(str(user_id))

    body = {
        "mode": "drive",
        "sources": [{"location": [lon, lat]}],
        "targets": [{"location": [tlon, tlat]} for _, tlat, tlon in targets],
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            response = await client.post(MATRIX_URL, params={"apiKey": settings.geoapify_api_key}, json=body)
    except httpx.HTTPError as exc:
        logger.warning("Could not reach Geoapify route matrix: %s", type(exc).__name__)
        return _unavailable("unreachable")

    if response.status_code != 200:
        logger.warning("Geoapify route matrix returned HTTP %s: %s", response.status_code, response.text[:300])
        return _unavailable("daily_limit" if response.status_code == 429 else "service_error")

    try:
        distances = _parse(response.json(), targets)
    except ValueError:
        return _unavailable("service_error")
    if not distances:
        return _unavailable("no_route")

    await db.map_distance_cache.replace_one(
        {"_id": key}, {"_id": key, "distances": distances, "fetched_at": datetime.now(timezone.utc)}, upsert=True,
    )
    return {"source": "geoapify", "distances": distances}