from __future__ import annotations

import os
import secrets
import time
import uuid

from fastapi import Depends, FastAPI, Header, Request, status
from fastapi.responses import JSONResponse

from .models import InvoiceRequest, PreflightResponse, ValidationResult, XmlValidationRequest
from .ubl import build_invoice_xml
from .validator import validate_xml


app = FastAPI(
    title="Croatia eInvoice Adapter API",
    version="0.2.0",
    description=(
        "Developer preview: structured JSON in, Croatian UBL invoice XML and "
        "deterministic preflight findings out. This service is not yet a certified "
        "production-compliance engine and must not be used as the sole basis for "
        "submitting live fiscal invoices."
    ),
    contact={"name": "API operator"},
    license_info={"name": "Proprietary developer preview"},
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class UnauthorizedRequest(Exception):
    pass


@app.exception_handler(UnauthorizedRequest)
async def unauthorized_handler(request: Request, exc: UnauthorizedRequest):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "unauthorized",
            "message": "Missing or invalid API access credential",
        },
        headers={"WWW-Authenticate": "ApiKey"},
    )


def require_api_access(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_rapidapi_proxy_secret: str | None = Header(
        default=None, alias="X-RapidAPI-Proxy-Secret"
    ),
) -> None:
    """Protect metered endpoints in production and marketplace deployments."""

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    direct_api_key = os.getenv("DIRECT_API_KEY") or os.getenv("API_KEY")
    rapidapi_proxy_secret = os.getenv("RAPIDAPI_PROXY_SECRET")
    allow_unauthenticated = _env_bool(
        "ALLOW_UNAUTHENTICATED", default=(app_env != "production")
    )

    if allow_unauthenticated and not direct_api_key and not rapidapi_proxy_secret:
        return

    direct_ok = bool(
        direct_api_key
        and x_api_key
        and secrets.compare_digest(x_api_key, direct_api_key)
    )
    rapid_ok = bool(
        rapidapi_proxy_secret
        and x_rapidapi_proxy_secret
        and secrets.compare_digest(x_rapidapi_proxy_secret, rapidapi_proxy_secret)
    )

    if not (direct_ok or rapid_ok):
        raise UnauthorizedRequest


@app.middleware("http")
async def request_guard_and_metadata(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()

    try:
        max_request_bytes = int(os.getenv("MAX_REQUEST_BYTES", "2097152"))
    except ValueError:
        max_request_bytes = 2_097_152

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            too_large = int(content_length) > max_request_bytes
        except ValueError:
            too_large = False
        if too_large:
            response = JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={
                    "error": "request_too_large",
                    "message": f"Request exceeds the {max_request_bytes}-byte limit",
                },
            )
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
def root() -> dict[str, object]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "developer-preview",
        "production_ready": False,
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "environment": os.getenv("APP_ENV", "development"),
        "production_ready": False,
    }


@app.get("/v1/info", dependencies=[Depends(require_api_access)])
def info() -> dict[str, object]:
    return {
        "country": "HR",
        "document": "UBL 2.1 Invoice",
        "mode": "developer-preview",
        "production_ready": False,
        "warning": (
            "Selected deterministic preflight checks only. Full UBL XSD, EN 16931, "
            "and current Croatian Schematron validation are not yet integrated."
        ),
    }


@app.post(
    "/v1/hr/invoices/generate",
    response_model=PreflightResponse,
    dependencies=[Depends(require_api_access)],
)
def generate_invoice(request: InvoiceRequest) -> PreflightResponse:
    xml, totals = build_invoice_xml(request)
    validation = validate_xml(xml)
    return PreflightResponse(xml=xml, validation=validation, totals=totals)


@app.post(
    "/v1/hr/invoices/validate",
    response_model=ValidationResult,
    dependencies=[Depends(require_api_access)],
)
def validate_invoice(request: XmlValidationRequest) -> ValidationResult:
    return validate_xml(request.xml)


@app.post(
    "/v1/hr/invoices/preflight",
    response_model=PreflightResponse,
    dependencies=[Depends(require_api_access)],
)
def preflight_invoice(request: InvoiceRequest) -> PreflightResponse:
    xml, totals = build_invoice_xml(request)
    validation = validate_xml(xml)
    return PreflightResponse(xml=xml, validation=validation, totals=totals)
