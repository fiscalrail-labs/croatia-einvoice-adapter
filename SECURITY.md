# Security notes

This repository is a development preview, not a certified invoicing service.

- Do not submit real invoices or personal data to an untrusted deployment.
- Production deployments must set `APP_ENV=production` and configure at least one of:
  - `DIRECT_API_KEY`
  - `RAPIDAPI_PROXY_SECRET`
- `/v1/` endpoints reject unauthenticated traffic when `ALLOW_UNAUTHENTICATED=false`.
- Request and response bodies are not intentionally logged by the application.
- The service rejects entity declarations and DTDs and uses an XML parser with network and entity resolution disabled.
- Rotate any credential exposed in logs, screenshots, or chat.
- Before commercial launch, add centralized secret management, dependency scanning, vulnerability response, structured privacy controls, abuse detection, and an independent review.
