from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.limits import MAX_BUDGET_INR, MAX_DURATION_DAYS, MIN_DURATION_DAYS
from app.models.user import clean_text


class GroupCreate(BaseModel):
    name: str
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return clean_text(v, "Group name", 2, 60)

    @field_validator("description")
    @classmethod
    def _desc(cls, v: str) -> str:
        v = v.strip()
        return clean_text(v, "Description", 1, 300) if v else ""


class JoinGroup(BaseModel):
    invite_code: str = Field(min_length=4, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class MessageCreate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty.")
        if len(v) > 1000:
            raise ValueError("Message must be at most 1000 characters.")
        return v


class SuggestionCreate(BaseModel):
    destination: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=300)
    budget: Optional[float] = Field(default=None, gt=0, le=MAX_BUDGET_INR, allow_inf_nan=False)
    duration: Optional[int] = Field(default=None, ge=MIN_DURATION_DAYS, le=MAX_DURATION_DAYS)
    preferences: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("note", "destination")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("preferences")
    @classmethod
    def _prefs(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            item = item.strip()
            if not item or len(item) > 30:
                raise ValueError("Each preference must be 1-30 characters.")
            cleaned.append(item)
        return cleaned


class DecideRequest(BaseModel):
    suggestion_id: str = Field(min_length=24, max_length=24)
