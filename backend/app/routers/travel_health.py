from fastapi import APIRouter, HTTPException, Query

from app.services.health_alerts import get_alerts_for_state
from app.services.health_engine import get_state_profile
from app.services.recommendation_engine import DF

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Travel health service error: {exc}")
    return {"destination": str(row.iloc[0]["Destination"]), **profile}
