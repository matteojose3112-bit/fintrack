# Aurelius Foundation — Implementation Status

Last updated: 2026-11-17

## Foundation 0.1 — completed domain baseline

- Added an isolated `Money` value object using Python `Decimal`.
- Added explicit initial currency exponent metadata for BHD, CAD, COP, EUR, GBP, JPY, KWD, and USD.
- Added fixed-scale decimal-string serialization, exact construction from integer minor units, integer minor-unit conversion, and canonical zero serialization.
- Added same-currency addition/subtraction and rejection of implicit FX arithmetic.
- Added tests for rounding, currency scales, decimal/minor-unit round trips, canonical zero, float rejection, non-finite values, unknown currencies, and cross-currency operations.
- Documented the money contract and architecture decision record.

## Foundation 0.2 — Accounts & Ledger implementation

- No database models or Alembic migrations have changed.
- Existing FinTrack API monetary fields still use numeric JSON and float-backed model columns on main.
- The new domain primitive is not wired into existing endpoints.
- No frontend monetary arithmetic has been migrated.
- No accounts, double-entry ledger, reconciliation, liabilities, FX conversion, investment holdings, market data, or AI features have been implemented.
- GitHub Actions run [#125](https://github.com/matteojose3112-bit/aurelius/actions/runs/44184005586) passed the backend and frontend jobs on this branch.

### Completed in Foundation 0.2 branch\n\n- Added immutable FinancialAccount values with owner scope, type, currency, status, and normal-side rules.\n- Added immutable LedgerPosting and JournalEntry values with positive amounts, unique account lines, single-currency journals, and exact debit/credit balance enforcement.\n- Added append-only LedgerBook posting, owner/account/currency/status validation, derived balances, same-currency asset transfers, and one-time exact reversals.\n- Added accounting golden-case tests for income, expenses, opening balances, transfers, reversals, and rejection paths.\n- Added docs/finance/ACCOUNT_LEDGER_CONTRACT.md.\n\n### Not yet complete\n\n- Foundation 0.2 GitHub Actions run [#136](https://github.com/matteojose3112-bit/aurelius/actions/runs/44185872151) passed backend and frontend jobs.\n- No persistence, database constraints, API schemas, account CRUD, reconciliation, imports, FX conversion, or production audit storage exists.\n- Concurrency control, idempotency, backdated-entry policy, account closure use cases, and durable append-only enforcement must be designed before persistence.\n\n## Acceptance checks

- [x] Backend unit tests pass in GitHub Actions (run #125).
- [x] Existing backend and frontend test suites remain green in CI (run #125; frontend tests and production build).
- [x] Static review confirms new account and ledger modules import only domain modules and Python standard-library types.\n- [x] Foundation 0.2 GitHub Actions run passes all backend and frontend jobs (run #136).
- [ ] Follow-up API/database migration design is reviewed before implementation.
- [ ] No production migration or deployment occurs without explicit approval.
