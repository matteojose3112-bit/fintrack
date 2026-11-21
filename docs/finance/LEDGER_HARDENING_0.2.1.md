# Foundation 0.2.1 — Ledger Hardening Contract

**Status:** Design baseline, 2026-11-17  
**Scope:** Posting semantics, duplicate-request behavior, concurrency, account lifecycle, effective dating, reconciliation, and legacy precision compatibility. This document is a design gate; it does not add persistence, API endpoints, migrations, or production behavior.

## 1. Idempotency and duplicate requests

### Command identity
- Every write command carries a client-generated idempotency key with at least 128 bits of randomness (UUIDv4 or equivalent).
- Durable uniqueness scope: (owner_id, operation, idempotency_key). Keys are not global across owners or command types.
- Store a canonical request hash alongside the key and resulting journal-entry ID / response.
- Canonicalization includes owner, operation, effective date, normalized description, ordered account IDs, debit/credit sides, currency codes, and integer minor-unit amounts. Exclude transport-only fields and request arrival time.
- Repeating the same key with the same canonical payload returns the original result and does not append another journal.
- Reusing the same key with a different payload returns a conflict; it never silently overwrites or creates a second entry.
- A distinct key with a duplicate explicit journal-entry ID is rejected by the journal ID uniqueness constraint.
- Retain idempotency records at least as long as journal history; permanent retention is preferred because retries may arrive late.

### Retry contract
A timeout after commit is an unknown client outcome, not proof of failure. The client retries with the same key. The server resolves the idempotency record and returns the committed result if the original transaction succeeded.

## 2. Atomicity and concurrency

The database adapter must implement one atomic unit of work:
1. Begin a database transaction.
2. Claim or lock the owner-scoped idempotency key.
3. Lock all affected account rows in deterministic ascending account-ID order to avoid lock-order deadlocks.
4. Re-check owner, status, currency, period policy, and reversal eligibility inside the transaction.
5. Insert the journal header and all postings.
6. Validate exact debit/credit equality per currency before commit.
7. Insert the idempotency result and commit.

Any failure rolls back the journal header, all postings, and idempotency claim together. No partially posted journal may be observable.

Required database protections:
- Unique journal-entry ID.
- Unique (owner_id, operation, idempotency_key).
- Unique reversal source (reversal_of) so two concurrent reversals cannot both commit.
- Foreign keys from postings to journal entries and accounts.
- Owner-scoped authorization in every query; never trust a client-supplied owner ID.
- Append-only database permissions / triggers for posted journal and posting rows. Corrections are new events.
- Balanced-entry enforcement through a deferred constraint trigger or a posting procedure that is the only permitted write path. A row-level CHECK cannot compare sums across posting rows.
- Account locks or an equivalent serializable / optimistic concurrency protocol for operations that depend on account state.

The current in-memory LedgerBook is a deterministic reference aggregate only. It is not thread-safe, durable, or cross-process safe; no in-memory lock or dictionary can substitute for database guarantees.

## 3. Account lifecycle and closure

- Account identity, owner, type, and currency remain immutable. Rename and display metadata changes are separate audited account events.
- Closing is a lifecycle transition, not deletion. Historical postings and balances remain queryable.
- A closed account rejects new ordinary postings and transfers.
- Asset and liability accounts may close only after their balance is zero in the account's currency, or after an explicit balanced settlement journal moves the remaining balance to an appropriate destination.
- Income and expense accounts are closed through an explicit period-close journal to retained earnings / equity, not by erasing or mutating historical activity.
- Reopening is a separate audited command with actor, reason, timestamp, and prior/new status. It must not rewrite historical entries.
- First persistence release should implement close / freeze semantics only; reopen and period-close workflows remain separately gated.

## 4. Effective dates and backdated entries

Each journal must distinguish:
- effective_date: the accounting date to which the event belongs.
- recorded_at: immutable server-generated UTC timestamp for when Aurelius accepted it.

