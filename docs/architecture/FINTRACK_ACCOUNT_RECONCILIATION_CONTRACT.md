# FinTrack — Account Reconciliation Contract

Status: design contract for the next financial-core milestone  
Scope: statement ingestion, deterministic matching, and reviewed corrections  
Safety: reconciliation is read-only until a user explicitly approves a correction.

## 1. Purpose

Reconciliation compares independently imported external account activity with FinTrack's immutable posted ledger history. It must explain differences without silently changing balances, rewriting journals, or treating an imported statement as authoritative proof that an internal transaction is correct.

The first implementation targets cash and bank accounts. Brokerage holdings, securities positions, tax lots, and FX translation are separate reconciliation domains.

## 2. Core invariants

1. **Owner isolation:** every import batch, source row, match, and discrepancy is scoped to one owner and one exact financial account.
2. **Currency identity:** a statement batch is bound to one immutable currency-definition snapshot. A row with a different currency is rejected or routed to a separately declared account; it is never converted implicitly.
3. **Exact amounts:** parse canonical decimal strings into integer minor units using the account's immutable currency exponent. Reject floats, non-finite values, excess precision, and values outside the ledger's 38-digit bound.
4. **Immutable evidence:** retain the original file digest, parser/version metadata, import timestamp, source row number, normalized source identity, and canonical row payload. Corrections create new records; imported evidence is never overwritten.
5. **Idempotent imports:** the same owner/account/file digest/parser version must replay the existing batch. A changed file or parser version creates a distinct batch, with duplicate detection across batches.
6. **No inferred posting:** importing or matching a statement row never creates, edits, reverses, or deletes a journal.
7. **Explainable matching:** every proposed match records its rule/version, candidate journal/posting IDs, amount/date/reference evidence, and confidence class. Ambiguous candidates remain unmatched.
8. **Concurrency safety:** batch finalization and match assignment use PostgreSQL transactions and deterministic row-lock order. A ledger posting created concurrently must not be double-matched.
9. **Auditability:** every user-confirmed match, unmatch, exclusion, and correction request records actor, timestamp, reason, and before/after state.
10. **Read-only by default:** any correction is a separate explicit workflow using existing journal reversal/posting rules and the same owner/currency/account guards.

## 3. Proposed persistence model

### ReconciliationImportBatch
- id, owner_id, financial_account_id
- currency_definition_id, statement_period_start, statement_period_end
- original_filename (display metadata only), file_sha256, parser_name, parser_version
- imported_at, imported_by, status (RECEIVED, VALIDATED, REVIEW, RECONCILED, REJECTED)
- source_opening_minor, source_closing_minor (nullable until supplied/validated)
- row_count, rejected_row_count

### ReconciliationStatementRow
- id, owner_id, batch_id, source_row_number
- source_transaction_id (nullable), booking_date, value_date (nullable)
- signed_amount_minor, currency_definition_id
- normalized_description, normalized_counterparty (nullable)
- source_reference (nullable), canonical_payload_sha256
- status (UNMATCHED, PROPOSED, MATCHED, EXCLUDED, DISPUTED)
- immutable source payload; no journal foreign key is required for unmatched evidence

### ReconciliationMatch
- id, owner_id, statement_row_id, journal_entry_id, journal_posting_id
- match_rule_version, match_type (EXACT_REFERENCE, EXACT_AMOUNT_DATE, MANUAL)
- evidence JSON, proposed_at, confirmed_at, confirmed_by
- state (PROPOSED, CONFIRMED, REVOKED)
- uniqueness prevents one statement row or one account posting from being confirmed twice

### ReconciliationAdjustmentRequest
- id, owner_id, account_id, statement_row_id (nullable), source_journal_id (nullable)
- request_type (MISSING_LEDGER_ENTRY, DUPLICATE_LEDGER_ENTRY, AMOUNT_MISMATCH, DATE_MISMATCH, OTHER)
- proposed_action, reason, status (OPEN, APPROVED, REJECTED, APPLIED)
- created_by/at, reviewed_by/at, applied_journal_id (nullable)
- approval and application are separate transitions; no direct row mutation

