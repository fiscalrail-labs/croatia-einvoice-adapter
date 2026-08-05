from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .models import InvoiceRequest, PreflightResponse, ValidationResult, XmlValidationRequest
from .official_engine import OfficialEngine, OfficialEngineError
from .security import access_and_safety_middleware
from .ubl import calculate_totals, decimal_text
from .validator import validate_xml as legacy_validate_xml
from .xsd_validator import UblXsdValidator


engine = OfficialEngine()
xsd = UblXsdValidator()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    xsd.load()
    await engine.start()
    app.state.engine = engine
    app.state.xsd = xsd
    yield
    await engine.stop()


app = FastAPI(
    title="Croatia eInvoice Adapter API",
    version="0.3.0",
    description=(
        "JSON-to-UBL generation and preflight validation using the official UBL 2.1 "
        "schema, EN 16931 rules, and Croatian CIUS/EXT rules. Readiness is exposed "
        "at /ready; paid production traffic must be blocked unless all engines are ready."
    ),
    contact={"name": "FiscalRail Labs"},
    license_info={"name": "Proprietary API; third-party validation artefacts retain source licences"},
    lifespan=lifespan,
)
app.middleware("http")(access_and_safety_middleware)


def _ready() -> bool:
    return engine.status.ready and xsd.status.ready


def _totals(request: InvoiceRequest) -> dict[str, str]:
    values = calculate_totals(request)
    return {
        key: decimal_text(value)
        for key, value in values.items()
        if key in {"net_total", "tax_total", "gross_total", "payable_total"}
    }


def _legacy_result(xml: str) -> ValidationResult:
    legacy = legacy_validate_xml(xml)
    return ValidationResult(
        valid=legacy.valid,
        profile=legacy.profile,
        profiles=[{"id": "legacy-preview", "version": "0.2.0", "source": "FiscalRail"}],
        findings=[
            {
                "rule_id": f.rule_id,
                "severity": "fatal" if f.severity in {"fatal", "error"} else f.severity,
                "profile": "legacy-preview",
                "business_terms": [],
                "path": f.path,
                "message": f.message,
            }
            for f in legacy.findings
        ],
        checks_run=legacy.checks_run,
        production_ready=False,
        engine="fiscalrail-legacy/0.2.0",
        summary={"fatal": len(legacy.findings) if not legacy.valid else 0},
    )


def _combine_report(xml: str, report: dict[str, Any]) -> ValidationResult:
    xsd_findings = xsd.validate(xml)
    schematron_findings = []
    for issue in report.get("issues", []):
        location = issue.get("location") or {}
        schematron_findings.append(
            {
                "rule_id": issue.get("ruleId", "UNKNOWN"),
                "severity": issue.get("severity", "fatal"),
                "profile": issue.get("profile", "unknown"),
                "business_terms": issue.get("businessTerms", []),
                "path": location.get("xpath", "/"),
                "line": location.get("line"),
                "column": location.get("column"),
                "message": issue.get("message", "Validation failed"),
                "hint": issue.get("hint"),
            }
        )
    findings = [*xsd_findings, *schematron_findings]
    fatal = sum(1 for item in findings if item["severity"] in {"fatal", "error"})
    source_summary = report.get("summary", {})
    return ValidationResult(
        valid=fatal == 0 and bool(report.get("valid")),
        profile="hr",
        profiles=[
            {"id": "ubl-xsd", "version": "2.1", "source": "Croatian Tax Administration / OASIS"},
            *report.get("profiles", []),
        ],
        findings=findings,
        checks_run=[
            "official Croatian UBL 2.1 XSD",
            "EN 16931 Schematron",
            "Croatian CIUS/EXT Schematron",
        ],
        production_ready=_ready(),
        engine=report.get("engine", "verifaktura/unknown"),
        summary={
            "fatal": fatal,
            "warning": sum(1 for item in findings if item["severity"] == "warning"),
            "info": sum(1 for item in findings if item["severity"] == "info"),
            "rules_fired": source_summary.get("rulesFired"),
            "schematron_duration_ms": source_summary.get("durationMs"),
        },
    )


