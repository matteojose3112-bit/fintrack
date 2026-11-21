# Foundation 0.5 — Global Data Provider Adapter Framework

**Status:** Provider-neutral contracts and PostgreSQL ingestion service implemented; no live provider adapter or credentials are included.

## Objective

No single vendor covers every global asset class, exchange, jurisdiction, historical depth, and data right. Aurelius therefore uses explicit provider adapters rather than binding core domain models to one vendor.

Provider categories may include:
- security/reference data;
- equity, ETF, bond, fund and corporate-action data;
- futures/options/commodity prices and contract specifications;
- FX and rates;
- crypto spot, derivatives, on-chain and token metadata;
- macroeconomic/statistical series;
- prediction/event-market observations;
- alternative asset valuations and private-market reference data.

Provider coverage is capability-specific. A provider that covers US equities does not imply global equity, futures, FX, crypto, or real-time coverage.

## Adapter contract

Every adapter declares:
- stable provider key and terms version;
- supported observation/data types;
- supported asset classes and instrument types;
- explicit region codes and MIC venue coverage, or an explicit global coverage declaration;
- historical/intraday/real-time support and delay class;
- rights scope and provider licensing metadata.

Every request declares instrument IDs, observation types, aware time range, asset/instrument class, region, venue, and granularity.

Every returned observation requires:
- source record ID for deduplication;
- stable instrument ID and observation type;
- exact Decimal value (never binary float);
- unit and/or quote currency where relevant;
- timezone-aware observed_at and retrieved_at;
- market session and methodology where available.

## Licensing and data rights

Provider access is not equivalent to a right to store, display, redistribute, or use data for model training. Every provider source is versioned by terms version and records rights scope, geographic coverage, license name/URL, and provider identity.

The ingestion service requires:
- active provider source;
- exact provider key and terms version match;
- purpose explicitly allowed by the license policy;
- region explicitly allowed, or documented global coverage;
- adapter capability coverage for requested data, asset class, instrument, region, and venue.

No automatic redistribution or training use is assumed. Provider terms must be reviewed before adding a live adapter.

## Ingestion behavior

1. Validate provider capabilities and license policy before calling the adapter.
2. Fetch outside the database transaction; do not hold database locks during network I/O.
3. Validate every returned instrument/type/time range and exact value.
4. Revalidate provider source/terms inside the persistence transaction.
5. Resolve unit and quote-currency references.
6. Insert immutable observations with source, terms version, observed/retrieved times, session, and methodology.
7. Deduplicate by provider source + source record ID + observation type + instrument ID using a unique index and PostgreSQL ON CONFLICT DO NOTHING.
8. Commit the batch atomically; a duplicate replay inserts zero rows.

Provider rate limiting, backoff, circuit breakers, API secrets, raw payload retention, and live network adapters remain provider-specific implementation work.

## Security and boundaries

- API keys/secrets belong in environment/secret management, never in provider metadata or logs.
- No provider is selected implicitly based on cheapest price.
- No data is assumed globally licensed.
- Provider coverage does not establish user eligibility to trade.
- Ingestion is PostgreSQL-only and is not yet exposed as a public API endpoint.
- No live network provider, subscription, or production source has been configured.

## Tests

Fake adapters validate capability matching, explicit global/regional coverage, exact Decimal observations, license-purpose rejection before network fetch, source/terms matching, and idempotent PostgreSQL insertion. Tests do not call external providers.

## Implementation status

Implemented in backend/app/domain/providers.py and backend/app/persistence/market_data_ingestion.py. Alembic revision 0004 adds the provider-observation deduplication index. Fake-provider PostgreSQL integration tests verify exact Decimal ingestion, license/purpose/region checks, provider source/terms identity, and duplicate replay. Latest CI: 34 PostgreSQL integration tests and 134 backend tests passed. No live provider has been connected.
