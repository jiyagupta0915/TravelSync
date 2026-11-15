from pydantic import BaseModel, Field


class OriginRequest(BaseModel):
    """The user's own location, sent only when they press "Show my location" and ask for driving distances."""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)