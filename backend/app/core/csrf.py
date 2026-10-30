"""
CSRF defence for cookie-authenticated requests.

The auth cookie is SameSite=Lax (blocks cross-site POST/PUT/PATCH/DELETE in modern browsers).
As defence in depth this middleware also checks the `Origin` (or `Referer`) header of every
state-changing /api request against the configured frontend origins:

  * Origin/Referer present and not allowed         -> 403
  * Origin/Referer both missing but a cookie sent  -> 403 (browsers always send Origin on these methods)
  * No cookie and no Origin (curl, server-to-server) -> allowed; there is no ambient credential to abuse
"""

from urllib.parse import urlparse

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.core.error_handlers import error_body

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_of(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


async def csrf_origin_middleware(request: Request, call_next):
    if request.method in UNSAFE_METHODS and request.url.path.startswith("/api"):
        origin = request.headers.get("origin")
        if origin is None and request.headers.get("referer"):
            origin = _origin_of(request.headers["referer"])
        allowed = set(settings.cors_origins)
        host = request.headers.get("host")
        if host:
            allowed.add(f"{request.url.scheme}://{host}")
        has_cookie = settings.cookie_name in request.cookies
        if (origin and origin not in allowed) or (not origin and has_cookie):
            return JSONResponse(status_code=403, content=error_body("This request was blocked for your protection (cross-site request).", 403))
    return await call_next(request)
