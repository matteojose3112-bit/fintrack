# ADR-0001: Deterministic Financial Core and Domain Boundaries

- **Status:** Accepted as the initial implementation direction
- **Date:** 2026-11-17
- **Decision owners:** Aurelius project maintainers

## Context

The inherited FinTrack MVP combines route handlers, persistence models, serialization, and financial calculations in a small FastAPI application. Its transaction, budget, and goal amounts currently use SQLAlchemy `Float` and Pydantic `float`. This is adequate only as a small prototype and is not a safe foundation for multi-currency accounting, investment analysis, or AI-supported financial decisions.

Aurelius must be able to explain where a number came from, reproduce deterministic calculations, preserve native-currency facts, and prevent an AI component from becoming an authority over financial records.

## Decision

1. **Modular monolith first.** Keep one deployable backend while separating domain rules, application use cases, providers, API transport, and intelligence interfaces.
2. **Domain independence.** Core value objects and calculations must not import FastAPI, SQLAlchemy, external APIs, model SDKs, or frontend code.
3. **Exact money.** Use Decimal internally, explicit currency codes/scales, decimal-string API representation, and reviewed rounding boundaries. Reject binary floats in the financial domain.
4. **Evidence-bearing external data.** Provider observations must preserve provider/source, instrument or series identifier, observation time/period, retrieval time, units/currency, freshness/delay status, and transformation metadata.
5. **Append-only decision evidence.** Financial events, corrections, reconciliations, model predictions, and decision records should preserve history rather than silently overwrite material facts.
6. **Application-owned permissions.** Application services enforce account ownership, validate commands, perform deterministic calculations, and record audit events.
7. **AI as read-only decision support.** Specialist agents receive bounded, typed, read-only tools and evidence packages. They cannot directly mutate financial records, write to the database, move money, or execute brokerage orders.
8. **Independent review.** Significant AI-generated research or decision support should be challenged by an independent reviewer with access to source evidence and explicit uncertainty.
9. **No premature infrastructure.** Do not add microservices, a heavyweight agent framework, vector database, or paid provider until a measured requirement justifies it.

## Initial module boundaries

| Module | Responsibility |
| --- | --- |
| `domain` | Money, currencies, accounts, ledger, portfolio, risk, thesis, decisions, predictions |
| `application` | Validated use cases, permissions, orchestration, transactions |
| `providers` | External market, filings, macro, FX, and news adapters |
| `intelligence` | Typed specialist contracts, evidence assembly, independent review |
| `api` | Versioned HTTP schemas and transport only |
| `jobs` | Later scheduled ingestion and reporting |

The first implemented domain primitive is `backend/app/domain/money.py`. Other modules are design targets, not claims of existing functionality.

## Consequences

### Positive
- Financial calculations can be unit-tested without a database, web server, model, or network.
- Provider changes do not require changes to financial domain rules.
- Evidence and audit requirements are explicit before adding AI.
- Existing MVP workflows can be migrated incrementally without claiming the old schema is already accounting-grade.

### Trade-offs
- Decimal-string APIs require frontend changes and deliberate formatting.
- Currency metadata and rounding rules require explicit maintenance.
- Append-only records and provenance add schema and storage complexity.
- A modular monolith requires disciplined boundaries and import rules.

## Rejected alternatives

- **AI-first implementation:** rejected because agents built on float-based and incomplete financial records would create confident but unreliable output.
- **Immediate microservices:** rejected because current scale and team size do not justify distributed operational complexity.
- **Universal two-decimal currency assumption:** rejected because currencies have different minor-unit exponents.
- **Implicit FX conversion:** rejected because it obscures rate source, timestamp, and conversion assumptions.
- **Direct agent database access or brokerage execution:** rejected on safety and auditability grounds.

## Follow-up decisions

- Specify account and ledger invariants before adding persistence tables.
- Design an event/correction/reversal model and reconciliation lifecycle.
- Select a versioned decimal-string API contract and frontend exact-arithmetic strategy.
- Define provenance and audit-event schemas before connecting providers or AI.
- Add property-based and accounting golden-case tests as domain use cases expand.
