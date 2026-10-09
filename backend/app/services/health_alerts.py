"""
Current outbreak alerts (section A of the Health & Safety module). This is NOT machine learning.

Alerts live in data/health_alerts.json, a small list the team maintains by hand from official
sources (WHO Disease Outbreak News, MoHFW/NCDC press releases, etc). It is NOT a live feed.
The file is re-read on every request, so editing it needs no server restart.

Each alert:  id, states (list, or ["*"] for nationwide), disease, title, summary,
             severity ("info" | "watch" | "warning"), reported_date (YYYY-MM-DD),
             source_name, source_url, optional active_until (YYYY-MM-DD)

Rules:
  - An alert counts as ACTIVE for 45 days after reported_date (or until active_until if given).
  - After that it shows as an EARLIER alert for up to a year.
  - "last_reviewed" in the file is the date someone last checked the official sources.
    Only change it when you really did. It is null until then, and the UI says so.
  - "No active alert" is never presented as "safe".
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "health_alerts.json"
ACTIVE_DAYS = 45
RECENT_DAYS = 365
STALE_AFTER_DAYS = 14


def _d(text):
    return datetime.strptime(text, "%Y-%m-%d").date()


def _fmt(d):
    return d.strftime("%d %b %Y")


def _load():
    try:
        raw = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None, []
    return raw.get("last_reviewed"), raw.get("alerts", [])


def get_alerts_for_state(state: str, today: date | None = None) -> dict:
    today = today or date.today()
    last_reviewed, alerts = _load()

    active, earlier = [], []
    for a in alerts:
        try:
            if state not in a["states"] and "*" not in a["states"]:
                continue
            reported = _d(a["reported_date"])
            until = _d(a["active_until"]) if a.get("active_until") else reported + timedelta(days=ACTIVE_DAYS)
            item = {
                "id": a["id"], "disease": a["disease"], "title": a["title"], "summary": a["summary"],
                "severity": a.get("severity", "info"), "reported_date": _fmt(reported),
                "source_name": a["source_name"], "source_url": a["source_url"],
                "_sort": reported,
            }
        except (KeyError, ValueError, TypeError):
            continue   # skip malformed entries instead of breaking the page
        if today <= until:
            active.append(item)
        elif today <= reported + timedelta(days=RECENT_DAYS):
            earlier.append(item)

    for lst in (active, earlier):
        lst.sort(key=lambda x: x["_sort"], reverse=True)
        for x in lst:
            del x["_sort"]

    notes = ["This is a hand-maintained list from official sources, not a live feed. "
             "No alert does not mean no risk."]
    stale = False
    if last_reviewed is None:
        stale = True
        notes.insert(0, "This alert list has not been reviewed yet, so it may be incomplete.")
    else:
        try:
            stale = (today - _d(last_reviewed)).days > STALE_AFTER_DAYS
        except ValueError:
            stale = True
        if stale:
            notes.insert(0, f"The alert list was last reviewed on {last_reviewed} and may be out of date.")

    return {
        "connected": True,
        "status": "alert" if active else "none",
        "message": (f"{len(active)} active alert{'s' if len(active) != 1 else ''} for {state}."
                    if active else f"No active alert found for {state} in our alert list."),
        "active": active,
        "earlier": earlier,
        "last_reviewed": last_reviewed,
        "stale": stale,
        "notes": notes,
    }
