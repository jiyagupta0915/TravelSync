"""
Auth, profile and settings request schemas.

* Signup: name / email / password are validated here. The password policy applies to NEW passwords only
  (signup, change, reset). Login deliberately does not apply it, so existing users with older, weaker
  passwords can still sign in.
* Profile/settings payloads forbid unknown fields, so a client can never smuggle in `email`, `role`,
  `password_hash`, `token_version`, or another user's id.
"""

import re
import unicodedata
from typing import Literal, Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.password_policy import validate_new_password
from app.models.limits import MAX_BUDGET_INR, MAX_DURATION_DAYS, MIN_DURATION_DAYS

_WS = re.compile(r"\s+")


def clean_text(value: str, label: str, min_len: int, max_len: int, require_letter: bool = False) -> str:
    value = _WS.sub(" ", unicodedata.normalize("NFC", value)).strip()
    if any(unicodedata.category(ch).startswith("C") for ch in value):
        raise ValueError(f"{label} contains invalid characters.")
    if len(value) < min_len:
        raise ValueError(f"{label} must be at least {min_len} characters." if min_len > 1 else f"{label} is required.")
    if len(value) > max_len:
        raise ValueError(f"{label} must be at most {max_len} characters.")
    if require_letter and not any(ch.isalpha() for ch in value):
        raise ValueError(f"{label} must contain at least one letter.")
    return value


def normalise_email(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Email is required.")
    if len(value) > 254:
        raise ValueError("Email is too long.")
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError("Enter a valid email address.")


class UserSignup(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value, "Name", 2, 80, require_letter=True)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalise_email(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_new_password(value)


class UserLogin(BaseModel):
    """No password policy here on purpose (existing users keep working)."""

    email: str = Field(default="", max_length=254)
    password: str = Field(default="", max_length=256)


class UserOut(BaseModel):
    id: str
    name: str
    email: str


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    home_city: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, value):
        return None if value is None else clean_text(value, "Name", 2, 80, require_letter=True)

    @field_validator("home_city")
    @classmethod
    def _city(cls, value):
        if value is None or not value.strip():
            return ""      # empty string clears the field
        return clean_text(value, "Home city", 2, 80)

    @model_validator(mode="after")
    def _something_to_update(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be empty.")
        return self


class SettingsUpdate(BaseModel):
    """Whole-document replacement of the user's saved defaults. null clears a value."""

    model_config = ConfigDict(extra="forbid")

    default_traveller_type: Optional[Literal["Family", "Couple", "Friends", "Solo"]] = None
    default_duration_days: Optional[int] = Field(default=None, ge=MIN_DURATION_DAYS, le=MAX_DURATION_DAYS)
    default_budget_inr: Optional[int] = Field(default=None, ge=1, le=MAX_BUDGET_INR)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_new_password(value)

    @model_validator(mode="after")
    def _different(self):
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self


class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalise_email(value)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_new_password(value)
