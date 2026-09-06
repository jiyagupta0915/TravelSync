from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["Clothing", "Weather", "Electronics", "Documents", "Activity", "Health"]


class PackingItem(BaseModel):
    id: str
    category: Category
    name: str
    quantity: int = 1
    packed: bool = False
    source: Literal["rule", "custom"] = "rule"


class GenerateRequest(BaseModel):
    activities: list[str] = Field(default_factory=list)
    regenerate: bool = False


class SetDatesRequest(BaseModel):
    start_date: str  # ISO date, e.g. "2026-09-20"
    end_date: str


class UpdateItemsRequest(BaseModel):
    items: list[PackingItem]


class PackingListOut(BaseModel):
    trip_id: str
    tier: Literal["climate", "forecast"]
    weather_summary: Optional[str] = None
    items: list[PackingItem]
    generated_at: str
    updated_at: str