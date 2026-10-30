from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.dependencies import require_current_user
from app.services.notifications import object_id_or_none, serialize_notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: dict = Depends(require_current_user)):
    db = get_db()
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("created_at", -1).limit(30)
    items = [serialize_notification(doc) async for doc in cursor]
    unread = await db.notifications.count_documents({"user_id": user["_id"], "read": False})
    return {"notifications": items, "unread_count": unread}


@router.post("/read-all")
async def mark_all_read(user: dict = Depends(require_current_user)):
    await get_db().notifications.update_many({"user_id": user["_id"], "read": False}, {"$set": {"read": True}})
    return {"unread_count": 0}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(require_current_user)):
    oid = object_id_or_none(notification_id)
    if oid is None:
        raise HTTPException(status_code=400, detail="Invalid notification id.")
    result = await get_db().notifications.update_one({"_id": oid, "user_id": user["_id"]}, {"$set": {"read": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"read": True}
