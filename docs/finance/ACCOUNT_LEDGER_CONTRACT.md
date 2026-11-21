# Aurelius Account and Ledger Contract

**Status:** Foundation 0.2 domain contract — 2026-11-17  
**Scope:** Immutable domain identities and append-only in-memory journal rules. No database schema, API endpoint, migration, or production workflow is changed.

## 1. Account invariants

- Every account has a stable account ID, owner ID, non-empty display name, accounting type, currency, and lifecycle status.
- Account ownership and classification are immutable domain identity. A rename or reclassification, if later supported, must be represented as an audited application command/event rather than silently rewriting historical postings.
- Each account is denominated in exactly one supported currency. Currency codes are normalized and validated by the canonical Money registry; no duplicate currency metadata is maintained.
- Balances are derived from posted ledger entries, never independently mutated or trusted as stored account state.
- Closed accounts cannot receive new postings. Closing an account is not yet implemented as a use case.

## 2. Account classification and normal balance

| Account type | Normal side | Examples |
|---|---|---|
| Asset | Debit | Cash, checking, savings, brokerage cash |
| Expense | Debit | Rent, groceries, fees |
| Liability | Credit | Credit card, loan payable |
| Equity | Credit | Opening balance equity, owner equity |
| Income | Credit | Salary, interest, dividends |

A debit increases debit-normal accounts and decreases credit-normal accounts. A credit does the reverse. balance_for() reports a signed balance relative to the account's normal side; a negative result represents a balance on the abnormal side, not an automatic validation failure.

## 3. Journal and posting invariants

- A journal entry is immutable and contains an ID, owner, effective date, description, and at least two postings.
- Every posting references one account, one side (debit or credit), and one strictly positive Money amount.
- An account may appear at most once in a journal entry; aggregate split lines before posting.
- All postings in a journal entry must use one currency. Total debit minor units must equal total credit minor units exactly.
- Each posting's currency must equal its account currency. Every account must exist, be open, and belong to the journal owner.
- Cross-currency journals are rejected. A future FX workflow must record explicit rate evidence and use separately balanced currency legs / clearing accounts; equal nominal amounts in different currencies are never treated as equal value.

## 4. Transfers

A transfer is a balanced journal between two distinct, same-owner, open asset accounts denominated in the same currency:
- Debit the destination asset account.
- Credit the source asset account.
- Do not create income or expense.
- Fees, FX transfers, liability payments, and transfers between unlike account types require separate explicit use cases and are not silently inferred.

The domain helper validates account ownership, type, and currency. It does not enforce available funds or prevent an asset account from becoming negative; overdraft policy is a separate product rule.

## 5. Corrections and reversals

- Posted journal entries are append-only: no update or delete operation exists.
- Correct a posted entry by appending a new journal with the exact opposite sides and original amounts, linked through reversal_of.
- A source entry may be reversed once; a reversal cannot itself be reversed. If a correction is needed after reversal, post a new corrected journal entry.
- The reversal has its own ID and effective date, preserving both the original event and correction history.
- The in-memory aggregate is a reference implementation, not a durable audit log or concurrency-safe posting engine. Database persistence must enforce unique IDs, owner scoping, balanced posting within one atomic transaction, reversal uniqueness, and append-only access controls.

## 6. Opening balances and accounting examples

Opening balances must be introduced as balanced journals against an explicit opening-balance equity account, not as a direct account balance write.

Examples below use USD:

| Event | Debit | Credit |
|---|---|---|
| Opening cash $1,000 | Cash $1,000 | Opening Balance Equity $1,000 |
| Salary $2,000 | Cash $2,000 | Salary Income $2,000 |
| Groceries $125.50 | Groceries Expense $125.50 | Cash $125.50 |
| Transfer $300 | Savings $300 | Checking $300 |
| Reverse salary | Salary Income $2,000 | Cash $2,000 |

The examples are domain golden cases, not tax/accounting policy for every jurisdiction.

## 7. Implementation and exclusions

Implemented in backend/app/domain/accounts.py and backend/app/domain/ledger.py, with golden-case tests in backend/tests/test_accounts_ledger.py.

Not implemented: persistence, database constraints, API schemas, account CRUD, account closure, reconciliation, imports, recurring entries, fees, liabilities workflows, FX conversion, multi-currency consolidated reporting, or production audit storage.

## 8. Required persistence design gates

Before API/database integration:
1. Resolve the overlapping legacy fixed-precision PRs and decide the final precision/storage contract; do not assume a universal Numeric(14,2) is sufficient.
2. Define idempotency keys, concurrent posting/locking, transaction atomicity, and reversal uniqueness constraints.
3. Define account closure, archived-account behavior, and whether backdated entries are allowed.
4. Define opening-balance migration and legacy transaction mapping with reconciliation totals.
5. Design account-level ownership and authorization for every query/export/job.
6. Specify API decimal-string schemas and frontend exact arithmetic.
7. Add disposable PostgreSQL integration tests for atomic balanced posting, duplicate requests, rollback, and owner isolation.
8. Obtain explicit approval before any production migration or deployment.
