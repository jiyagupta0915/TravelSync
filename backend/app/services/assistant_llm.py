"""
Optional AI model behind the TravelSync assistant, for questions the built-in answers don't cover.

It is deliberately a helper that is allowed to fail: `ask_model` returns the model's answer as text, or None when no
model is configured, the per-user limit is reached, the call times out, the provider refuses (e.g. the free quota
ran out) or the answer is empty. The caller then shows the normal built-in reply, so a flaky or exhausted key never
breaks the assistant.

Free-tier quotas are small, so:
  * only the question is sent (no user name, trips, groups or anything else about the user);
  * identical questions are answered from a small in-memory cache;
  * each user gets a limited number of model questions per time window.

Works with any OpenAI-compatible chat-completions API (Groq, xAI Grok, OpenRouter, Mistral, ...). See .env.example.
"""

import logging
import time
from collections import OrderedDict, defaultdict, deque

import httpx

from app.config import settings

logger = logging.getLogger("travelsync.assistant")

# Recognised from the start of the key when ASSISTANT_BASE_URL is not set.
KNOWN_PROVIDERS = {"gsk_": "https://api.groq.com/openai/v1", "xai-": "https://api.x.ai/v1"}

SYSTEM_PROMPT = (
    "You are the TravelSync assistant, a helper inside a trip-planning app for travel within India. "
    "Answer the traveller's question in plain text, in at most 120 words, with no markdown. "
    "Only answer questions about travel; for anything else, say you can only help with travel planning. "
    "Do not state exact prices, opening hours or timetables as facts - say they should be checked. "
    "Do not give medical advice; for health questions, point to the app's Health & Safety page and official sources."
)

MAX_PER_USER, WINDOW_SECONDS = 8, 10 * 60        # model questions each user may ask per window
CACHE_SIZE = 200

_cache: "OrderedDict[str, str]" = OrderedDict()
_asked: dict[str, deque] = defaultdict(deque)


def base_url() -> str:
    if settings.assistant_base_url:
        return settings.assistant_base_url
    return next((url for prefix, url in KNOWN_PROVIDERS.items() if settings.assistant_api_key.startswith(prefix)), "")


def is_configured() -> bool:
    return bool(settings.assistant_api_key and settings.assistant_model and base_url())


def _within_limit(user_key: str) -> bool:
    events, cutoff = _asked[user_key], time.monotonic() - WINDOW_SECONDS
    while events and events[0] < cutoff:
        events.popleft()
    if len(events) >= MAX_PER_USER:
        return False
    events.append(time.monotonic())
    return True


async def _post(url: str, headers: dict, body: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=settings.assistant_timeout_seconds) as client:
        return await client.post(url, headers=headers, json=body)


async def ask_model(question: str, user_key: str) -> str | None:
    """The model's answer to `question`, or None if there is no usable answer (see the module docstring)."""
    if not is_configured():
        return None
    cache_key = " ".join(question.lower().split())
    if cache_key in _cache:
        _cache.move_to_end(cache_key)
        return _cache[cache_key]
    if not _within_limit(user_key):
        return None
    try:
        response = await _post(
            f"{base_url()}/chat/completions",
            {"Authorization": f"Bearer {settings.assistant_api_key}"},
            # Room for the answer (about 120 words) plus the hidden "reasoning" tokens some models spend first.
            {"model": settings.assistant_model, "max_tokens": 700, "temperature": 0.4,
             "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]},
        )
        if response.status_code != 200:
            # e.g. 429 = quota used up, 404/400 = model name not available to this key, 401 = bad key.
            logger.warning("Assistant model returned HTTP %s: %s", response.status_code, response.text[:300])
            return None
        answer = (response.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:                       # timeout, network, unexpected response shape
        logger.warning("Assistant model call failed: %s", type(exc).__name__)
        return None
    if not answer:
        return None
    answer = answer[:1500]
    _cache[cache_key] = answer
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return answer
