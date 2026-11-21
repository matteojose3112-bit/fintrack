# Foundation 0.6 — Portfolio Lot Persistence

**Status:** SQLAlchemy schema and Alembic revision implemented on a draft feature branch; PostgreSQL CI validation is pending.

## Scope

Persist the deterministic long-only trade/lot domain introduced in backend/app/domain/portfolio_lots.py. This slice stores imported or manually recorded executions and the resulting immutable acquisition/disposal facts. A trade execution is a record of a fill—not an order instruction.

## Tables

- investment_portfolios: owner-scoped portfolio container, independent of reporting currency.
- trade_executions: immutable BUY/SELL fill facts, exact quantity/price/fee, quote-currency registry reference, execution timestamp, source, cost-basis method, and request fingerprint.
- portfolio_lots: immutable acquisition lot opened by a BUY execution.
- lot_disposal_allocations: immutable allocation of a SELL execution across one or more acquisition lots, including cost basis, gross/net proceeds, allocated fee, and realized gain/loss.
- portfolio_position_locks: mutable serialization rows used by the future posting service. They are operational coordination state, not financial history.

## Financial and ownership invariants

1. Quantities, unit prices, fees, costs, and proceeds use unscaled exact PostgreSQL NUMERIC; binary floats are not accepted by the domain.
2. A lot's remaining quantity and remaining cost are derived from its original acquisition values less immutable disposal allocations. No mutable balance is stored on a lot.
3. Trade executions, acquisition lots, and disposal allocations are append-only in PostgreSQL. Corrections must be represented by explicit compensating/rebuild events in a later workflow, never by editing history.
4. Composite foreign keys bind each execution, lot, and disposal to the same owner, portfolio, brokerage account, instrument, and quote-currency definition.
5. Brokerage account owner scope is enforced by a composite (account_id, owner_id) reference. Account deletion remains restricted by existing financial-history policy.
6. Quote currency references the versioned ISO registry. Quantity precision is instrument/unit-specific and is not inferred from fiat currency precision.
7. A position lock is scoped by owner + portfolio + account + instrument + quote currency. The future service must acquire it before checking available quantity and writing executions/allocations.

## Explicit non-goals

- No broker order placement, order routing, account connection, or real-money trading.
- No tax-lot jurisdiction rules, tax reporting, wash-sale logic, or claim that FIFO/LIFO/specific selection is legally valid in every jurisdiction.
- No short positions, options exercise/assignment, futures variation margin, corporate-action transformations, dividends, or return-of-capital processing in this first long-only slice.
- No automatic conversion between quote currencies and portfolio reporting currency.
- No coupling to cash-ledger journals yet. A later application service must define and test the atomic relationship between trade fills and cash/fee postings before API exposure.
- No user-facing portfolio API in this schema PR.

## Migration and tests

Alembic revision 0005_portfolio_lots follows 0004_obs_idempotency. It creates the portfolio/execution/lot/allocation/lock tables, adds the composite account-owner uniqueness needed for safe references, and installs PostgreSQL append-only triggers plus finite/range checks for numeric values.

PostgreSQL 16 tests cover exact unscaled decimal persistence, cross-owner account rejection, immutable lot/allocation rows, same-scope disposal references, and mutable lock rows. The CI workflow now includes this test module; the run result must be checked before claiming validation.

## Next implementation gates

1. Implement a PostgreSQL-only application service that serializes each position, replays the deterministic domain book, claims execution IDs idempotently, and writes execution + lot/allocation + audit records atomically.
2. Test independent-connection oversell races, duplicate execution races, failed-transaction rollback, and specific-lot isolation.
3. Define late-arriving/backdated fill policy and deterministic rebuild/correction semantics before accepting out-of-order broker imports.
4. Design atomic cash-ledger integration, including settlement currency, FX legs, commissions, taxes/withholding, and fees.
5. Add owner-scoped read APIs only after the persistence service and concurrency suite pass.