## 4. Deterministic matching policy

Matching runs in ordered passes; each pass may only propose a candidate:

1. Exact stable bank/source transaction reference + exact account + currency + amount.
2. Exact amount + exact booking date + normalized counterparty/reference evidence.
3. Exact amount within a configurable date window, only when there is exactly one candidate and no conflicting reference.
4. Manual selection by an authorized owner.

Never auto-confirm fuzzy text-only matches, split/aggregate matches, FX conversions, or multiple-candidate matches. Those require a separate explicitly designed allocation workflow.

The matching engine must not use an LLM to choose or confirm a financial match. AI may summarize a discrepancy after deterministic candidates and evidence have been assembled.

## 5. Balance and discrepancy calculations

For each account and statement period, calculate using integer minor units:

- Opening balance from the statement, if provided.
- Ledger opening balance immediately before the period.
- Statement movement: sum of imported signed rows.
- Ledger movement: sum of posted account-side journal postings in the period.
- Expected closing = opening + movement, subject to the account's normal-side convention.
- Statement closing versus computed closing difference.
- Unmatched statement rows, unmatched ledger postings, duplicate candidates, and unresolved adjustment requests.

Use the account's configured accounting timezone and a documented booking-date policy. Never mix booking date and value date implicitly. Period boundaries are half-open [start, end) in the account timezone, converted to aware UTC instants for querying.

## 6. CSV import boundary

The first adapter accepts a documented FinTrack canonical CSV schema, not arbitrary bank formats. Required columns: booking_date, amount, currency, description. Optional: source_transaction_id, value_date, counterparty, reference.

- Parse dates strictly and reject ambiguous locale formats.
- Parse amounts from strings only; never use binary floating point.
- Validate the entire file before marking a batch VALIDATED.
- Enforce file-size, row-count, column-count, and text-length limits.
- Treat all imported text as untrusted data; neutralize formula-leading characters on any later CSV export.
- Preserve source line numbers and row-level rejection reasons.
- No external bank connector, credential collection, scraping, or automatic sync in this milestone.

## 7. API and UI sequence

1. Upload canonical CSV to create a RECEIVED batch.
2. Validate and persist immutable rows atomically; return row-level errors.
3. Show summary totals and unmatched items without changing ledger balances.
4. Generate proposed matches with deterministic rules.
5. Owner confirms or rejects each proposed match.
6. Show reconciliation status and unresolved discrepancies.
7. Create an adjustment request; a separate approval action is required before an existing journal reversal/new journal can be applied.

The first UI should clearly label imported rows as external evidence and ledger postings as FinTrack records.

## 8. Required PostgreSQL test gates

- Cross-owner batch/account/row/match rejection at database and service layers.
- Currency snapshot mismatch and excess decimal precision rejection.
- Same-file replay and changed-file distinct batch behavior.
- Duplicate source IDs within and across batches.
- Formula-like CSV cells safely retained as text and safely exported.
- Exact reference matching; ambiguous exact-amount candidates remain unconfirmed.
- No double assignment of a statement row or ledger posting under concurrent match attempts.
- Concurrent ledger posting does not produce a double match.
- Outer transaction rollback removes batch, rows, and match proposals together.
- Confirm/unconfirm audit events are append-only.
- Import, match, and discrepancy flows never alter journal balances.
- Timezone and half-open period boundary golden cases.

## 9. Explicit exclusions

No bank credentials, open-banking integration, broker statement import, securities-position reconciliation, automatic journal generation, FX conversion, AI matching, tax reporting, production migration, or deployment.

## 10. Delivery order

1. Domain contracts and canonical CSV parser with pure tests.
2. Owner-scoped PostgreSQL models and migration.
3. Immutable import persistence and idempotency.
4. Deterministic match proposal engine.
5. Confirm/revoke workflow with audit trail and concurrency tests.
6. Read-only reconciliation summary API and UI.
7. Separately reviewed adjustment-request workflow.

The acceptance criterion is that FinTrack can explain and evidence every reconciliation difference while leaving posted accounting facts unchanged until an authorized, separately audited correction is approved.
