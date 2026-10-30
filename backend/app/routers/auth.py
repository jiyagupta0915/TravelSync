"""
/api/auth/*  - signup, login, session, logout, password change and (provider-gated) password recovery.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.core.rate_limit import FailureLimiter
from app.core.security import (
    burn_password_check, create_access_token, hash_password, hash_reset_token, new_reset_token, verify_password,
)
from app.database import get_db
from app.dependencies import get_current_user, require_current_user
from app.models.user import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, UserLogin, UserSignup,
)
from app.services.email_service import EmailDeliveryError, send_email

logger = logging.getLogger("travelsync.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

login_limiter = FailureLimiter(settings.login_max_failures, settings.login_window_seconds)
recovery_limiter = FailureLimiter(5, 60 * 60)


def serialize_user(user: dict) -> dict:
    """Only whitelisted, non-sensitive fields ever leave the server."""
    return {
        "id": str(user["_id"]),
        "name": user.get("name") or "",
        "email": user.get("email") or "",
        "home_city": user.get("home_city") or "",
        "settings": user.get("settings") or {},
    }


def _cookie_kwargs() -> dict:
    return {"httponly": True, "samesite": settings.cookie_samesite, "secure": settings.cookie_secure, "path": "/"}


def set_auth_cookie(response: Response, user: dict) -> None:
    token = create_access_token(str(user["_id"]), user.get("token_version", 0))
    response.set_cookie(key=settings.cookie_name, value=token, max_age=settings.jwt_expires_minutes * 60, **_cookie_kwargs())


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, **_cookie_kwargs())


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, response: Response):
    db = get_db()
    if await db.users.find_one({"email": payload.email}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")

    user = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "token_version": 0,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await db.users.insert_one(user)
    except DuplicateKeyError:           # lost a race with a parallel signup: the unique index is the real guard
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")
    user["_id"] = result.inserted_id

    set_auth_cookie(response, user)       # automatic login after signup
    return {"user": serialize_user(user)}


@router.post("/login")
async def login(payload: UserLogin, request: Request, response: Response):
    email = payload.email.strip().lower()
    password = payload.password
    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password are required.")

    key = f"{_client_ip(request)}|{email}"
    login_limiter.check(key)

    user = await get_db().users.find_one({"email": email})
    if not user or not verify_password(password, user.get("password_hash", "")):
        if not user:
            burn_password_check(password)
        login_limiter.record(key)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    login_limiter.reset(key)
    set_auth_cookie(response, user)
    return {"user": serialize_user(user)}


@router.get("/me")
async def me(request: Request, response: Response, user: dict | None = Depends(get_current_user)):
    """200 {"user": null} = no valid session (and a stale cookie is cleared). 503 = we could not check."""
    response.headers["Cache-Control"] = "no-store"
    if not user:
        if getattr(request.state, "invalid_session", False):
            clear_auth_cookie(response)
        return {"user": None}
    return {"user": serialize_user(user)}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully."}


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, response: Response, user: dict = Depends(require_current_user)):
    if not verify_password(payload.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=403, detail="Your current password is incorrect.")

    db = get_db()
    new_version = int(user.get("token_version", 0)) + 1
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "token_version": new_version,
                  "password_changed_at": datetime.now(timezone.utc)}},
    )
    user["token_version"] = new_version          # every older session is now revoked; this one gets a fresh cookie
    set_auth_cookie(response, user)
    return {"message": "Password updated. Other devices have been signed out."}


@router.get("/recovery-status")
async def recovery_status():
    """Lets the UI say honestly whether password recovery can work on this server."""
    return {"available": settings.email_configured}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, request: Request):
    if not settings.email_configured:
        raise HTTPException(
            status_code=503,
            detail="Password recovery by email isn't available on this server because email delivery is not configured.",
        )
    key = _client_ip(request)
    recovery_limiter.check(key)
    recovery_limiter.record(key)

    db = get_db()
    user = await db.users.find_one({"email": payload.email}, {"_id": 1, "email": 1})
    if user:
        token, token_hash = new_reset_token()
        await db.password_resets.delete_many({"user_id": user["_id"]})
        await db.password_resets.insert_one({
            "user_id": user["_id"], "token_hash": token_hash, "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_minutes),
        })
        link = f"{settings.frontend_base_url}/reset-password?token={token}"
        body = (f"Hello,\n\nUse the link below to choose a new TravelSync password. It works once and expires in "
                f"{settings.password_reset_minutes} minutes.\n\n{link}\n\nIf you didn't ask for this, you can ignore this email.\n")
        try:
            await send_email(user["email"], "Reset your TravelSync password", body)
        except EmailDeliveryError as exc:
            logger.error("Password-reset email could not be delivered: %s", exc)
    # Same answer whether or not the account exists, so this endpoint cannot be used to discover accounts.
    return {"message": "If an account exists for that email, a reset link has been sent. It expires in "
                       f"{settings.password_reset_minutes} minutes."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    db = get_db()
    now = datetime.now(timezone.utc)
    record = await db.password_resets.find_one_and_delete(
        {"token_hash": hash_reset_token(payload.token), "expires_at": {"$gt": now.replace(tzinfo=None)}}
    )
    if record is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Please request a new one.")

    user = await db.users.find_one({"_id": record["user_id"]}, {"token_version": 1})
    if user is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Please request a new one.")
    await db.users.update_one(
        {"_id": record["user_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password),
                  "token_version": int(user.get("token_version", 0)) + 1,
                  "password_changed_at": now}},
    )
    await db.password_resets.delete_many({"user_id": record["user_id"]})
    return {"message": "Password updated. You can now log in with your new password."}
