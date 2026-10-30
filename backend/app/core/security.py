"""
Password hashing (bcrypt) and JWT access-token creation/verification.

Passwords are never stored or logged in plaintext - only their bcrypt hash is persisted.
Auth state is a signed JWT in an httpOnly cookie, so JavaScript can never read it.

Tokens carry `sub` (user id), `iat`, `exp` and `tv` (token version). Bumping a user's
`token_version` (password change / reset) invalidates every token issued before it.
Verification pins the algorithm and *requires* `exp` and `sub`, so unsigned or
expiry-less tokens are rejected.
"""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# Used to spend the same time on "unknown email" as on "wrong password" (no user enumeration by timing).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: str, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tv": int(token_version),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token_claims(token: str) -> dict | None:
    """Returns the verified claims, or None when the token is invalid, tampered with or expired."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if not isinstance(claims.get("sub"), str):
        return None
    return claims


def decode_access_token(token: str) -> str | None:
    claims = decode_token_claims(token)
    return claims["sub"] if claims else None


def new_reset_token() -> tuple[str, str]:
    """(token to email, sha256 hash to store). Only the hash is ever persisted."""
    import hashlib

    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_reset_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
