# v0.3.0 production-engine upgrade

This release replaces the hand-written preview rules on production deployments with three deterministic validation layers:

1. The Croatian Tax Administration's published UBL 2.1 XSD archive (document 198, published 2026-04-15).
2. EN 16931 Schematron rules through `verifaktura` 0.1.8.
3. Croatian CIUS/EXT Schematron rules through `@verifaktura/cius-hr` 0.1.8 (profile 2026-03-15).

The API does not report `production_ready: true` unless both the XSD engine and the official Schematron worker load successfully. `/ready` returns HTTP 503 when either layer is unavailable, and Render uses `/ready` as its health check.

## Supply-chain controls

- Exact npm package versions are pinned.
- The official Croatian XSD archive is downloaded from the Tax Administration during the Docker build.
- Its SHA-256 hash is recorded in the image and returned by `/ready`.
- The weekly GitHub Actions job rebuilds the image against current official artifacts and runs a complete JSON -> UBL -> XSD -> EN 16931 -> HR CIUS smoke test.
- Production disables the legacy fallback.

## Remaining commercial gate

A successful `/ready` response and CI smoke test establish technical readiness for the supported standard invoice scenario. They do not make FiscalRail an information intermediary, submit invoices, or provide legal/tax advice. The API generates and validates documents for transmission through a certified intermediary.