async def _official_validate(xml: str, language: str = "en", max_issues: int = 200) -> ValidationResult:
    if not _ready():
        if _bool("ALLOW_LEGACY_FALLBACK", os.getenv("APP_ENV", "development") != "production" or "PYTEST_CURRENT_TEST" in os.environ):
            return _legacy_result(xml)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "validation_engine_not_ready",
                "official_engine": engine.status.detail,
                "xsd_engine": xsd.status.detail,
            },
        )
    try:
        report = await engine.request("validate", xml=xml, lang=language, maxIssues=max_issues)
        return _combine_report(xml, report)
    except (OfficialEngineError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail={"error": "validation_failed", "message": str(exc)}) from exc


@app.exception_handler(OfficialEngineError)
async def official_engine_handler(request: Request, exc: OfficialEngineError):
    return JSONResponse(status_code=503, content={"error": "official_engine_error", "message": str(exc)})


@app.get("/", include_in_schema=False)
def root() -> dict[str, object]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ready" if _ready() else "starting-or-degraded",
        "production_ready": _ready(),
        "documentation": "/docs",
        "health": "/health",
        "readiness": "/ready",
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "version": app.version, "environment": os.getenv("APP_ENV", "development")}


@app.get("/ready")
def readiness() -> JSONResponse:
    ready = _ready()
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready": ready,
            "production_ready": ready,
            "official_engine": {
                "ready": engine.status.ready,
                "detail": engine.status.detail,
                "metadata": engine.status.metadata,
            },
            "ubl_xsd": {
                "ready": xsd.status.ready,
                "detail": xsd.status.detail,
                "schema_path": xsd.status.schema_path,
                "source_sha256": xsd.status.source_sha256,
            },
        },
    )


@app.get("/v1/info")
def info() -> dict[str, object]:
    return {
        "country": "HR",
        "document": "UBL 2.1 Invoice",
        "mode": "official-validation" if _ready() else "degraded",
        "production_ready": _ready(),
        "validation_layers": ["UBL 2.1 XSD", "EN 16931", "HR CIUS/EXT"],
        "engine": engine.status.metadata,
    }


@app.post("/v1/hr/invoices/generate", response_model=PreflightResponse)
async def generate_invoice(request: InvoiceRequest) -> PreflightResponse:
    if not engine.status.ready:
        if _bool("ALLOW_LEGACY_FALLBACK", os.getenv("APP_ENV", "development") != "production" or "PYTEST_CURRENT_TEST" in os.environ):
            from .ubl import build_invoice_xml
            xml, totals = build_invoice_xml(request)
            return PreflightResponse(xml=xml, validation=_legacy_result(xml), totals=totals)
        raise HTTPException(status_code=503, detail="Official generation engine is not ready")
    result = await engine.request("generate", invoice=request.model_dump(mode="json"))
    xml = result["xml"]
    validation = await _official_validate(xml)
    return PreflightResponse(xml=xml, validation=validation, totals=_totals(request))


@app.post("/v1/hr/invoices/validate", response_model=ValidationResult)
async def validate_invoice(request: XmlValidationRequest) -> ValidationResult:
    return await _official_validate(request.xml, request.language, request.max_issues)


@app.post("/v1/hr/invoices/preflight", response_model=PreflightResponse)
async def preflight_invoice(request: InvoiceRequest) -> PreflightResponse:
    if not engine.status.ready:
        if _bool("ALLOW_LEGACY_FALLBACK", os.getenv("APP_ENV", "development") != "production" or "PYTEST_CURRENT_TEST" in os.environ):
            from .ubl import build_invoice_xml
            xml, totals = build_invoice_xml(request)
            return PreflightResponse(xml=xml, validation=_legacy_result(xml), totals=totals)
        raise HTTPException(status_code=503, detail="Official generation engine is not ready")
    result = await engine.request("preflight", invoice=request.model_dump(mode="json"), lang="en", maxIssues=200)
    xml = result["xml"]
    validation = _combine_report(xml, result["report"])
    return PreflightResponse(xml=xml, validation=validation, totals=_totals(request))
