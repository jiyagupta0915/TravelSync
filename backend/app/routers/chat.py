"""
TravelSync assistant endpoint. The answer is built from TravelSync's own data by app/services/chatbot.py. Only when
that has no answer, and an AI model is configured, the question alone is sent to the model
(app/services/assistant_llm.py); if that fails for any reason the user gets the built-in "here is what I can help
with" reply. `source` in the response says which of the two produced the answer.

Login is required because some answers are about the user's own trips and groups; those are always read for the
session user, never from anything the client sends, and are never sent to the model.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import require_current_user
from app.models.chat import ChatRequest
from app.routers.groups import _unread_counts
from app.services import assistant_llm, chatbot

logger = logging.getLogger("travelsync.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def ask(payload: ChatRequest, user: dict = Depends(require_current_user)):
    db = get_db()
    trips = [t async for t in db.trips.find({"user_id": user["_id"]}).sort("created_at", -1)]
    group_docs = [g async for g in db.groups.find({"member_ids": user["_id"]}).sort("created_at", -1)]
    unread = await _unread_counts(db, user, [g["_id"] for g in group_docs])
    groups = [{"name": g["name"], "members": len(g["member_ids"]), "unread": unread[g["_id"]]} for g in group_docs]
    try:
        reply, destination = chatbot.answer(payload.message, user_name=user.get("name") or "there", trips=trips, groups=groups,
                                            context_destination=payload.destination)
    except Exception:
        logger.exception("The assistant could not answer")
        raise HTTPException(status_code=500, detail="The assistant couldn't answer that right now. Please try again.")
    source = "travelsync-data"
    if reply.pop("unmatched", False):
        generated = await assistant_llm.ask_model(payload.message, str(user["_id"]))
        if generated:
            reply = {"text": generated, "items": [], "links": [], "suggestions": chatbot.STARTERS[:3]}
            source = "ai-model"
    return {"reply": reply, "destination": destination, "source": source}
