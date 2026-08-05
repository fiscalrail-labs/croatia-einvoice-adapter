# HR eInvoice Preflight Prototype

A working proof of the proposed computer-to-computer business model:

```text
structured invoice JSON
        -> API
        -> Croatian UBL 2.1 XML
        -> deterministic preflight findings
        -> machine-readable response
```

## What this proves

- An ERP or accounting system can call one endpoint instead of generating Croatian invoice XML itself.
- The same request produces the same result; there is no generative-AI judgment in the transaction path.
- Check-digit, structural, classification, date, and arithmetic failures are returned as JSON.
- The service can be metered per call by an API marketplace or a normal billing gateway.

## What this does **not** prove

This version is **not production-compliant** and must not be used to submit live invoices. It implements a deliberately limited preflight subset. Production requires, at minimum:

1. UBL 2.1 XSD validation.
2. The complete EN 16931 validation artifact.
3. The current Croatian CIUS/extension Schematron artifact.
4. Regression tests against the Croatian Tax Administration's official examples.
5. Version pinning, signed artifact provenance, rule-update monitoring, security review, and an uptime plan.

The API explicitly returns `production_ready: false` so nobody can mistake the prototype for a certified compliance result.

## Endpoints

- `GET /health`
- `POST /v1/hr/invoices/generate`
- `POST /v1/hr/invoices/preflight`
- `POST /v1/hr/invoices/validate`
- Interactive OpenAPI documentation: `/docs`

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Then:

```bash
curl -s http://127.0.0.1:8000/v1/hr/invoices/preflight \
  -H 'Content-Type: application/json' \
  --data-binary @examples/invoice.json
```

## Run tests

```bash
pytest -q
```

## Run with Docker

```bash
docker build -t hr-einvoice-preflight .
docker run --rm -p 8000:8000 hr-einvoice-preflight
```

## The commercial test

Do not yet market this as a Croatia validator. The official validator artifacts are public, and commercial platforms already provide validation. The more credible paid wedge is:

> JSON-to-Croatian-UBL generation, versioned official validation, normalized error JSON, automatic rule updates, and a stable API contract.

A marketplace listing should offer a free development tier and charge for production volume. The demand test is whether unrelated developers invoke the endpoint after seeing a public listing—without founder-led sales.

## Protected private preview

```bash
./scripts/start_private_preview.sh
```

The script generates a private `X-API-Key` and starts the service in production-style access-control mode. For a permanent host, use `render.yaml` and follow `DEPLOY_NOW.md`.

## Deployment-ready developer preview

Version 0.2 adds:

- optional direct API-key protection (`X-API-Key`),
- RapidAPI proxy-secret verification (`X-RapidAPI-Proxy-Secret`),
- request-size enforcement,
- request IDs and processing-time headers,
- Render Blueprint deployment configuration,
- CI tests, smoke testing, and marketplace listing copy.

For the shortest deployment path, follow `DEPLOY_NOW.md`.
