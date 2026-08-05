# Croatia eInvoice Adapter API v0.3.0

A deterministic computer-to-computer API for Croatian eInvoice generation and preflight validation.

## Production validation stack

- Official Croatian UBL 2.1 XSD archive
- EN 16931 Schematron
- Croatian CIUS/EXT Schematron for Fiskalizacija 2.0
- OIB, IBAN, KPD, arithmetic and structured error reporting

The service reports `production_ready: true` only when every official engine is loaded. Check:

```text
GET /ready
```

## Endpoints

- `POST /v1/hr/invoices/preflight` — JSON in, UBL XML plus official validation report out
- `POST /v1/hr/invoices/generate` — generate UBL and validate it
- `POST /v1/hr/invoices/validate` — validate supplied UBL XML
- `GET /v1/info` — engine and profile metadata
- `GET /ready` — production readiness and official-artifact fingerprint

## Authentication

Send either:

```text
X-API-Key: <API_KEY or DIRECT_API_KEY>
```

or, when published behind RapidAPI:

```text
X-RapidAPI-Proxy-Secret: <RAPIDAPI_PROXY_SECRET>
```

## Local preview

Python-only tests use the legacy fallback because the official npm and XSD artifacts are installed during the Docker build:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Production test

```bash
docker build -t fiscalrail-croatia .
docker run --rm -p 8000:8000 -e API_KEY=test-secret fiscalrail-croatia
API_KEY=test-secret python scripts/production_smoke.py
```

See `PRODUCTION_UPGRADE.md`, `SECURITY.md`, and `MARKETPLACE_LISTING.md`.
