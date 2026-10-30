"""
One-time script: adds Latitude / Longitude columns to TravelSync_Top_Places_250.csv.

Why: the Smart Stay Recommendations feature ranks hotels by how close they are to a
destination's top-5 places, so every place needs coordinates. The CSV only has names.

Run it from the backend folder (once):
    python scripts/geocode_places.py --limit 10      # small test first (10 places)
    python scripts/geocode_places.py                 # then the real run (1250 places)

Needs GEOAPIFY_API_KEY in backend/.env. Uses 1 Geoapify credit per place (free plan = 3,000
credits/day, 5 requests/second), so the full run fits in a single day.

Safe to re-run: places that already have coordinates are skipped, and progress is saved to the
CSV every 50 places, so if it stops (internet, daily limit) you can simply run it again.

A result is only accepted if it lies within 60 km of the destination's own coordinates, so a
place called e.g. "Mall Road" can never be pinned to a different city. Places that cannot be
found are left blank; the Stays feature then falls back to the destination centre for them.
"""

import argparse
import math
import os
import sys
import time
from pathlib import Path

import httpx
import pandas as pd
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"
PLACES_CSV = DATA_DIR / "TravelSync_Top_Places_250.csv"
DESTINATIONS_CSV = DATA_DIR / "ItiNova_India_Destinations_250.csv"

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
SEARCH_RADIUS_M = 60_000        # only look within 60 km of the destination
MAX_ACCEPTED_KM = 60            # and double-check the distance on our side
SECONDS_BETWEEN_CALLS = 0.25    # stays under the free plan's 5 requests/second
SAVE_EVERY = 50


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geocode(client: httpx.Client, api_key: str, text: str, lat: float, lon: float):
    """Returns (lat, lon) of the best match near (lat, lon), or None. Retries on rate limits."""
    params = {
        "text": text,
        "filter": f"circle:{lon},{lat},{SEARCH_RADIUS_M}",
        "bias": f"proximity:{lon},{lat}",
        "limit": 1,
        "lang": "en",
        "apiKey": api_key,
    }
    for attempt in range(4):
        response = client.get(GEOCODE_URL, params=params)
        if response.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        if response.status_code in (401, 403):
            sys.exit("Geoapify rejected the API key (HTTP %s). Check GEOAPIFY_API_KEY in backend/.env." % response.status_code)
        response.raise_for_status()
        features = response.json().get("features") or []
        if not features:
            return None
        props = features[0].get("properties") or {}
        if props.get("lat") is None or props.get("lon") is None:
            return None
        found_lat, found_lon = float(props["lat"]), float(props["lon"])
        if haversine_km(lat, lon, found_lat, found_lon) > MAX_ACCEPTED_KM:
            return None
        return found_lat, found_lon
    sys.exit("Geoapify keeps answering 'too many requests' (daily limit reached?). Run the script again later - it resumes where it stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add Latitude/Longitude to the top-places CSV.")
    parser.add_argument("--limit", type=int, default=None, help="only geocode this many places (for a quick test)")
    args = parser.parse_args()

    load_dotenv(BACKEND_DIR / ".env")
    api_key = os.getenv("GEOAPIFY_API_KEY", "").strip()
    if not api_key:
        sys.exit("GEOAPIFY_API_KEY is missing. Add it to backend/.env first (see the setup guide).")

    places = pd.read_csv(PLACES_CSV)
    destinations = pd.read_csv(DESTINATIONS_CSV).set_index(
        pd.read_csv(DESTINATIONS_CSV)["Destination"].str.strip().str.lower()
    )

    for column in ("Latitude", "Longitude"):
        if column not in places.columns:
            places[column] = float("nan")

    todo = places.index[places["Latitude"].isna() | places["Longitude"].isna()].tolist()
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} places to geocode ({len(places) - len(todo)} already done or skipped).")

    found = missed = 0
    with httpx.Client(timeout=20.0) as client:
        for count, index in enumerate(todo, start=1):
            row = places.loc[index]
            key = str(row["Destination"]).strip().lower()
            if key not in destinations.index:
                missed += 1
                continue
            dest = destinations.loc[key]
            result = geocode(client, api_key, f"{row['Place_Name']}, {row['Destination']}, India",
                             float(dest["Latitude"]), float(dest["Longitude"]))
            if result:
                places.loc[index, "Latitude"] = round(result[0], 6)
                places.loc[index, "Longitude"] = round(result[1], 6)
                found += 1
            else:
                missed += 1
                print(f"  not found: {row['Place_Name']} ({row['Destination']})")

            if count % SAVE_EVERY == 0:
                places.to_csv(PLACES_CSV, index=False)
                print(f"  ...{count}/{len(todo)} done (saved)")
            time.sleep(SECONDS_BETWEEN_CALLS)

    places.to_csv(PLACES_CSV, index=False)
    total_with = int(places["Latitude"].notna().sum())
    print(f"Finished. Found {found}, not found {missed}. {total_with}/{len(places)} places now have coordinates.")


if __name__ == "__main__":
    main()