import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import is_valid_iban, is_valid_oib


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def payload() -> dict:
    return json.loads((ROOT / "examples" / "invoice.json").read_text())


def test_check_digits() -> None:
    assert is_valid_oib("11111111119")
    assert is_valid_oib("12345678903")
    assert not is_valid_oib("12345678901")
    assert is_valid_iban("HR1210010051863000160")


def test_generate_and_validate() -> None:
    response = client.post("/v1/hr/invoices/generate", json=payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["validation"]["valid"] is True, data["validation"]
    assert data["totals"] == {
        "net_total": "100.00",
        "tax_total": "25.00",
        "gross_total": "125.00",
        "payable_total": "125.00",
    }
    assert "<cbc:CustomizationID>" in data["xml"]


def test_bad_oib_rejected_before_generation() -> None:
    body = payload()
    body["supplier"]["oib"] = "12345678901"
    response = client.post("/v1/hr/invoices/generate", json=body)
    assert response.status_code == 422


def test_invalid_xml_returns_findings() -> None:
    response = client.post(
        "/v1/hr/invoices/validate",
        json={"xml": "<Invoice><cbc:ID>bad id</cbc:ID></Invoice>"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["findings"]) >= 1


def test_tampered_total_is_detected() -> None:
    generated = client.post("/v1/hr/invoices/generate", json=payload()).json()
    tampered = generated["xml"].replace(
        '<cbc:PayableAmount currencyID="EUR">125.00</cbc:PayableAmount>',
        '<cbc:PayableAmount currencyID="EUR">124.00</cbc:PayableAmount>',
    )
    response = client.post("/v1/hr/invoices/validate", json={"xml": tampered})
    data = response.json()
    assert data["valid"] is False
    assert any(f["rule_id"] == "CALC-TOTAL-4" for f in data["findings"])


def test_doctype_is_rejected() -> None:
    xml = '<!DOCTYPE Invoice [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Invoice>&xxe;</Invoice>'
    response = client.post("/v1/hr/invoices/validate", json={"xml": xml})
    data = response.json()
    assert data["valid"] is False
    assert data["findings"][0]["rule_id"] == "SEC-XML-1"


def test_multiple_tax_rates() -> None:
    body = payload()
    body["lines"].append(
        {
            "description": "Reduced-rate item",
            "quantity": "2",
            "unit_price": "10.00",
            "unit_code": "H87",
            "vat_rate": 13,
            "kpd_code": "58.29.50",
        }
    )
    response = client.post("/v1/hr/invoices/preflight", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["validation"]["valid"] is True, data["validation"]
    assert data["totals"] == {
        "net_total": "120.00",
        "tax_total": "27.60",
        "gross_total": "147.60",
        "payable_total": "147.60",
    }


def test_production_mode_rejects_missing_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "false")
    monkeypatch.setenv("DIRECT_API_KEY", "test-secret")
    monkeypatch.delenv("RAPIDAPI_PROXY_SECRET", raising=False)

    response = client.post("/v1/hr/invoices/preflight", json=payload())
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_production_mode_accepts_direct_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "false")
    monkeypatch.setenv("DIRECT_API_KEY", "test-secret")
    monkeypatch.delenv("RAPIDAPI_PROXY_SECRET", raising=False)

    response = client.post(
        "/v1/hr/invoices/preflight",
        json=payload(),
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_production_mode_accepts_rapidapi_proxy_secret(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "false")
    monkeypatch.delenv("DIRECT_API_KEY", raising=False)
    monkeypatch.setenv("RAPIDAPI_PROXY_SECRET", "rapid-secret")

    response = client.post(
        "/v1/hr/invoices/preflight",
        json=payload(),
        headers={"X-RapidAPI-Proxy-Secret": "rapid-secret"},
    )
    assert response.status_code == 200


def test_request_size_limit(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "false")
    monkeypatch.setenv("DIRECT_API_KEY", "test-secret")
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1024")

    response = client.post(
        "/v1/hr/invoices/validate",
        content=b"x" * 1025,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": "test-secret",
        },
    )
    assert response.status_code == 413
    assert response.json()["error"] == "request_too_large"
