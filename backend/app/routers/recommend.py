from fastapi import APIRouter, HTTPException

from app.models.recommend import RecommendRequest
from app.services.recommendation_engine import recommend_destinations

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
        return {
            "count": len(results),
            "recommendations": results,
            "rules": {
                "duration": "Destinations within \u00b11 day receive the strongest duration score",
                "budget": "The entered budget is treated as a target range; nearby costs remain eligible",
                "distance": "Destinations within the selected maximum distance are preferred; a small tolerance is allowed",
            },
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendation service error: {exc}")
