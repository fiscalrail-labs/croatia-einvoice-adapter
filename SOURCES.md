# Technical source trail

## Croatian Tax Administration (authoritative source)

The Docker build retrieves the official Croatian UBL 2.1 schema archive directly from the Croatian Tax Administration:

- eInvoice technical documentation index:
  https://porezna.gov.hr/fiskalizacija/bezgotovinski-racuni/tehnicka-specifikacija
- Official UBL 2.1 eInvoice schema archive (document 198, published 2026-04-15):
  https://porezna.gov.hr/fiskalizacija/api/dokumenti/198
- Current Croatian eInvoice validator archive (document 197):
  https://porezna.gov.hr/fiskalizacija/api/dokumenti/197
- Official example documents (document 158):
  https://porezna.gov.hr/fiskalizacija/api/dokumenti/158
- Validator announcement and Croatian CustomizationID guidance:
  https://porezna.gov.hr/fiskalizacija/bezgotovinski-racuni/bezgotovinski-racuni-novosti/o/validator-eracuna

The official artifacts and published Croatian rules are authoritative. FiscalRail's normalized JSON output is a convenience layer and does not replace the official specification.

## Validation and generation engine

- Verifaktura project:
  https://github.com/verifaktura/verifaktura
- Packages pinned by this release:
  - `verifaktura` 0.1.8
  - `@verifaktura/cius-hr` 0.1.8
  - `@verifaktura/build` 0.1.8

Verifaktura code is Apache-2.0. Validation artifacts bundled or downloaded by its published packages retain the licenses of their original sources. See `NOTICE.md` and the installed packages' notices in the built image.
