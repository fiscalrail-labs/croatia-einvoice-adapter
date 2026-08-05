# RapidAPI listing draft

## Name
Croatia eInvoice Adapter API

## One-line description
Generate Croatian Fiscalization 2.0-style UBL invoice XML from ordinary JSON and receive normalized deterministic preflight errors.

## Intended buyer
ERP, accounting, billing, marketplace, and vertical-SaaS developers testing Croatian invoice output.

## Important status
This is a **developer preview**, not a certified production-compliance service. It does not yet include the complete UBL 2.1 XSD, EN 16931, and current Croatian Schematron validation stack. Do not market it as guaranteed legal, tax, delivery, or fiscalization compliance.

## Endpoints

- `GET /v1/info`
- `POST /v1/hr/invoices/generate`
- `POST /v1/hr/invoices/preflight`
- `POST /v1/hr/invoices/validate`

## Initial pricing experiment

| Plan | Price | Requests per month | Hard limit |
|---|---:|---:|---:|
| Development | Free | 100 | 100 |
| Builder | $19 | 5,000 | 5,000 |
| Growth | $69 | 50,000 | 50,000 |
| Scale | $199 | 250,000 | 250,000 |

Do not enable paid plans until the complete production validation stack is implemented. During the developer-preview test, publish only the free 100-call plan or label every paid tier as beta access with the limitations prominently disclosed.

## Search terms
Croatia eInvoice, Fiscalization 2.0, Croatian UBL, EN 16931, invoice XML, ERP integration, invoice validator, OIB validator, KPD code

## Backend protection
Set the deployment environment variable `RAPIDAPI_PROXY_SECRET` to the unique value RapidAPI displays for `X-RapidAPI-Proxy-Secret`. The backend rejects marketplace calls whose proxy secret does not match.
