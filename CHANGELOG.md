# Changelog

## 0.3.0 - 2026-08-05

- Added official Croatian UBL 2.1 XSD validation sourced from the Tax Administration.
- Added persistent Node validation worker using EN 16931 and Croatian CIUS/EXT Schematron artefacts.
- Replaced production XML generation with `@verifaktura/build`.
- Added dynamic `/ready` health gate and official artefact SHA-256 reporting.
- Disabled hand-written legacy validation in production.
- Added weekly Docker integration testing against current official artefacts.
- Preserved direct API-key and RapidAPI proxy-secret authentication.

## 0.2.0 - 2026-08-05

- Hardened developer-preview deployment with API authentication and request limits.
