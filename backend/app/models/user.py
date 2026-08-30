"""
Auth request schemas.

Fields are intentionally left un-constrained at the schema level (no
min_length, no EmailStr) so that missing/invalid values fall through to
the same hand-written validation the API used previously, producing the
exact same user-facing error messages instead of FastAPI's generic
422 validation-error text.
"""

from pydantic import BaseModel


class UserSignup(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""


class UserLogin(BaseModel):
    email: str = ""
    password: str = ""


class UserOut(BaseModel):
    id: str
    name: str
    email: str
