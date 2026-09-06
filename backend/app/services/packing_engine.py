"""
Smart Packing Assistant - rule engine.

Two tiers, by design (see project notes):
  Tier 1 "climate"  - always available. Uses the destination's Region
                       and terrain/activity profile columns already in
                       the destinations dataset (no dates needed).
  Tier 2 "forecast"  - available once the trip has travel dates. Calls
                       Open-Meteo (no API key required) for the actual
                       forecast and refines the weather-related items.

Every rule is a plain function so it stays easy to explain/defend and
easy to unit test - deliberately not ML for this module.
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("travelsync.packing")

# ---- Region -> baseline climate assumption (Tier 1) ----
REGION_CLIMATE = {
    "North": "cold",
    "South": "hot",
    "East": "rainy",
    "West": "hot",
    "Central": "hot",
    "Northeast": "rainy",
}


def _new_item(item_id: str, category: str, name: str, quantity: int = 1) -> dict:
    return {
        "id": item_id,
        "category": category,
        "name": name,
        "quantity": quantity,
        "packed": False,
        "source": "rule",
    }


# ---------------------------------------------------------------- #
# Weather (Tier 2)
# ---------------------------------------------------------------- #

async def fetch_weather_summary(
    latitude: float, longitude: float, start_date: str, end_date: str
) -> Optional[dict]:
    """
    Calls Open-Meteo's free forecast API for the given coordinates and
    date range. Returns a small summary dict, or None if the call
    fails / dates are out of range - callers must fall back to the
    Tier 1 climate profile in that case.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
    }
    url = "https://api.open-meteo.com/v1/forecast"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open-Meteo request failed, falling back to climate profile: %s", exc)
        return None

    daily = data.get("daily", {})
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    rain_probs = daily.get("precipitation_probability_max", [])

    if not max_temps or not min_temps:
        return None

    avg_max = sum(max_temps) / len(max_temps)
    avg_min = sum(min_temps) / len(min_temps)
    avg_rain_prob = sum(rain_probs) / len(rain_probs) if rain_probs else 0

    if avg_rain_prob >= 50:
        condition = "rainy"
    elif avg_max >= 32:
        condition = "hot"
    elif avg_min <= 12:
        condition = "cold"
    else:
        condition = "mild"

    return {
        "condition": condition,
        "avg_max_temp": round(avg_max, 1),
        "avg_min_temp": round(avg_min, 1),
        "avg_rain_probability": round(avg_rain_prob, 1),
    }


# ---------------------------------------------------------------- #
# Rule engine
# ---------------------------------------------------------------- #

ACTIVITY_ITEMS: dict[str, list[str]] = {
    "beach": ["Swimwear", "Beach towel", "Sunscreen (SPF 50)", "Flip-flops"],
    "trekking": ["Hiking shoes", "Trekking poles", "Moisture-wicking socks", "Headlamp"],
    "adventure": ["Quick-dry clothing", "Sports shoes", "Knee/elbow guards"],
    "nightlife": ["Evening outfit", "Comfortable party shoes"],
    "spiritual": ["Modest clothing (covers shoulders/knees)", "Scarf/stole"],
    "photography": ["Extra memory cards", "Camera cleaning kit", "Portable tripod"],
    "nature": ["Insect repellent", "Binoculars"],
}

FIXED_ITEMS = {
    "Electronics": [("Phone charger", 1), ("Power bank", 1)],
    "Documents": [("ID proof", 1), ("Trip tickets / bookings", 1), ("Cash + cards", 1)],
}


def build_checklist(
    duration: Optional[int],
    condition: str,
    activities: list[str],
    health_alert_active: bool = False,
) -> list[dict]:
    """
    Pure function: given a duration, a resolved weather `condition`
    ("hot" | "cold" | "rainy" | "mild") and a list of activity tags,
    returns a flat list of packing item dicts.
    """
    days = duration or 3
    items: list[dict] = []
    idx = 0

    def add(category: str, name: str, quantity: int = 1) -> None:
        nonlocal idx
        idx += 1
        items.append(_new_item(f"r{idx}", category, name, quantity))

    # ---- Duration-scaled clothing base ----
    add("Clothing", "T-shirts / tops", min(days, 7))
    add("Clothing", "Bottoms (trousers/shorts)", min(max(days // 2, 1), 4))
    add("Clothing", "Innerwear & socks", min(days, 7))
    add("Clothing", "Comfortable walking shoes")
    add("Clothing", "Sleepwear")

    # ---- Weather-condition rules ----
    if condition == "rainy":
        add("Weather", "Umbrella")
        add("Weather", "Raincoat")
        add("Weather", "Waterproof bag / pouch")
    elif condition == "cold":
        add("Weather", "Warm jacket")
        add("Weather", "Thermal inners")
        add("Weather", "Woolen cap & gloves")
    elif condition == "hot":
        add("Weather", "Sunscreen")
        add("Weather", "Cap / hat")
        add("Weather", "Sunglasses")
    else:  # mild
        add("Weather", "Light jacket (for evenings)")

    # ---- Fixed categories ----
    for category, entries in FIXED_ITEMS.items():
        for name, qty in entries:
            add(category, name, qty)

    # ---- Activity rules ----
    for activity in activities:
        key = activity.strip().lower()
        for name in ACTIVITY_ITEMS.get(key, []):
            add("Activity", name)

    # ---- Cross-module: Health Intelligence hook ----
    if health_alert_active:
        add("Health", "Insect repellent")
        add("Health", "Basic first-aid / ORS sachets")

    return items