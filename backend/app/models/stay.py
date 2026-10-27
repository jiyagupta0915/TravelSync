from pydantic import BaseModel, Field


class SaveStayRequest(BaseModel):
    # Only the id of a stay travels from the browser. The server looks the stay up itself
    # in the current recommendations, so nobody can save made-up hotel details to a trip.
    stay_key: str = Field(min_length=8, max_length=64)