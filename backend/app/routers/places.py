from fastapi import APIRouter, HTTPException, Query

from app.models.place_schemas import TopPlacesResponse
from app.services.places_service import get_top_places

# "/api" prefix matches every other TravelSync router (the frontend calls /api/...)
router = APIRouter(prefix="/api", tags=["places"])


@router.get("/places/{destination}", response_model=TopPlacesResponse)
async def top_places(destination: str, limit: int = Query(5, ge=1, le=5)):
    places = get_top_places(destination, limit)
    if not places:
        raise HTTPException(status_code=404, detail=f"No places found for '{destination}'")
    return {"destination": destination, "places": places}
