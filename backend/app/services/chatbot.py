"""
TravelSync assistant: answers travel questions from TravelSync's own data. No AI model and no API key.

How a question is answered:
  1. Find what it is about: a destination (or state) named in the message; otherwise the one the conversation was
     already about; otherwise, for questions about "my trip", the user's most recent trip.
  2. Find what is being asked (the intent) by counting keyword hits: health, packing, places, groups, trips,
     recommendations, destination facts, or a greeting.
  3. Build the reply from the same services the rest of the app uses (top places, packing rules, health alerts and
     history, the destinations dataset, the user's own trips and groups).

Anything it cannot place gets a "here is what I can help with" reply (`_fallback`), marked "unmatched". The chat
route may then ask an AI model instead (app/services/assistant_llm.py) - only for those, and only if one is set up.

Every reply is a dict: {"text", "items" (bullet lines), "links" ([{label, to}] inside the app), "suggestions"
(follow-up questions to offer)}.
"""

import re

from app.services.destination_info import get_destination_profile
from app.services.health_alerts import get_alerts_for_state
from app.services.health_engine import IS_SYNTHETIC, get_state_profile
from app.services.packing_engine import REGION_CLIMATE, build_checklist
from app.services.places_service import get_top_places
from app.services.recommendation_engine import DF, INTEREST_FEATURES

# ------------------------------------------------------------------ what the message is about
_DESTINATIONS = {str(name).lower(): str(name) for name in DF["Destination"]}
_STATES = {str(name).lower(): str(name) for name in DF["State"].unique()}


def _name_pattern(names):
    longest_first = sorted(names, key=len, reverse=True)          # "New Delhi" must win over "Delhi"
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in longest_first) + r")\b")


_DESTINATION_RE = _name_pattern(_DESTINATIONS)
_STATE_RE = _name_pattern(_STATES)

# Words people use for each interest column of the dataset.
_INTEREST_WORDS = {
    "Mountain": ["mountain", "mountains", "hills", "hill station", "snow"],
    "Beach": ["beach", "beaches", "sea", "coast"],
    "Nature": ["nature", "greenery", "forest", "wildlife"],
    "Adventure": ["adventure", "adventurous", "rafting", "paragliding"],
    "Culture": ["culture", "cultural"],
    "Relaxation": ["relax", "relaxing", "relaxation", "peaceful", "calm"],
    "Nightlife": ["nightlife", "party", "parties", "clubs"],
    "Spiritual": ["spiritual", "temple", "temples", "pilgrimage"],
    "Trekking": ["trek", "treks", "trekking", "hiking", "hike"],
    "Photography": ["photography", "photos", "scenic"],
    "Food": ["food", "foodie", "cuisine"],
    "Heritage": ["heritage", "history", "historical", "forts", "monuments"],
}
assert set(_INTEREST_WORDS) == set(INTEREST_FEATURES)