Policy:
- Backdated entries are permitted only in an open accounting period and retain their true recorded_at timestamp.
- A closed period rejects backdated postings by default.
- Any exceptional closed-period adjustment requires an explicit privileged command, reason, actor, and audit event; it must not silently reopen the period.
- Future-dated ordinary postings are rejected. Scheduled transactions are a separate pending instruction and are not ledger entries until executed / confirmed.
- Period boundaries and timezone rules must be explicit in the owning entity's accounting settings; do not infer them from browser locale.

## 5. Reconciliation and corrections

- Reconciliation compares imported statement lines against posted ledger activity using stable source identifiers, account, currency, amount, and transaction date.
- Deduplicate imported statement lines by (owner_id, account_id, source, external_transaction_id) where the provider supplies a stable ID. Fallback matching is a review candidate, never an automatic identity guarantee.
- Match status and reconciliation sessions are separate audit records; matching does not mutate journal entries.
- Unmatched statement activity is proposed as a new journal entry and requires validation before posting.
- A reconciliation difference is surfaced explicitly. It is not silently plugged into income or expense.
- Corrections to posted entries use a full reversal plus a new corrected journal. Partial correction is represented by a separately described adjustment journal linked to the original, not by editing postings.
- A reversal preserves original amounts, currencies, account references, and exact opposite sides. One source entry can have at most one full reversal.

Golden scenarios required before persistence:
1. Exact statement match and repeated import of the same external ID.
2. Duplicate import with changed payload under the same provider ID: conflict / review, not overwrite.
3. Missing ledger transaction proposed and posted once.
4. Unmatched ledger transaction remains visible.
5. Statement amount / date mismatch remains unresolved until reviewed.
6. Reversal and corrected replacement preserve original and correction history.
7. Reconciliation difference cannot be hidden by an automatic balancing plug.

## 6. Legacy fixed-precision PR compatibility

The existing legacy work is not the canonical Aurelius ledger contract:
- PR #10 proposes SQLAlchemy Numeric(14, 2) for legacy transactions, budgets, and goals, with a two-decimal conversion migration.
- PR #12 is a draft integration vehicle containing PR #10 plus legacy authentication, account-isolation, CSV, frontend, and CI hardening.
- Foundation 0.1 supports currency exponents of 0, 2, and 3 decimal places (for example JPY, USD / CAD / COP, and KWD / BHD). A universal scale of 2 is insufficient for the canonical multi-currency ledger.
- Do not merge PR #10 or #12 as the ledger monetary persistence design. Their two-decimal contract may remain appropriate for existing legacy MVP fields, but it must be isolated from the new ledger.
- Before integration, choose one canonical storage strategy: integer minor units plus a versioned currency-exponent registry; or fixed-precision NUMERIC columns with currency-specific scale and a rigorously bounded precision policy.
- API requests and responses must transmit monetary amounts as decimal strings plus currency (or integer minor units plus currency); JSON floating-point values are prohibited for canonical financial writes and balances.
- Legacy migration must preserve original values, document rounding, reconcile per-owner totals, and retain a reversible backup / restore path. Never silently reinterpret old two-decimal values as a different currency scale.

## 7. Persistence and API design gates

Before implementation:
- Approve the idempotency and lock protocol against the selected PostgreSQL version.
- Decide the accounting-period owner and period-close permissions.
- Define canonical UUID / ID strategy and recorded_at timestamp source.
- Define database-enforced balanced posting and append-only privileges.
- Define API request / response schemas, conflict semantics, and retry behavior.
- Add disposable PostgreSQL concurrency tests: same-key same-payload race, same-key different-payload race, two competing reversals, concurrent account closure / posting, rollback after partial insert, and owner isolation.
- Keep frontend calculations in integer minor units or a decimal library; never use JavaScript Number for authoritative money arithmetic.
- Obtain explicit approval before any production migration, deployment, brokerage integration, or external financial action.

## 8. Explicit non-goals

This design does not implement production persistence, reconciliation import adapters, account closure commands, accounting periods, tax treatment, FX conversion, fees, portfolio positions, broker connectivity, order execution, or autonomous money movement.
