from pydantic import BaseModel

class PlaceOut(BaseModel):
    rank: int
    place_name: str
    category: str
    rating: float
    popularity: float
    duration_hrs: float
    best_season: str
    description: str
    score: float

class TopPlacesResponse(BaseModel):
    destination: str
    places: list[PlaceOut]