from fastapi import APIRouter, HTTPException, Query

from app.services.recommendation_engine import DF, STARTING, search_start_locations

router = APIRouter(prefix="/api", tags=["destinations"])


@router.get("/destinations/search")
async def destination_search(q: str = "", limit: int = Query(10)):
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


@router.get("/start-locations/search")
async def start_locations_search(q: str = "", limit: int = Query(15)):
    try:
        limit = min(max(int(limit), 1), 15)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be an integer")
    return {"results": search_start_locations(STARTING, q, limit)}
