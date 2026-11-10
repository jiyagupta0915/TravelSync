from fastapi import APIRouter, HTTPException, Path, Query

from app.services.recommendation_engine import DF, INTEREST_FEATURES, STARTING, TRAVELLER_TYPES, search_start_locations

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


def _strongest(row, columns, minimum, limit):
    """The columns this destination scores highest on (0-1 profile scores from the dataset), best first."""
    scored = sorted(((float(row[c]), c) for c in columns), reverse=True)
    return [name for score, name in scored if score >= minimum][:limit]


@router.get("/destinations/{name}")
async def destination_profile(name: str = Path(max_length=120)):
    """Overview of one destination from the bundled dataset: where it is, typical stay and daily budget, what it is
    known for and who it suits. Declared after /destinations/search so that path keeps working."""
    rows = DF[DF["Destination"].str.lower() == name.strip().lower()].head(1)
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"No destination called '{name}' was found.")
    row = rows.iloc[0]
    return {"destination": {
        "name": str(row["Destination"]), "state": str(row["State"]), "region": str(row["Region"]),
        "ideal_days": int(row["Ideal_Days"]), "avg_daily_budget_inr": int(row["Avg_Daily_Budget_INR"]),
        "latitude": float(row["Latitude"]), "longitude": float(row["Longitude"]),
        "known_for": _strongest(row, INTEREST_FEATURES, 0.7, 5),
        "best_for": _strongest(row, TRAVELLER_TYPES, 0.8, 4),
    }}


@router.get("/start-locations/search")
async def start_locations_search(q: str = Query("", max_length=100), limit: int = Query(15)):
    try:
        limit = min(max(int(limit), 1), 15)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="limit must be an integer")
    return {"results": search_start_locations(STARTING, q, limit)}
