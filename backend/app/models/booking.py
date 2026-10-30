from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

BookingKind = Literal["hotel", "flight", "train", "bus", "activity", "other"]


class BookingBase(BaseModel):
    kind: BookingKind
    title: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="", max_length=80)
    reference: str = Field(default="", max_length=60)          # the confirmation / PNR / ticket number the USER typed in
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    amount_inr: Optional[float] = Field(default=None, ge=0, le=100_000_000, allow_inf_nan=False)
    notes: str = Field(default="", max_length=500)

    @field_validator("title", "provider", "reference", "notes")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("Title is required.")
        return v

    @model_validator(mode="after")
    def _dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date cannot be earlier than the start date.")
        return self


class BookingCreate(BookingBase):
    trip_id: str = Field(min_length=24, max_length=24)


class BookingUpdate(BookingBase):
    """Full replacement of the editable fields (the trip it belongs to cannot be changed)."""
