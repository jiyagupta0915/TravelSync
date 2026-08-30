from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import UserLogin, UserSignup

router = APIRouter(prefix="/api/auth", tags=["auth"])


def serialize_user(user: dict) -> dict:
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


def set_auth_cookie(response: Response, user_id: str) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, response: Response):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    password = payload.password

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email and password are required.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must contain at least 8 characters.")

    try:
        db = get_db()
        user = {
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc),
        }
        result = await db.users.insert_one(user)
        user["_id"] = result.inserted_id
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists. Please log in."
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not connect to MongoDB: {exc}")

    # Automatic login immediately after signup.
    set_auth_cookie(response, str(user["_id"]))
    return {"user": serialize_user(user)}


@router.post("/login")
async def login(payload: UserLogin, response: Response):
    email = payload.email.strip().lower()
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    try:
        db = get_db()
        user = await db.users.find_one({"email": email})
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Could not connect to MongoDB: {exc}")

    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    set_auth_cookie(response, str(user["_id"]))
    return {"user": serialize_user(user)}


@router.get("/me")
async def me(user: dict | None = Depends(get_current_user)):
    if not user:
        return {"user": None}
    return {"user": serialize_user(user)}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(settings.cookie_name, path="/")
    return {"message": "Logged out successfully."}
