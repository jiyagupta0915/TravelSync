from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.limits import MAX_BUDGET_INR, MAX_DURATION_DAYS, MIN_DURATION_DAYS


class TripCreate(BaseModel):
    destination: str = Field(default="", max_length=120)
    duration: Optional[int] = Field(default=None, ge=MIN_DURATION_DAYS, le=MAX_DURATION_DAYS)
    budget: Optional[float] = Field(default=None, gt=0, le=MAX_BUDGET_INR, allow_inf_nan=False)
    traveller_type: Optional[Literal["Family", "Couple", "Friends", "Solo"]] = None
    source: Optional[Literal["known-destination", "recommendation", "group-vote"]] = "known-destination"
    group_id: Optional[str] = Field(default=None, min_length=24, max_length=24)   # set when the trip comes from a group decision

    @field_validator("destination")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class TripOut(BaseModel):
    id: str
    user_id: str
    destination: str
    state: str
    region: str
    latitude: float
    longitude: float
    duration: Optional[int] = None
    budget: Optional[float] = None
    traveller_type: Optional[str] = None
    source: Optional[str] = None
    created_at: str
    status: str
