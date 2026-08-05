# Third-party notices

FiscalRail Labs' application code in this package is provided for deployment of the Croatia eInvoice Adapter API.

This release uses the following third-party components:

1. **Verifaktura**
   - Source: https://github.com/verifaktura/verifaktura
   - License: Apache License 2.0
   - Used for EN 16931 validation, Croatian CIUS/EXT validation, and UBL generation.

2. **Croatian Tax Administration technical artifacts**
   - Source index: https://porezna.gov.hr/fiskalizacija/bezgotovinski-racuni/tehnicka-specifikacija
   - The Docker build downloads the official UBL schema archive from document endpoint 198.
   - These artifacts remain subject to the terms and notices of their publisher.

3. **OASIS UBL 2.1 schemas**
   - Used through the official Croatian schema distribution.
   - The schemas retain their original notices and terms.

Do not remove third-party copyright, attribution, or license files from installed packages or downloaded official artifacts.
