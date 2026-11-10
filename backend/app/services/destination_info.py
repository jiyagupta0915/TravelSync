"""Plain facts about one destination, read from the bundled destinations dataset."""

from app.services.recommendation_engine import DF, INTEREST_FEATURES, TRAVELLER_TYPES


def _strongest(row, columns, minimum, limit):
    """The columns this destination scores highest on (0-1 profile scores from the dataset), best first."""
    scored = sorted(((float(row[c]), c) for c in columns), reverse=True)
    return [name for score, name in scored if score >= minimum][:limit]


def get_destination_profile(name: str) -> dict | None:
    """Where it is, typical stay and daily budget, what it is known for and who it suits. None if unknown."""
    rows = DF[DF["Destination"].str.lower() == name.strip().lower()].head(1)
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {
        "name": str(row["Destination"]), "state": str(row["State"]), "region": str(row["Region"]),
        "ideal_days": int(row["Ideal_Days"]), "avg_daily_budget_inr": int(row["Avg_Daily_Budget_INR"]),
        "latitude": float(row["Latitude"]), "longitude": float(row["Longitude"]),
        "known_for": _strongest(row, INTEREST_FEATURES, 0.7, 5),
        "best_for": _strongest(row, TRAVELLER_TYPES, 0.8, 4),
    }
