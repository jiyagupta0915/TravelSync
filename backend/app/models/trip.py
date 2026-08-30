from typing import Optional

from pydantic import BaseModel


class TripCreate(BaseModel):
    destination: str = ""
    duration: Optional[int] = None
    budget: Optional[float] = None
    traveller_type: Optional[str] = None
    source: Optional[str] = "known-destination"


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
