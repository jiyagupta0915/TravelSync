from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal["Clothing", "Weather", "Electronics", "Documents", "Activity", "Health"]
MAX_ITEMS = 200


class PackingItem(BaseModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    category: Category
    name: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=99)
    packed: bool = False
    source: Literal["rule", "custom"] = "rule"

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Item name cannot be empty.")
        return value


class GenerateRequest(BaseModel):
    activities: list[str] = Field(default_factory=list, max_length=12)
    regenerate: bool = False

    @field_validator("activities")
    @classmethod
    def _activities(cls, value: list[str]) -> list[str]:
        for entry in value:
            if not entry.strip() or len(entry) > 30:
                raise ValueError("Each activity must be 1-30 characters.")
        return value


class SetDatesRequest(BaseModel):
    start_date: str  # ISO date, e.g. "2026-09-20"
    end_date: str


class UpdateItemsRequest(BaseModel):
    items: list[PackingItem] = Field(max_length=MAX_ITEMS)

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Item ids must be unique.")
        return self


class PackingListOut(BaseModel):
    trip_id: str
    tier: Literal["climate", "forecast"]
    weather_summary: Optional[str] = None
    items: list[PackingItem]
    generated_at: str
    updated_at: str
