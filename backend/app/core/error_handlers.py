"""
Normalises every error response to `{"error": "message"}`.

FastAPI's defaults are `{"detail": "..."}` for HTTPException and a
structured list under `detail` for request-validation errors. The
existing TravelSync frontend reads `data.error` on any non-2xx
response, so these handlers keep that contract intact without
requiring any frontend changes.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Hard-coded rather than fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY /
# _CONTENT so this keeps working across both older and newer
# FastAPI/Starlette releases, which renamed this constant.
UNPROCESSABLE_ENTITY = 422


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = ".".join(str(part) for part in first["loc"] if part != "body")
        message = f"{field}: {first['msg']}" if field else first["msg"]
    else:
        message = "Invalid request."
    return JSONResponse(status_code=UNPROCESSABLE_ENTITY, content={"error": message})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
