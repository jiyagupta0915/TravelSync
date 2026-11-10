from app.services import chatbot
from tests.conftest import create_trip, make_client


async def ask(c, message, destination=None):
    r = await c.post("/api/chat", json={"message": message, "destination": destination})
    assert r.status_code == 200, r.text
    return r.json()


def test_detect_finds_the_intent_and_what_it_is_about():
    assert chatbot.detect("What are the top places in goa?") | {"interests": []} == {"intent": "places", "destination": "Goa", "state": "Goa", "interests": []}
    assert chatbot.detect("what should I pack for my trip")["intent"] == "packing"          # tie with "my trip": packing wins
    assert chatbot.detect("any outbreaks in Kerala")["state"] == "Kerala"
    assert chatbot.detect("suggest a beach destination") == {"intent": "recommend", "destination": None, "state": None, "interests": ["Beach"]}
    assert chatbot.detect("qwerty zxcv")["intent"] is None


async def test_places_info_and_follow_up_using_conversation_context(client, alice):
    places = await ask(client, "top places in Manali")
    assert places["destination"] == "Manali" and places["source"] == "travelsync-data"
    assert len(places["reply"]["items"]) == 5 and places["reply"]["items"][0].startswith("1. ")

    info = await ask(client, "tell me about manali")
    assert info["reply"]["text"] == "Manali is in Himachal Pradesh (North India)."
    assert "Ideal stay: 5 days" in info["reply"]["items"] and "Average daily budget: ₹2,306" in info["reply"]["items"]

    # no destination in the follow-up: it carries over from the conversation
    follow_up = await ask(client, "what should I pack?", destination="Manali")
    assert follow_up["destination"] == "Manali" and "5 days in Manali (the ideal stay)" in follow_up["reply"]["text"]
    assert any(i.startswith("Clothing: 5 × T-shirts") for i in follow_up["reply"]["items"])
    assert any("Warm jacket" in i for i in follow_up["reply"]["items"])                    # North -> cold-weather rules
    assert follow_up["reply"]["links"] == [{"label": "Packing assistant", "to": "/packing"}]


async def test_packing_uses_the_users_own_trip_when_there_is_one(client, alice):
    trip = await create_trip(client, "Goa")                       # 4 days
    mine = await ask(client, "what should I pack for my trip?")
    assert mine["destination"] == "Goa" and "4 days in Goa (your trip)" in mine["reply"]["text"]
    assert mine["reply"]["links"] == [{"label": "Open this trip's packing list", "to": f"/trip/{trip['id']}/packing"}]


async def test_health_is_labelled_honestly(client, alice):
    by_place = await ask(client, "is it safe? any health alerts in Goa")
    assert by_place["reply"]["text"].startswith("Health and safety for Goa:")
    joined = " ".join(by_place["reply"]["items"])
    assert "not a live feed" in joined and "not medical advice" in joined and "Most reported in Goa historically" in joined
    assert by_place["reply"]["links"] == [{"label": "Open Health & Safety", "to": "/health"}]
    by_state = await ask(client, "any outbreaks in Kerala?")
    assert by_state["reply"]["text"].startswith("Health and safety for Kerala:")


async def test_recommend_by_interest_and_without_one(client, alice):
    beach = await ask(client, "suggest a beach destination")
    assert "beach" in beach["reply"]["text"] and len(beach["reply"]["items"]) == 5
    assert beach["reply"]["links"] == [{"label": "Find my destination", "to": "/planner/recommend"}]
    vague = await ask(client, "where should I go?")
    assert vague["reply"]["items"] == [] and "Suggest a beach destination" in vague["reply"]["suggestions"]


async def test_my_trips_and_groups_are_only_ever_the_session_users(client, client_b, alice, bob):
    assert (await ask(client, "show my trips"))["reply"]["text"] == "You haven't saved any trips yet."
    await create_trip(client, "Goa")
    await create_trip(client_b, "Manali")
    trips = await ask(client, "show my trips")
    assert trips["reply"]["text"] == "You have 1 saved trip." and trips["reply"]["items"] == ["Goa, Goa - 4 days - ₹20,000"]

    group = (await client.post("/api/groups", json={"name": "Goa Gang"})).json()["group"]
    await client_b.post("/api/groups/join", json={"invite_code": group["invite_code"]})
    await client.post(f"/api/groups/{group['id']}/messages", json={"text": "hello"})
    groups = await ask(client_b, "any unread messages in my groups?")
    assert groups["reply"]["text"] == "You're in 1 group. 1 unread message in total."
    assert groups["reply"]["items"] == ["Goa Gang - 2 members, 1 unread message"]
    assert (await ask(client, "my groups"))["reply"]["text"] == "You're in 1 group. No unread messages."


async def test_greeting_unknown_questions_and_validation(client, alice):
    hello = await ask(client, "hi")
    assert hello["reply"]["text"].startswith("Hi Alice!") and hello["reply"]["suggestions"] == chatbot.STARTERS
    unknown = await ask(client, "what is the meaning of life")
    assert unknown["reply"]["text"].startswith("I'm not sure about that one") and unknown["destination"] is None
    assert (await ask(client, "what should I pack?"))["reply"]["text"].startswith("Which destination should I pack for?")
    assert (await ask(client, "Leh"))["reply"]["text"].startswith("Leh is in")           # just a name: destination facts
    assert (await ask(client, "pack", destination="Atlantis"))["reply"]["text"].startswith("Which destination")   # bad context is ignored

    assert (await client.post("/api/chat", json={"message": "   "})).status_code == 422
    assert (await client.post("/api/chat", json={"message": "x" * 301})).status_code == 422
    async with make_client() as anon:
        assert (await anon.post("/api/chat", json={"message": "hi"})).status_code == 401


