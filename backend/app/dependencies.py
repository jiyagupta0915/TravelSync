"""
Reusable FastAPI dependencies.

`get_current_user` is optional (returns None when there is no valid session) and is used by
/api/auth/me. `require_current_user` raises 401 and guards every private endpoint.

The user is ALWAYS re-derived from the signed JWT cookie and re-read from MongoDB; nothing the
client sends (ids, roles, flags) is ever trusted as proof of identity or permission.

An invalid / expired / revoked token means "not logged in" (None). A database failure is NOT the
same thing: it surfaces as 503 so the frontend can tell "your session is gone" from "try again".
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status
from pymongo.errors import PyMongoError

from app.config import settings
from app.core.security import decode_token_claims
from app.database import get_db


async def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None

    claims = decode_token_claims(token)
    if not claims:
        request.state.invalid_session = True
        return None

    try:
        object_id = ObjectId(claims["sub"])
    except (InvalidId, TypeError):
        request.state.invalid_session = True
        return None

    try:
        user = await get_db().users.find_one({"_id": object_id})
    except PyMongoError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="We couldn't verify your session right now. Please try again.")

    if user is None or int(claims.get("tv", 0)) != int(user.get("token_version", 0)):
        request.state.invalid_session = True
        return None
    return user


async def require_current_user(user: dict | None = Depends(get_current_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be logged in to continue.")
    return user