# ------------------------------------------------------------------ what is being asked
# Order matters: on a tie the earlier intent wins ("what should I pack for my trip" is packing, not trips).
_INTENT_WORDS = {
    "health": ["health", "outbreak", "outbreaks", "disease", "diseases", "alert", "alerts", "dengue", "malaria", "safe",
               "safety", "precaution", "precautions", "illness", "sick", "vaccine", "vaccines"],
    "packing": ["pack", "packing", "carry", "wear", "clothes", "luggage", "bring"],
    "places": ["place", "places", "visit", "see", "attraction", "attractions", "sightseeing", "things to do", "spots", "famous"],
    "groups": ["group", "groups", "unread", "chat", "chats", "messages"],
    "trips": ["my trip", "my trips", "trips", "upcoming", "planned"],
    "recommend": ["recommend", "suggest", "suggestion", "where should i go", "where to go", "where can i go", "ideas"],
    "info": ["about", "budget", "cost", "costs", "expensive", "cheap", "days", "how long", "known for", "tell me", "where is"],
    "greeting": ["hi", "hello", "hey", "help", "what can you do", "thanks", "thank you"],
}
_INTENT_RES = {intent: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b") for intent, words in _INTENT_WORDS.items()}

STARTERS = ["Top places in Goa", "What should I pack for Manali?", "Any health alerts in Kerala?", "Suggest a beach destination", "Show my trips"]


def _inr(value) -> str:
    return f"₹{int(value):,}"


def _reply(text, items=None, links=None, suggestions=None) -> dict:
    return {"text": text, "items": items or [], "links": links or [], "suggestions": suggestions or []}


def detect(message: str) -> dict:
    """{"intent", "destination", "state", "interests"} found in the message itself (no conversation context)."""
    text = " ".join(message.lower().split())
    destination = _DESTINATION_RE.search(text)
    state = _STATE_RE.search(text)
    interests = [feature for feature, words in _INTEREST_WORDS.items()
                 if re.search(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", text)]
    scores = {intent: len(pattern.findall(text)) for intent, pattern in _INTENT_RES.items()}
    best = max(scores, key=scores.get)               # dicts keep insertion order, so ties go to the earlier intent
    intent = best if scores[best] else None
    return {"intent": intent, "destination": _DESTINATIONS[destination.group(1)] if destination else None,
            "state": _STATES[state.group(1)] if state else None, "interests": interests}


# ------------------------------------------------------------------ replies built from TravelSync data
def _places(destination: str) -> dict:
    places = get_top_places(destination, 5)
    if not places:
        return _reply(f"I don't have a places list for {destination} yet.", suggestions=[f"Tell me about {destination}"])
    items = [f"{p['rank']}. {p['place_name']} - {p['category']}, rated {float(p['rating']):.1f}, best in {p['best_season']}" for p in places]
    return _reply(f"Top places to visit in {destination}, ranked by rating and popularity:", items,
                  suggestions=[f"Tell me about {destination}", f"What should I pack for {destination}?"])


def _info(destination: str) -> dict:
    p = get_destination_profile(destination)
    items = [f"Ideal stay: {p['ideal_days']} days", f"Average daily budget: {_inr(p['avg_daily_budget_inr'])}"]
    if p["known_for"]:
        items.append("Known for: " + ", ".join(p["known_for"]))
    if p["best_for"]:
        items.append("Great for: " + ", ".join(p["best_for"]))
    return _reply(f"{p['name']} is in {p['state']} ({p['region']} India).", items,
                  suggestions=[f"Top places in {p['name']}", f"Any health alerts in {p['name']}?"])


def _packing(destination: str, trip: dict | None) -> dict:
    p = get_destination_profile(destination)
    days = (trip or {}).get("duration") or p["ideal_days"]
    condition = REGION_CLIMATE.get(p["region"], "mild")     # same rule the Packing page uses when it has no forecast
    by_category: dict[str, list[str]] = {}
    for item in build_checklist(days, condition, []):
        label = f"{item['quantity']} × {item['name']}" if item["quantity"] > 1 else item["name"]
        by_category.setdefault(item["category"], []).append(label)
    items = [f"{category}: {', '.join(names)}" for category, names in by_category.items()]
    based_on = "your trip" if trip else "the ideal stay"
    links = ([{"label": "Open this trip's packing list", "to": f"/trip/{trip['_id']}/packing"}] if trip
             else [{"label": "Packing assistant", "to": "/packing"}])
    return _reply(f"For {days} days in {destination} ({based_on}), assuming typically {condition} weather for the region:", items, links,
                  [f"Top places in {destination}", f"Any health alerts in {destination}?"])


def _health(state: str, place: str) -> dict:
    alerts = get_alerts_for_state(state)
    items = [f"Alert: {a['title']} (reported {a['reported_date']}, {a['source_name']})" for a in alerts["active"]]
    profile = get_state_profile(state)
    if profile.get("has_data"):
        history = "demo data, not real outbreaks" if IS_SYNTHETIC else "past reports, not live"
        common = ", ".join(d["disease"] for d in profile["top_diseases"][:3])
        items.append(f"Most reported in {state} historically ({history}): {common}")
        for group in profile["precautions"][:2]:
            items.append(f"{group['label']}: {group['tips'][0]}")
    items.append("Our alert list is maintained by hand from official sources. It is not a live feed, and no alert does not mean no risk.")
    items.append("This is general information, not medical advice.")
    return _reply(f"Health and safety for {place}: {alerts['message']}", items, [{"label": "Open Health & Safety", "to": "/health"}],
                  [f"What should I pack for {place}?"] if place != state else [])


def _recommend(interests: list[str]) -> dict:
    finder = [{"label": "Find my destination", "to": "/planner/recommend"}]
    if not interests:
        return _reply("What kind of trip are you after? Tell me an interest, or use the destination finder for a match on budget, days and distance.",
                      links=finder, suggestions=["Suggest a beach destination", "Suggest a mountain destination", "Suggest a place for trekking"])
    ranked = DF.assign(_score=DF[interests].astype(float).mean(axis=1)).sort_values("_score", ascending=False).head(5)
    items = [f"{r.Destination}, {r.State} - about {int(r.Ideal_Days)} days, {_inr(r.Avg_Daily_Budget_INR)} a day" for r in ranked.itertuples()]
    top = str(ranked.iloc[0]["Destination"])
    return _reply(f"Destinations that score highest for {' and '.join(i.lower() for i in interests)} in our dataset:", items, finder,
                  [f"Tell me about {top}", f"Top places in {top}"])


def _trips(trips: list[dict]) -> dict:
    if not trips:
        return _reply("You haven't saved any trips yet.", links=[{"label": "Find my destination", "to": "/planner/recommend"}],
                      suggestions=["Suggest a beach destination"])
    items = []
    for t in trips[:5]:
        details = [f"{t['duration']} days" if t.get("duration") else None, _inr(t["budget"]) if t.get("budget") else None]
        items.append(f"{t['destination']}, {t['state']}" + "".join(f" - {d}" for d in details if d))
    more = f" Showing the latest 5 of {len(trips)}." if len(trips) > 5 else ""
    latest = trips[0]["destination"]
    return _reply(f"You have {len(trips)} saved {'trip' if len(trips) == 1 else 'trips'}.{more}", items, [{"label": "My Trips", "to": "/trips"}],
                  [f"What should I pack for {latest}?", f"Top places in {latest}"])


def _groups(groups: list[dict]) -> dict:
    if not groups:
        return _reply("You're not in a travel group yet. Create one or join with an invite code.", links=[{"label": "Groups", "to": "/groups"}])
    items = [f"{g['name']} - {g['members']} {'member' if g['members'] == 1 else 'members'}"
             + (f", {g['unread']} unread {'message' if g['unread'] == 1 else 'messages'}" if g["unread"] else "") for g in groups]
    unread = sum(g["unread"] for g in groups)
    summary = f"{unread} unread {'message' if unread == 1 else 'messages'} in total." if unread else "No unread messages."
    return _reply(f"You're in {len(groups)} {'group' if len(groups) == 1 else 'groups'}. {summary}", items, [{"label": "Groups", "to": "/groups"}])


def _greeting(name: str, thanks: bool) -> dict:
    if thanks:
        return _reply("You're welcome! Ask me anything else about your trip.", suggestions=STARTERS[:3])
    return _reply(f"Hi {name.split()[0]}! I answer from TravelSync's own data: destinations, top places, packing, health alerts, and your trips and groups.",
                  suggestions=STARTERS)


def _fallback() -> dict:
    # "unmatched" tells the chat route that nothing here answered the question, so it may try the AI model.
    return {"unmatched": True, **_reply("I'm not sure about that one. I can help with destinations, top places, what to pack, health alerts, and your trips and groups.",
                  suggestions=STARTERS)}


def _ask_where(what: str) -> dict:
    return _reply(f"Which destination should I {what}? Try a name like Goa or Manali.", suggestions=STARTERS[:3])


# ------------------------------------------------------------------ putting it together
def answer(message: str, *, user_name: str, trips: list[dict], groups: list[dict], context_destination: str | None = None) -> tuple[dict, str | None]:
    """Returns (reply, destination the conversation is now about). `trips` are the user's trips, newest first;
    `groups` are {"name", "members", "unread"} for the user's groups."""
    found = detect(message)
    intent, destination, state = found["intent"], found["destination"], found["state"]
    text = message.lower()

    # Questions about the user's own things need no destination.
    if intent == "groups":
        return _groups(groups), context_destination
    if intent == "trips" and not destination:
        return _trips(trips), context_destination
    if intent == "greeting" and not destination:
        return _greeting(user_name, "thank" in text), context_destination
    if intent == "recommend" or (found["interests"] and not destination and intent in (None, "places", "info")):
        return _recommend(found["interests"]), context_destination

    if intent == "health" and not destination and state:               # "any outbreaks in Kerala?"
        return _health(state, state), context_destination

    # Everything else is about a destination: named now, or carried over, or the user's latest trip.
    if not destination and context_destination and _DESTINATIONS.get(context_destination.lower()):
        destination = _DESTINATIONS[context_destination.lower()]
    if not destination and trips and intent in ("packing", "health", "places") and re.search(r"\bmy trip\b", text):
        destination = trips[0]["destination"]
    if not destination:
        # "info" words ("tell me", "how long", "cost"...) are too general to assume a destination was meant, so
        # without one the question counts as unmatched rather than getting "which destination?".
        asks = {"packing": "pack for", "health": "check health alerts for", "places": "show places for"}
        return (_ask_where(asks[intent]) if intent in asks else _fallback()), context_destination

    trip = next((t for t in trips if t["destination"] == destination), None)
    if intent == "packing":
        return _packing(destination, trip), destination
    if intent == "health":
        return _health(get_destination_profile(destination)["state"], destination), destination
    if intent == "places":
        return _places(destination), destination
    reply = _info(destination)                          # "Manali", "tell me about Manali", "budget for Manali"
    # A longer question that names a destination but matches nothing we know ("plan a 2 day itinerary for Jaipur")
    # is really unmatched: the route may ask the AI model, and these facts are what the user gets if it can't.
    if intent is None and len(_DESTINATION_RE.sub("", " ".join(text.split())).split()) > 2:
        reply["unmatched"] = True
    return reply, destination
