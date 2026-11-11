"""ASGI middleware: security headers, request-size limit, rate limiting.

Rate limiting is an in-process token bucket keyed by client IP — adequate
for the single-node Phase 1 deployment. A Redis-backed limiter can replace
it without changing call sites.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if request.url.path in ("/api/v1/health", "/api/v1/system/status"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = settings.rate_limit_window_seconds
        bucket = self._buckets[ip]
        while bucket and bucket[0] < now - window:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_requests:
            retry_after = max(1, int(bucket[0] + window - now))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"detail": "Rate limit exceeded; slow down."},
            )
        bucket.append(now)
        return await call_next(request)
