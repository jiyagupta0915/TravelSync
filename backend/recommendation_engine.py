import joblib
import numpy as np

ARTIFACT_PATH = "itinova_recommender.joblib"
artifact = joblib.load(ARTIFACT_PATH)

scaler = artifact["scaler"]
X_scaled = artifact["X_scaled"]
df = artifact["df"]
experience_features = artifact["experience_features"]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arcsin(np.sqrt(a))


def recommend_destinations(
    user_preferences,
    user_importance,
    top_n=5,
    user_budget=None,
    user_duration=None,
    max_distance_km=None,
    start_lat=None,
    start_lon=None,
    candidate_count=30
):
    missing_pref = [f for f in experience_features if f not in user_preferences]
    missing_imp = [f for f in experience_features if f not in user_importance]

    if missing_pref:
        raise ValueError(f"Missing preference features: {missing_pref}")

    if missing_imp:
        raise ValueError(f"Missing importance features: {missing_imp}")

    user_vector = np.array(
        [user_preferences[f] for f in experience_features],
        dtype=float
    ).reshape(1, -1)

    user_scaled = scaler.transform(user_vector)

    weights = np.array(
        [user_importance[f] for f in experience_features],
        dtype=float
    )

    if np.all(weights == 0):
        raise ValueError("At least one feature must have non-zero importance.")

    weighted_distances = np.sqrt(
        np.sum(
            weights * (X_scaled - user_scaled) ** 2,
            axis=1
        )
    )

    candidate_count = min(int(candidate_count), len(df))
    candidate_indices = np.argsort(weighted_distances)[:candidate_count]

    results = df.iloc[candidate_indices].copy()
    results["KNN_Distance"] = weighted_distances[candidate_indices]
    results["Similarity_Score"] = 1 / (1 + results["KNN_Distance"])

    if user_duration is not None:
        user_duration = int(user_duration)

        results = results[
            (results["Ideal_Days"] >= user_duration - 2)
            & (results["Ideal_Days"] <= user_duration + 2)
        ].copy()

    if user_budget is not None and user_duration is not None:
        results["Estimated_Trip_Budget_INR"] = (
            results["Avg_Daily_Budget_INR"] * user_duration
        )

        results = results[
            results["Estimated_Trip_Budget_INR"] <= float(user_budget)
        ].copy()

    if (
        max_distance_km is not None
        and start_lat is not None
        and start_lon is not None
        and "Latitude" in results.columns
        and "Longitude" in results.columns
    ):
        if results[["Latitude", "Longitude"]].notna().all().all():
            results["Distance_From_Start_Km"] = haversine(
                float(start_lat),
                float(start_lon),
                results["Latitude"].astype(float).values,
                results["Longitude"].astype(float).values
            )

            results = results[
                results["Distance_From_Start_Km"] <= float(max_distance_km)
            ].copy()

    results = results.sort_values("KNN_Distance").head(int(top_n))

    # Convert NumPy values to native Python values for JSON serialization.
    return results.to_dict(orient="records")
