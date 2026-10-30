"""
One error format for the whole API:

    {"error": "<message safe to show a user>", "code": "<machine readable>", "details": [{"field", "message"}]?}

`error` is the key the existing frontend already reads. `code` and `details` are additive.
Server-side problems (database down, bugs) are logged with their traceback but only a generic
message is returned - no stack traces, driver messages or connection strings ever reach the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import DatabaseUnavailable

logger = logging.getLogger("travelsync.errors")

UNPROCESSABLE_ENTITY = 422

CODES = {
    400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed",
    409: "conflict", 413: "payload_too_large", 422: "validation_error", 429: "rate_limited",
    500: "server_error", 502: "upstream_error", 503: "service_unavailable", 504: "upstream_timeout",
}


def error_body(message: str, status_code: int, details: list | None = None) -> dict:
    body = {"error": message, "code": CODES.get(status_code, "error")}
    if details:
        body["details"] = details
    return body


def _clean_message(message: str) -> str:
    return message.removeprefix("Value error, ").strip()


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
    return JSONResponse(status_code=exc.status_code, content=error_body(detail, exc.status_code), headers=getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err.get("loc", ()) if part not in ("body", "query", "path"))
        if err.get("type") == "json_invalid":
            message = "The request body is not valid JSON."
        else:
            message = _clean_message(str(err.get("msg", "Invalid value.")))
        details.append({"field": field, "message": message})
    if not details:
        message = "Invalid request."
    else:
        first = details[0]
        message = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(status_code=UNPROCESSABLE_ENTITY, content=error_body(message, UNPROCESSABLE_ENTITY, details))


async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content=error_body("The database is temporarily unavailable. Please try again in a moment.", 503),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=error_body("Something went wrong on our side. Please try again.", 500))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PyMongoError, database_exception_handler)
    app.add_exception_handler(DatabaseUnavailable, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
