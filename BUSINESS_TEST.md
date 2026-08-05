# Commercial test: Croatia eInvoice Adapter API

## Decision made

Do **not** sell a raw validator alone. Croatia publishes its own validator artifacts, and existing API vendors already sell broad UBL/EN 16931 validation. The sellable experiment is a narrower developer convenience layer:

> One stable JSON schema in; Croatian UBL 2.1 XML, deterministic preflight, normalized error JSON, and automatic rule-version maintenance out.

## Listing position

**Name:** Croatia eInvoice Adapter API

**One-line description:** Generate and preflight Croatian Fiscalization 2.0 UBL invoices from ordinary JSON.

**Buyer:** Developers maintaining ERP, billing, vertical SaaS, marketplace, or accounting integrations that need Croatian invoice output but do not want to maintain Croatian XML rules.

**Do not promise:** tax filing, invoice delivery, certified access-point service, legal compliance, or production acceptance until the complete official validation stack has been integrated and independently tested.

## Self-service pricing experiment

| Tier | Monthly price | Included calls |
|---|---:|---:|
| Development | $0 | 100 |
| Builder | $19 | 5,000 |
| Growth | $69 | 50,000 |
| Scale | $199 | 250,000 |

These are test prices, not validated prices.

## No-sales validation gate

Publish the API with a free tier and track only self-service behavior for 30 days.

Continue only when all of these occur:

1. At least 10 unrelated developer accounts make successful calls.
2. At least 3 accounts return on three or more different days.
3. At least 1 account exceeds the free quota or chooses a paid tier.
4. Support remains below 15 minutes per active account per month.
5. No result requires transaction-by-transaction human review.

Kill or substantially change the product when:

- Most usage is one-time curiosity.
- Nobody returns after testing.
- Users demand invoice delivery/fiscalization rather than generation and validation.
- Official rule maintenance consumes more revenue than the API produces.
- A broad e-invoice API adds complete Croatian support at commodity pricing.

## Production completion checklist

- [ ] Integrate UBL 2.1 XSD validation.
- [ ] Integrate complete EN 16931 validation.
- [ ] Integrate the current Croatian Schematron artifacts using an XSLT 2.0/3.0 engine.
- [ ] Pin artifact versions and record their hashes.
- [ ] Add official Croatian sample invoices as regression fixtures.
- [ ] Add credit notes, allowances, charges, exemptions, reverse charge, prepayments, and rounding cases.
- [ ] Add an automated official-artifact change detector.
- [ ] Add API keys, quotas, request logs, abuse limits, deletion policy, and uptime monitoring.
- [ ] Obtain independent technical review before describing results as production compliance validation.
