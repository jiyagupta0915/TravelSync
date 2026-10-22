from functools import lru_cache
from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "TravelSync_Top_Places_250.csv"

RATING_WEIGHT = 0.5
POPULARITY_WEIGHT = 0.5


@lru_cache(maxsize=1)
def _load_places() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["Destination_Key"] = df["Destination"].str.strip().str.lower()
    # Min-max normalise rating (3.9-4.9) so it's comparable with popularity (0.3-0.99)
    r = df["Rating"]
    rating_norm = (r - r.min()) / (r.max() - r.min())
    df["Score"] = (RATING_WEIGHT * rating_norm + POPULARITY_WEIGHT * df["Popularity"]).round(4)
    return df


def get_top_places(destination: str, limit: int = 5) -> list[dict]:
    df = _load_places()
    subset = df[df["Destination_Key"] == destination.strip().lower()]
    if subset.empty:
        return []
    top = subset.sort_values(["Score", "Rating", "Popularity"], ascending=False).head(limit)
    return [
        {
            "rank": i,
            "place_name": row.Place_Name,
            "category": row.Category,
            "rating": row.Rating,
            "popularity": row.Popularity,
            "duration_hrs": row.Duration_Hrs,
            "best_season": row.Best_Season,
            "description": row.Description,
            "score": row.Score,
        }
        for i, row in enumerate(top.itertuples(), start=1)
    ]