# ------------------------------------------------------------------ optional AI model for unmatched questions
import httpx
import pytest

from app.config import settings
from app.services import assistant_llm


@pytest.fixture
def model(monkeypatch):
    """Configures a fake Groq-style key and replaces the outbound call. `calls` records what was sent."""
    monkeypatch.setattr(settings, "assistant_api_key", "gsk_test_key")
    monkeypatch.setattr(settings, "assistant_model", "test-model")
    monkeypatch.setattr(settings, "assistant_base_url", "")
    assistant_llm._cache.clear()
    assistant_llm._asked.clear()
    state = {"calls": [], "status": 200, "content": "October to March is pleasant.", "raise": None}

    async def fake_post(url, headers, body):
        state["calls"].append({"url": url, "headers": headers, "body": body})
        if state["raise"]:
            raise state["raise"]
        return httpx.Response(state["status"], json={"choices": [{"message": {"content": state["content"]}}]})

    monkeypatch.setattr(assistant_llm, "_post", fake_post)
    return state


async def test_without_a_key_unmatched_questions_get_the_builtin_reply(client, alice, monkeypatch):
    monkeypatch.setattr(settings, "assistant_api_key", "")
    r = await ask(client, "what is the meaning of life")
    assert r["source"] == "travelsync-data" and r["reply"]["text"].startswith("I'm not sure about that one")
    assert "unmatched" not in r["reply"]


async def test_model_answers_only_unmatched_questions_and_gets_only_the_question(client, alice, model):
    await create_trip(client, "Goa")
    matched = await ask(client, "top places in Goa")                       # built-in answer: the model is not called
    assert matched["source"] == "travelsync-data" and model["calls"] == []

    r = await ask(client, "When is the best season for a road journey?")
    assert r["source"] == "ai-model" and r["reply"]["text"] == "October to March is pleasant."
    call = model["calls"][0]
    assert call["url"] == "https://api.groq.com/openai/v1/chat/completions"         # provider recognised from the key
    assert call["headers"] == {"Authorization": "Bearer gsk_test_key"} and call["body"]["model"] == "test-model"
    sent = str(call["body"]["messages"])
    assert "When is the best season for a road journey?" in sent
    assert "Alice" not in sent and "alice@example.com" not in sent and "Goa" not in sent    # nothing about the user

    again = await ask(client, "  when is the BEST season for a road journey?  ")    # same question: served from the cache
    assert again["source"] == "ai-model" and len(model["calls"]) == 1


@pytest.mark.parametrize("failure", ["quota", "timeout", "empty", "garbage"])
async def test_model_failures_fall_back_to_the_builtin_reply(client, alice, model, failure):
    if failure == "quota":
        model["status"] = 429
    elif failure == "timeout":
        model["raise"] = httpx.ReadTimeout("too slow")
    elif failure == "empty":
        model["content"] = "   "
    else:
        model["content"] = None
    r = await client.post("/api/chat", json={"message": "tell me a travel story"})
    assert r.status_code == 200
    assert r.json()["source"] == "travelsync-data" and r.json()["reply"]["text"].startswith("I'm not sure about that one")


async def test_each_user_gets_a_limited_number_of_model_questions(client, alice, model):
    for n in range(assistant_llm.MAX_PER_USER):
        assert (await ask(client, f"random travel question number {n} zzz"))["source"] == "ai-model"
    over = await ask(client, "one more random travel question zzz")
    assert over["source"] == "travelsync-data" and len(model["calls"]) == assistant_llm.MAX_PER_USER


def test_provider_is_recognised_from_the_key_or_set_explicitly(monkeypatch):
    monkeypatch.setattr(settings, "assistant_model", "m")
    monkeypatch.setattr(settings, "assistant_base_url", "")
    monkeypatch.setattr(settings, "assistant_api_key", "xai-abc")
    assert assistant_llm.base_url() == "https://api.x.ai/v1" and assistant_llm.is_configured()
    monkeypatch.setattr(settings, "assistant_api_key", "sk-something-else")
    assert not assistant_llm.is_configured()                               # unknown provider and no base URL
    monkeypatch.setattr(settings, "assistant_base_url", "https://example.test/v1")
    assert assistant_llm.is_configured()
    monkeypatch.setattr(settings, "assistant_model", "")
    assert not assistant_llm.is_configured()                               # a model name is required


async def test_open_question_about_a_destination_goes_to_the_model_with_facts_as_the_fallback(client, alice, model):
    r = await ask(client, "plan me a 2 day itinerary for Jaipur")
    assert r["source"] == "ai-model" and r["destination"] == "Jaipur" and len(model["calls"]) == 1
    assert (await ask(client, "Jaipur"))["source"] == "travelsync-data"            # just the name: built-in facts
    model["status"] = 429                                                          # quota gone: facts, not an error
    r = await ask(client, "what is the vibe like in Jaipur these days")
    assert r["source"] == "travelsync-data" and r["reply"]["text"].startswith("Jaipur is in Rajasthan")
    assert "unmatched" not in r["reply"]
