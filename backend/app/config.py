"""
Centralised application settings.

All configuration is read from environment variables (see .env.example).
Nothing here is hard-coded for production use - only safe local-dev
fallbacks are provided so the app can boot without a .env file present.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = APP_DIR.parent                        # backend/
load_dotenv(BACKEND_DIR / ".env")


def _split_csv_env(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Settings:
    # MongoDB
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "travelsync")

    # Auth / JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-development-secret")
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = int(os.getenv("JWT_EXPIRES_MINUTES", str(60 * 24 * 7)))  # 7 days

    # Cookies
    cookie_name: str = "access_token"
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    # CORS
    cors_origins: list[str] = _split_csv_env(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    # Misc
    environment: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
