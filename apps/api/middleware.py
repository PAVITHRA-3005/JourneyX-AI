from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limit per client IP (default 60 requests per minute).

    State is in-process, which is appropriate for a single uvicorn worker.
    Use a shared store for multi-worker deployments.
    """

    def __init__(self, app, rpm: int | None = None) -> None:
        super().__init__(app)
        self.rpm = rpm or int(os.getenv("JOURNEYX_RATE_LIMIT_RPM", "60"))
        self._lock = Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            bucket = [t for t in self._hits[key] if t >= window_start]
            if len(bucket) >= self.rpm:
                self._hits[key] = bucket
                return False
            bucket.append(now)
            self._hits[key] = bucket
            return True

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)
        key = self._client_key(request)
        if not self._allow(key):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit_rpm": self.rpm,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        return await call_next(request)