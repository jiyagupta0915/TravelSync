from fastapi import APIRouter, HTTPException, Path, Query

from app.services.destination_info import get_destination_profile
from app.services.recommendation_engine import DF, STARTING, search_start_locations

router = APIRouter(prefix="/api", tags=["destinations"])


@router.get("/destinations/search")
async def destination_search(q: str = Query("", max_length=100), limit: int = Query(10)):
    query = q.strip().lower()
    try:
        limit = min(max(int(limit), 1), 20)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be an integer")

    if not query:
        rows = DF.head(limit)
    else:
        mask = (
            DF["Destination"].str.lower().str.contains(query, regex=False)
            | DF["State"].str.lower().str.contains(query, regex=False)
        )
        rows = DF[mask].head(limit)

    columns = ["Destination", "State", "Region", "Latitude", "Longitude", "Ideal_Days", "Avg_Daily_Budget_INR"]
    return {"results": rows[columns].to_dict("records")}


@router.get("/destinations/{name}")
async def destination_profile(name: str = Path(max_length=120)):
    """Overview of one destination from the bundled dataset: where it is, typical stay and daily budget, what it is
    known for and who it suits. Declared after /destinations/search so that path keeps working."""
    profile = get_destination_profile(name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No destination called '{name}' was found.")
    return {"destination": profile}


@router.get("/start-locations/search")
async def start_locations_search(q: str = Query("", max_length=100), limit: int = Query(15)):
    try:
        limit = min(max(int(limit), 1), 15)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be an integer")
    return {"results": search_start_locations(STARTING, q, limit)}
