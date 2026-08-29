"""
Content-based weighted-KNN destination recommendation engine.

Loads the curated destination dataset once at process start, fits a
StandardScaler over the interest + traveller-type feature columns, and
exposes `recommend_destinations()` which combines:

  1. preference similarity (weighted-Euclidean KNN-style distance over the
     scaled interest/traveller-type feature vector)
  2. trip-duration compatibility
  3. budget compatibility (treated as a target range, not an exact match)
  4. geographical distance from the user's starting location (Haversine)

into a single ranked list. No external model artifact is required -
everything needed ships in data/ItiNova_India_Destinations_250.csv, so the
engine is self-contained and reproducible on a clean install.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "ItiNova_India_Destinations_250.csv"

# Feature order matters: it must match the order used to build the scaler
# and the order used to build every user vector. Keep this list, the CSV
# column order, and the frontend's DEFAULT_FEATURES list in sync.
TRAVELLER_TYPES = ["Family", "Couple", "Friends", "Solo"]
INTEREST_FEATURES = [
    "Mountain", "Beach", "Nature", "Adventure", "Culture", "Relaxation",
    "Nightlife", "Spiritual", "Trekking", "Photography", "Food", "Heritage",
]
FEATURES = INTEREST_FEATURES + TRAVELLER_TYPES

REQUIRED_COLUMNS = FEATURES + [
    "Destination", "State", "Region", "Latitude", "Longitude",
    "Avg_Daily_Budget_INR", "Ideal_Days",
]

if not DATA_PATH.exists():
    raise RuntimeError(f"Destination dataset not found at {DATA_PATH}")

DF = pd.read_csv(DATA_PATH)

_missing_columns = [c for c in REQUIRED_COLUMNS if c not in DF.columns]
if _missing_columns:
    raise RuntimeError(f"Destination dataset is missing required columns: {_missing_columns}")

if DF[REQUIRED_COLUMNS].isnull().any().any():
    raise RuntimeError("Destination dataset contains missing values in required columns.")

# Fit the scaler once, at import time, over the full destination catalogue.
# Every user vector is transformed with this exact same scaler so that
# distances are computed in a consistent feature space.
_scaler = StandardScaler()
X_SCALED = _scaler.fit_transform(DF[FEATURES].astype(float).values)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres. lat2/lon2 may be arrays."""
    R = 6371.0088
    lat1_r = np.radians(float(lat1))
    lon1_r = np.radians(float(lon1))
    lat2_r = np.radians(np.asarray(lat2, dtype=float))
    lon2_r = np.radians(np.asarray(lon2, dtype=float))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _validate_preferences(preferences, importance):
    if not isinstance(preferences, dict) or not isinstance(importance, dict):
        raise ValueError("preferences and importance must be objects keyed by interest name.")
    for feature in INTEREST_FEATURES:
        if feature not in preferences:
            raise ValueError(f"preferences.{feature} is required.")
        value = float(preferences[feature])
        if not 0 <= value <= 1:
            raise ValueError(f"preferences.{feature} must be between 0 and 1.")
        if feature not in importance:
            raise ValueError(f"importance.{feature} is required.")
        weight = float(importance[feature])
        if not 0 <= weight <= 3:
            raise ValueError(f"importance.{feature} must be between 0 and 3.")


def duration_score(ideal_days, requested_days):
    diff = abs(float(ideal_days) - requested_days)
    if diff <= 1:
        return 1.0
    if diff <= 2:
        return 0.80
    if diff <= 3:
        return 0.60
    return 0.30


def budget_score(target_budget, estimated_cost):
    """Budget is a target, not an exact match: ~85%-115% scores highest,
    up to 125% is tolerated with a lower score, beyond that is rejected."""
    if estimated_cost <= target_budget:
        return 1.0 if estimated_cost >= 0.85 * target_budget else 0.95
    ratio = estimated_cost / target_budget
    if ratio <= 1.15:
        return 0.90
    if ratio <= 1.25:
        return 0.65
    return 0.0


def distance_score(distance_km, max_distance_km):
    if distance_km <= max_distance_km:
        return 1.0
    if distance_km <= max_distance_km * 1.10:
        return 0.75
    return 0.0


