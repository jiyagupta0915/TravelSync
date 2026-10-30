"""
/api/users/me  - the logged-in user's own profile and saved settings.

The user is always the one in the session cookie; there is no user id in any URL or body, so
there is nothing to tamper with. Email changes are intentionally not offered (they would need
verification); `email`, ids and credentials are rejected by the schemas (extra="forbid").
"""

from fastapi import APIRouter, Depends

from app.database import get_db
from app.dependencies import require_current_user
from app.models.user import ProfileUpdate, SettingsUpdate
from app.routers.auth import serialize_user

router = APIRouter(prefix="/api/users/me", tags=["users"])


@router.get("")
async def get_profile(user: dict = Depends(require_current_user)):
    return {"user": serialize_user(user)}


@router.patch("")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(require_current_user)):
    changes = payload.model_dump(exclude_unset=True)
    if "home_city" in changes and changes["home_city"] == "":
        await get_db().users.update_one({"_id": user["_id"]}, {"$unset": {"home_city": ""}})
        user.pop("home_city", None)
        changes.pop("home_city")
    if changes:
        await get_db().users.update_one({"_id": user["_id"]}, {"$set": changes})
        user.update(changes)
    return {"user": serialize_user(user)}


@router.get("/settings")
async def get_settings(user: dict = Depends(require_current_user)):
    return {"settings": user.get("settings") or {}}


@router.put("/settings")
async def put_settings(payload: SettingsUpdate, user: dict = Depends(require_current_user)):
    stored = {key: value for key, value in payload.model_dump().items() if value is not None}
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"settings": stored}})
    return {"settings": stored}
