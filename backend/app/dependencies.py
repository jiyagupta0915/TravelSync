"""
Reusable FastAPI dependencies.

`get_current_user` is optional (returns None if not logged in) and is
used on public endpoints that behave differently for logged-in users
(e.g. /api/auth/me). `require_current_user` is the same lookup but
raises 401 if there is no valid session - use it on any endpoint that
must be authenticated (e.g. trip creation).

Backend-side auth is never trusted from frontend-supplied values: the
user is always re-derived from the signed JWT cookie and re-fetched
from MongoDB on every request.
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db


async def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None

    user_id = decode_access_token(token)
    if not user_id:
        return None

    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        return None

    db = get_db()
    return await db.users.find_one({"_id": object_id})


async def require_current_user(user: dict | None = Depends(get_current_user)) -> dict:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to continue.",
        )
    return user