def recommend_destinations(
    preferences,
    importance,
    traveller_type,
    duration,
    budget=None,
    start_lat=None,
    start_lon=None,
    max_distance_km=None,
    top_n=6,
):
    _validate_preferences(preferences, importance)

    if traveller_type not in TRAVELLER_TYPES:
        raise ValueError("traveller_type must be one of Family, Couple, Friends, Solo.")

    duration = int(duration)
    if not 1 <= duration <= 30:
        raise ValueError("duration must be between 1 and 30 days.")

    if budget is not None:
        budget = float(budget)
        if budget <= 0:
            raise ValueError("budget must be greater than 0.")

    if max_distance_km is not None:
        max_distance_km = float(max_distance_km)
        if max_distance_km <= 0:
            raise ValueError("max_distance_km must be greater than 0.")
        if start_lat is None or start_lon is None:
            raise ValueError("Starting location coordinates are required for distance filtering.")

    # Build the user's feature vector in the exact same column order as FEATURES.
    user_vector = np.zeros(len(FEATURES), dtype=float)
    weight_vector = np.zeros(len(FEATURES), dtype=float)
    for i, feature in enumerate(INTEREST_FEATURES):
        user_vector[i] = float(preferences[feature])
        weight_vector[i] = float(importance[feature])

    # Traveller type is encoded as a strong, exclusive one-hot signal.
    traveller_index = len(INTEREST_FEATURES) + TRAVELLER_TYPES.index(traveller_type)
    user_vector[traveller_index] = 1.0
    weight_vector[traveller_index] = 3.0

    if not np.any(weight_vector[: len(INTEREST_FEATURES)] > 0):
        raise ValueError("Select at least one travel interest with non-zero importance.")

    user_scaled = _scaler.transform(user_vector.reshape(1, -1))[0]

    # Weighted-Euclidean KNN-style content similarity over every destination.
    preference_distance = np.sqrt(np.sum(weight_vector * (X_SCALED - user_scaled) ** 2, axis=1))
    preference_score = 1 / (1 + preference_distance)

    result = DF.copy()
    result["preference_score"] = preference_score
    candidate_count = min(60, len(result))
    result = result.sort_values("preference_score", ascending=False).head(candidate_count).copy()

    result["duration_score"] = result["Ideal_Days"].apply(lambda d: duration_score(d, duration))

    if budget is not None:
        result["estimated_trip_budget_inr"] = result["Avg_Daily_Budget_INR"] * duration
        result["budget_score"] = result["estimated_trip_budget_inr"].apply(
            lambda cost: budget_score(budget, cost)
        )
        result = result[result["budget_score"] > 0].copy()
    else:
        result["budget_score"] = 1.0

    if max_distance_km is not None:
        result["distance_km"] = haversine_km(
            start_lat, start_lon, result["Latitude"].values, result["Longitude"].values
        )
        result["distance_score"] = result["distance_km"].apply(
            lambda d: distance_score(d, max_distance_km)
        )
        result = result[result["distance_score"] > 0].copy()
    else:
        result["distance_score"] = 1.0

    result["final_score"] = (
        0.60 * result["preference_score"]
        + 0.15 * result["duration_score"]
        + 0.15 * result["budget_score"]
        + 0.10 * result["distance_score"]
    )
    result = result.sort_values(["final_score", "preference_score"], ascending=False).head(int(top_n))

    columns = [
        "Destination", "State", "Region", "Latitude", "Longitude",
        "Avg_Daily_Budget_INR", "Ideal_Days", "preference_score",
        "duration_score", "budget_score", "distance_score", "final_score",
    ]
    if "estimated_trip_budget_inr" in result.columns:
        columns.append("estimated_trip_budget_inr")
    if "distance_km" in result.columns:
        columns.append("distance_km")

    records = result[columns].replace({np.nan: None}).to_dict("records")
    for record in records:
        for key in ("preference_score", "duration_score", "budget_score", "distance_score", "final_score"):
            record[key] = round(float(record[key]), 3)
        record["Avg_Daily_Budget_INR"] = int(record["Avg_Daily_Budget_INR"])
        record["Ideal_Days"] = int(record["Ideal_Days"])
        if record.get("estimated_trip_budget_inr") is not None:
            record["estimated_trip_budget_inr"] = int(record["estimated_trip_budget_inr"])
        if record.get("distance_km") is not None:
            record["distance_km"] = round(float(record["distance_km"]), 1)
    return records


def search_start_locations(starting_df, query="", limit=15):
    """Search the starting-locations dataset by location or state name."""
    query = (query or "").strip().lower()
    if query:
        mask = (
            starting_df["Location"].str.lower().str.contains(query, regex=False)
            | starting_df["State"].str.lower().str.contains(query, regex=False)
        )
        matches = starting_df[mask].head(limit)
    else:
        matches = starting_df.head(limit)
    return matches[["Location", "State", "Latitude", "Longitude"]].to_dict("records")