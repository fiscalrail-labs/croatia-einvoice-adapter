# RapidAPI listing draft — v0.3.0

## Name
Croatia eInvoice JSON-to-UBL & Preflight API

## One-line description
Convert ordinary invoice JSON to Croatian UBL 2.1 and validate it against the official UBL schema, EN 16931 rules, and Croatian CIUS/EXT rules.

## Intended buyer
ERP, accounting, billing, marketplace, and vertical-SaaS developers that need a computer-to-computer Croatian eInvoice component.

## Commercial status gate
Enable paid plans only after the deployed service returns:

```json
{"production_ready": true}
```

from `GET /ready`, and the GitHub `Production engine CI` workflow passes. The API is a generation and preflight component; it is not an information intermediary and does not transmit or fiscalize invoices.

## Endpoints

- `GET /v1/info`
- `POST /v1/hr/invoices/generate`
- `POST /v1/hr/invoices/preflight`
- `POST /v1/hr/invoices/validate`

## Initial pricing experiment

| Plan | Price (USD) | Requests per month | Overage |
|---|---:|---:|---:|
| Development | Free | 100 | Blocked |
| Builder | $19 | 5,000 | $0.004/request |
| Growth | $79 | 50,000 | $0.002/request |
| Scale | $249 | 250,000 | $0.001/request |

## Marketplace copy

**What it does**

- Accepts structured invoice JSON.
- Generates Croatian UBL 2.1 XML.
- Runs official UBL XSD validation.
- Runs EN 16931 business rules.
- Runs Croatian CIUS/EXT Fiscalization 2.0 rules.
- Returns normalized JSON errors with rule IDs, severity, XPath, source profile, and repair hints.

**What it does not do**

- Send invoices to recipients.
- Act as a certified information intermediary.
- Submit fiscalization messages.
- Replace tax or legal advice.

## Search terms
Croatia eInvoice, Fiskalizacija 2.0, Croatian UBL, EN 16931, invoice XML, ERP integration, invoice validator, OIB, KPD 2025

## Backend protection
Set `RAPIDAPI_PROXY_SECRET` in Render to the unique value RapidAPI uses for `X-RapidAPI-Proxy-Secret`. Keep the direct `API_KEY` private for owner testing.
