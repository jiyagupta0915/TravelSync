from typing import Dict, Optional

from pydantic import BaseModel


class RecommendRequest(BaseModel):
    preferences: Dict[str, float]
    importance: Dict[str, float]
    traveller_type: str
    duration: int
    budget: Optional[float] = None
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    max_distance_km: Optional[float] = None
    top_n: Optional[int] = 6
