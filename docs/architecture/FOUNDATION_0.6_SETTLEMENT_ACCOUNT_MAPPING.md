# Foundation 0.6 — Portfolio-to-Ledger Account Mapping

**Status:** Persistence schema implemented; no mapping API or settlement coordinator is exposed.

## Purpose

Trade executions already identify an owner-scoped brokerage account. Settlement must not use that account as both cash and investment holdings. This mapping makes the four ledger roles explicit for one portfolio, brokerage cash account, and immutable currency-definition snapshot.

## Mapping scope

PortfolioLedgerAccountMappingModel stores:

- owner_id and portfolio_id: the owning user and active investment portfolio.
- cash_account_id: the brokerage cash ASSET account; this must match the execution's existing account_id.
- investment_control_account_id: a separate ASSET account for the portfolio lot subledger.
- realized_gain_account_id: an INCOME account.
- realized_loss_account_id: an EXPENSE account.
- currency_definition_id: the exact currency-definition snapshot shared by all four accounts and the trade execution.

One mapping is allowed for each (portfolio_id, cash_account_id, currency_definition_id) scope. All four account IDs must be distinct. Mapping resolution is by identifiers and scope only; display names are never consulted.

## Database guarantees

Alembic revision 0006_settlement_account_mapping adds the table and:

- Composite foreign keys enforce portfolio ownership.
- Four composite foreign keys enforce that every ledger account belongs to the same owner and exact currency-definition snapshot.
- A unique constraint prevents duplicate mappings for one portfolio/cash-account/currency scope.
- A check constraint prevents one account from being assigned multiple roles.
- A PostgreSQL BEFORE INSERT OR UPDATE trigger requires an active portfolio and open accounts with the required role types (ASSET, ASSET, INCOME, EXPENSE).

The trigger validates mapping creation/update. An account can be closed later, so settlement must re-check all four mapped accounts immediately before posting. The new resolve_portfolio_ledger_mapping_in_session operation performs this check in a caller-owned PostgreSQL transaction: it locks the active portfolio, exact mapping, then all four accounts in deterministic UUID order, and validates owner, currency, account type, and OPEN status. The caller retains transaction ownership.

The exact currency-definition ID is intentional: it preserves the registry snapshot used by an execution. A new currency registry definition does not silently inherit an old mapping; a matching mapping must be explicitly established for that snapshot.

## Explicitly not implemented

This change does not add mapping CRUD endpoints, choose default ledger accounts, create accounts automatically, backfill mappings, write journals, check cash sufficiency, or settle trades. No existing account is modified and no balance is seeded. The settlement coordinator remains blocked on shared lot/money quantization and cross-domain PostgreSQL tests.

## Validation plan

- Model tests verify the mapping key, owner/currency composite foreign keys, and distinct-account invariant.
- PostgreSQL integration tests verify a valid mapping, duplicate-scope rejection, wrong account-role rejection, and cross-owner rejection.
- CI applies migration 0006 on PostgreSQL 16 and validates the mapping trigger/constraints. The final draft PR head passed 46 PostgreSQL integration tests and 154 backend tests (46 PostgreSQL-only cases skipped in SQLite mode).