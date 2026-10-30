import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.health_alerts import get_alerts_for_state
from app.services.health_engine import IS_SYNTHETIC, get_state_profile
from app.services.recommendation_engine import DF

logger = logging.getLogger("travelsync.health")

# NOTE: prefix is /api/travel-health, not /api/health - /api/health is already the
# server health-check endpoint in routers/meta.py.
router = APIRouter(prefix="/api/travel-health", tags=["travel-health"])


@router.get("/{destination}")
async def travel_health(destination: str, month: int | None = Query(None, ge=1, le=12)):
    row = DF[DF["Destination"].str.lower() == destination.strip().lower()].head(1)
    if row.empty:
        raise HTTPException(status_code=404, detail="Please choose a destination from the available suggestions.")
    state = str(row.iloc[0]["State"])
    try:
        profile = get_state_profile(state, month)
        profile["current_alerts"] = get_alerts_for_state(state)   # section A: not ML
    except Exception:
        logger.exception("Travel health computation failed for %s", state)
        raise HTTPException(status_code=500, detail="Travel health information could not be prepared right now.")
    alerts = profile["current_alerts"]
    # Say plainly what each block of data is. Nothing here is a live or verified outbreak feed.
    profile["data_labels"] = {
        "historical_outbreaks": "Synthetic demo data - not real outbreaks" if IS_SYNTHETIC else "Historical reports (not live)",
        "historical_is_synthetic": IS_SYNTHETIC,
        "current_alerts": "Hand-maintained list from official sources - not a live feed",
        "current_alerts_verified": bool(alerts.get("verified")),
        "current_alerts_last_reviewed": alerts.get("last_reviewed"),
    }
    return {"destination": str(row.iloc[0]["Destination"]), **profile}
