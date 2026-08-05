from __future__ import annotations

import secrets
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from .config import get_settings


PUBLIC_PATHS = {"/", "/health", "/ready", "/docs", "/openapi.json", "/redoc"}


def _matches(candidate: str | None, expected: str | None) -> bool:
    return bool(candidate and expected and secrets.compare_digest(candidate, expected))


def _is_authorized(request: Request) -> bool:
    settings = get_settings()
    if settings.allow_unauthenticated:
        return True
    return _matches(request.headers.get("x-api-key"), settings.direct_api_key) or _matches(
        request.headers.get("x-rapidapi-proxy-secret"),
        settings.rapidapi_proxy_secret,
    )


async def access_and_safety_middleware(request: Request, call_next) -> Response:
    settings = get_settings()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.perf_counter()

    if request.url.path.startswith("/v1/"):
        if not settings.access_is_configured:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "service_not_configured",
                    "message": "API access is not configured on this deployment.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "request_too_large",
                            "message": f"Request exceeds {settings.max_request_bytes} bytes.",
                            "request_id": request_id,
                        },
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_content_length",
                        "message": "Content-Length must be an integer.",
                        "request_id": request_id,
                    },
                    headers={"X-Request-ID": request_id},
                )

        if not _is_authorized(request):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Provide a valid X-API-Key or call through the configured RapidAPI proxy.",
                    "request_id": request_id,
                },
                headers={
                    "WWW-Authenticate": "ApiKey",
                    "X-Request-ID": request_id,
                },
            )

    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response
