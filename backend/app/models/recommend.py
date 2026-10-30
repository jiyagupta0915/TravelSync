from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.limits import MAX_BUDGET_INR, MAX_DISTANCE_KM, MAX_DURATION_DAYS, MIN_DURATION_DAYS


class RecommendRequest(BaseModel):
    preferences: Dict[str, float]
    importance: Dict[str, float]
    traveller_type: str = Field(max_length=20)
    duration: int = Field(ge=MIN_DURATION_DAYS, le=MAX_DURATION_DAYS)
    budget: Optional[float] = Field(default=None, gt=0, le=MAX_BUDGET_INR, allow_inf_nan=False)
    start_lat: Optional[float] = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    start_lon: Optional[float] = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    max_distance_km: Optional[float] = Field(default=None, gt=0, le=MAX_DISTANCE_KM, allow_inf_nan=False)
    top_n: Optional[int] = Field(default=6, ge=1, le=10)

    @field_validator("preferences", "importance")
    @classmethod
    def _bounded(cls, value: Dict[str, float]) -> Dict[str, float]:
        if len(value) > 40:
            raise ValueError("Too many entries.")
        for key, number in value.items():
            if len(key) > 40:
                raise ValueError("Feature name is too long.")
            if not 0 <= number <= 3:
                raise ValueError("Values must be between 0 and 3.")
        return value
