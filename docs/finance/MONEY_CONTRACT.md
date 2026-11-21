# Aurelius Money and Currency Contract

**Status:** Initial implementation contract — 2026-11-17  
**Scope:** Domain-level foundation only. This contract does not migrate the existing database or change current API payloads.

## 1. Canonical representation

- Monetary values are exact decimal quantities, represented in Python by `decimal.Decimal`.
- Public API and import boundaries must accept and emit decimal strings (for example, `"1250.40"`), never JSON binary floating-point numbers as the source of financial truth.
- Persisted amounts must use fixed-precision decimal database types sized from documented product limits. Currency is stored explicitly beside every amount.
- Integer minor units are suitable for bounded calculations and interchange only when paired with an explicit currency code and exponent.
- Binary floats are prohibited in financial domain calculations, persistence contracts, and serialized monetary values.

## 2. Currency scale

Currency scale is a property of the currency or monetary unit, not a universal two-decimal assumption. The current registry is generated from the versioned SIX ISO 4217 List One and List Three sources. The bundled current release has 178 codes, including 165 with a published minor-unit exponent. Supported precision includes zero, two, three, and four decimal places (for example JPY, USD, KWD, and CLF).

Unknown codes and codes without a published exponent fail closed; do not silently assume two decimals. Registry updates require reviewed source snapshots and regression tests. Historical List Three entries are retained, but their exponent is not inferred when the source does not publish it.

## 2.1 Versioned ISO 4217 reference data

The domain now bundles SIX's ISO 4217 List One (current currencies and funds) and List Three (historical denominations) as a versioned snapshot. The current bundled release contains 178 current codes, of which 165 publish a minor-unit exponent. The historical bundle preserves 152 code/withdrawal-date records across 137 distinct codes; the same code may have different withdrawal dates in different jurisdictions.

The snapshot updater at backend/scripts/update_iso4217_snapshot.py downloads the official SIX XML lists and regenerates the JSON data file. This is a maintainer action; the application does not fetch currency definitions at runtime. The official source and release dates are stored with the snapshot.

Money uses the current registry instead of a hard-coded allowlist. It accepts current List One entries with a published minor-unit exponent, including fund-flagged monetary/accounting units. That is an arithmetic capability, **not** permission to use every code as a cash account denomination. Future account creation must distinguish spendable cash currencies from fund codes, index units, precious-metal reference codes, and other special-purpose units.

List Three does not publish minor-unit exponents. Aurelius preserves historical codes, names, numeric codes, country associations, and jurisdiction-specific withdrawal dates, but does not infer historical precision from a replacement currency. Exact historical monetary interpretation requires an appropriate historical List One snapshot or separately verified source.

## 3. Rounding

- The initial domain primitive uses decimal `ROUND_HALF_UP` when normalizing an amount to its currency scale.
- Intermediate calculations retain Decimal precision and are not rounded after every operation.
- Round only at defined monetary boundaries (currency minor-unit posting, display, settlement, or an explicitly specified conversion).
- Any future tax, interest, fee, allocation, or FX rule must declare its own legally/business-appropriate rounding boundary and tests. This default is a technical baseline, not a universal tax or banking rule.

## 4. Arithmetic and FX

- Addition and subtraction require identical currency codes.
- Cross-currency arithmetic is rejected.
- FX conversion must be an explicit application/domain operation using a rate with base currency, quote currency, observed/effective timestamp, source, retrieval timestamp, and conversion direction.
- A converted amount must retain the original amount/currency and the rate evidence used. Never overwrite native-currency truth with a reporting-currency estimate.

## 5. Input validation

- Accept Decimal values internally and decimal strings at external boundaries.
- Reject floats, booleans, NaN, positive/negative infinity, malformed strings, and unsupported currencies.
- Normalize currency codes to uppercase and validate a three-letter code.
- Negative amounts are permitted at the primitive level for reversals, corrections, and signed balances; individual use cases impose their own direction/positivity rules.

## 6. API migration policy

The existing FinTrack API currently exposes numeric JSON values and the existing database model uses floating-point columns on `main`. The new `Money` primitive does not silently change those contracts.

Before any endpoint migration:
1. Review the separate fixed-precision integration work (PR #12 and its source PRs).
2. Define versioned request/response schemas with decimal strings and explicit currency.
3. Add compatibility tests and a deliberate frontend decimal-string strategy; do not rely on JavaScript `Number` for exact financial arithmetic.
4. Design a reversible/verified database migration, backup, restore, and reconciliation plan.
5. Obtain explicit approval before production migration or deployment.

## 7. Initial implementation

backend/app/domain/money.py provides an immutable Money value object backed by backend/app/domain/currency.py and the bundled SIX ISO 4217 snapshot. It supports registry-backed scale normalization, fixed-scale serialization, exact integer-minor-unit construction/conversion, canonical zero, and same-currency arithmetic. Tests cover current/historical registry facts, country-specific withdrawal dates, importer parsing, 0/2/3/4-decimal precision, float rejection, invalid values, and cross-currency arithmetic.

## 8. Non-goals

This contract does not yet implement FX feeds, account balances, ledger posting, investment lots, market prices, tax calculations, or portfolio valuation. It does not constitute accounting, tax, or legal advice.
