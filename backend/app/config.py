"""
Centralised application settings.

All configuration is read from environment variables (see .env.example).
Only safe local-development fallbacks are provided so the app can boot without a
.env file. In production (ENVIRONMENT=production) `validate_settings()` refuses to
start with a missing/weak JWT secret, an insecure cookie or a wildcard CORS origin.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = APP_DIR.parent                        # backend/
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger("travelsync.config")

DEV_DEFAULT_SECRET = "change-this-development-secret"


def _split_csv_env(value: str) -> list[str]:
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    # Misc
    environment: str = os.getenv("ENVIRONMENT", "development").strip().lower()

    # MongoDB
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "travelsync")

    # Auth / JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", DEV_DEFAULT_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = _int_env("JWT_EXPIRES_MINUTES", 60 * 24 * 7)  # 7 days

    # Cookies. Secure defaults to ON in production; set COOKIE_SECURE=false only for plain-http local use.
    cookie_name: str = "access_token"
    cookie_secure: bool = _bool_env("COOKIE_SECURE", os.getenv("ENVIRONMENT", "development").strip().lower() == "production")
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()

    # CORS / CSRF: the browser origins allowed to call this API with cookies.
    cors_origins: list[str] = _split_csv_env(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    # Login throttling (in-memory, per process).
    login_max_failures: int = _int_env("LOGIN_MAX_FAILURES", 5)
    login_window_seconds: int = _int_env("LOGIN_WINDOW_SECONDS", 15 * 60)

    # Smart Stay Recommendations (Geoapify Places API). The key stays on the server only.
    geoapify_api_key: str = os.getenv("GEOAPIFY_API_KEY", "")

    # Password recovery. Recovery is only offered when an SMTP server is configured.
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = _int_env("SMTP_PORT", 587)
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_starttls: bool = _bool_env("SMTP_STARTTLS", True)
    frontend_base_url: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
    password_reset_minutes: int = _int_env("PASSWORD_RESET_MINUTES", 30)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


settings = Settings()


def validate_settings(current: Settings = settings) -> None:
    """Fail fast on unsafe production configuration; warn loudly in development."""
    problems: list[str] = []
    weak_secret = current.jwt_secret_key == DEV_DEFAULT_SECRET or len(current.jwt_secret_key) < 32
    if current.is_production:
        if weak_secret:
            problems.append("JWT_SECRET_KEY must be set to a random value of at least 32 characters.")
        if not current.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production (HTTPS only cookies).")
        if any(origin == "*" for origin in current.cors_origins) or not current.cors_origins:
            problems.append("CORS_ORIGINS must list the exact frontend origin(s); '*' is not allowed with cookies.")
        if problems:
            raise RuntimeError("Unsafe production configuration: " + " ".join(problems))
    elif weak_secret:
        logger.warning("Using the development JWT secret. Set JWT_SECRET_KEY before deploying.")
    if current.cookie_samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE must be one of lax, strict, none.")
    if current.cookie_samesite == "none" and not current.cookie_secure:
        raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true.")
