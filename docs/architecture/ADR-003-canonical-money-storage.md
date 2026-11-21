# ADR-003 — Canonical Monetary Persistence

- **Status:** Proposed; PostgreSQL implementation now being validated in Foundation 0.3
- **Date:** 2026-11-17
- **Decision:** Store monetary quantities as exact PostgreSQL NUMERIC values with database-enforced integrality and a hard 38-digit magnitude bound. The application represents authoritative posting magnitudes as Python integers.

## Context

Aurelius supports currencies and monetary units with zero, two, three, and four fractional decimal places. A universal two-decimal column is incorrect. PostgreSQL BIGINT is exact but limited to 19 decimal digits and can overflow long-lived aggregates. Binary floating point is unacceptable for authoritative money.

A subtle PostgreSQL behavior matters: declaring a column NUMERIC(38,0) coerces/rounds fractional input to scale zero before a CHECK constraint sees the stored value. That means a conventional CHECK cannot reliably reject every fractional input at that column boundary. We want the database to reject fractional minor-unit values, not silently round them.

## Decision

- Persist each journal posting's positive magnitude in an unconstrained-precision PostgreSQL NUMERIC column with a CHECK requiring:
  - amount_minor = trunc(amount_minor)
  - amount_minor > 0
  - amount_minor < 10^38
- This permits at most 38 integer digits while retaining exact numeric semantics and rejecting fractional values before they become authoritative ledger rows.
- The application domain accepts integer minor units only and enforces the same 38-digit bound before persistence. SQLAlchemy maps the column with Numeric(asdecimal=True), without a scale that would pre-round fractional input.
- SQLite's portable schema check enforces positivity; PostgreSQL migration adds the stricter integrality and upper-bound constraint. SQLite is not evidence of PostgreSQL behavior.
- Store an immutable currency-definition reference on each account and journal. The definition contains currency code, exponent (when published), registry list/release, and source provenance. Posting accounts must reference the same currency definition as their journal.
- The registry is versioned and append-only. Never silently change an existing currency's exponent. A new registry release creates new immutable definitions.
- API monetary inputs and outputs use canonical decimal strings plus currency or integer minor-unit strings plus currency. Never use JSON floating-point numbers for authoritative values.
- Convert between major-unit decimal strings and minor units using decimal/integer arithmetic only.

## Bounds and operational limits

The database permits positive integral magnitudes from 1 through 10^38 - 1. This is a hard persisted posting bound, not a target transaction size. Domain validation rejects values outside the range before SQL execution. Account balance queries use exact numeric aggregation; any derived result outside the documented bound is an integrity/operational error, never a wrapped value.

A future product-level limit should be substantially lower and configurable per owner/account, but must remain an explicit policy rather than an undocumented database assumption. This ADR does not set a business transaction cap.

## Trade-offs

- Unconstrained NUMERIC plus explicit CHECK is slightly more verbose than NUMERIC(38,0), but avoids PostgreSQL's pre-check scale rounding while retaining exact arithmetic and the intended 38-digit ceiling.
- The explicit currency-definition reference makes historical interpretation stable and auditable.
- The design does not perform FX conversion. A journal is single-currency; cross-currency transfers require separately balanced FX legs with explicit rates, fees, and gain/loss accounting.

## Consequences

- SQLAlchemy maps posting magnitude as Numeric(asdecimal=True) with no scale; PostgreSQL migration adds the exact integer/range CHECK.
- PostgreSQL integration tests are mandatory for fractional rejection, range boundaries, constraints, transaction isolation, and concurrency behavior.
- Legacy Numeric(14,2) fields remain isolated from the canonical ledger and require an explicit migration/adapter.
