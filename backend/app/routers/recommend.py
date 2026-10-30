import logging

from fastapi import APIRouter, HTTPException

from app.models.recommend import RecommendRequest
from app.services.recommendation_engine import recommend_destinations

logger = logging.getLogger("travelsync.recommend")

# Intentionally public (no login needed): it only ranks the bundled destination dataset and
# touches no user data. Every input is bounded by RecommendRequest.
router = APIRouter(prefix="/api", tags=["recommend"])


@router.post("/recommend")
async def recommend(payload: RecommendRequest):
    try:
        top_n = min(max(int(payload.top_n or 6), 1), 10)
        results = recommend_destinations(
            preferences=payload.preferences,
            importance=payload.importance,
            traveller_type=payload.traveller_type,
            duration=payload.duration,
            budget=payload.budget,
            start_lat=payload.start_lat,
            start_lon=payload.start_lon,
            max_distance_km=payload.max_distance_km,
            top_n=top_n,
        )
    except (TypeError, ValueError) as exc:          # messages come from our own validation, safe to show
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Recommendation engine failed")
        raise HTTPException(status_code=500, detail="Recommendations could not be prepared right now. Please try again.")
    return {
        "count": len(results),
        "recommendations": results,
        "rules": {
            "duration": "Destinations within \u00b11 day receive the strongest duration score",
            "budget": "The entered budget is treated as a target range; nearby costs remain eligible",
            "distance": "Destinations within the selected maximum distance are preferred; a small tolerance is allowed",
        },
    }
