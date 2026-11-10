from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str
    destination: Optional[str] = Field(default=None, max_length=120)   # what the conversation was about so far

    @field_validator("message")
    @classmethod
    def _message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Type a question first.")
        if len(v) > 300:
            raise ValueError("Please keep your question under 300 characters.")
        return v
