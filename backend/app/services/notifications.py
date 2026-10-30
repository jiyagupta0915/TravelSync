"""In-app notifications. Each one is created by a real event (a member joined, a destination was suggested ...)."""

from datetime import datetime, timezone

from bson import ObjectId


async def notify(db, user_ids, kind: str, message: str, link: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    docs = [
        {"user_id": uid, "kind": kind, "message": message[:200], "link": link, "read": False, "created_at": now}
        for uid in user_ids
    ]
    if docs:
        await db.notifications.insert_many(docs)


def serialize_notification(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]), "kind": doc.get("kind"), "message": doc.get("message", ""), "link": doc.get("link"),
        "read": bool(doc.get("read")), "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else None,
    }


def object_id_or_none(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None
