# Foundation 0.6 — Trade Settlement Accounting Specification

**Status:** Proposed accounting contract; design-only. This document is the gate before implementing a settlement coordinator.

## 1. Purpose and boundary

Aurelius already persists an executed fill and its lot effects through `apply_portfolio_execution_in_session(...)`, and can persist a journal through `post_journal_in_session(...)`. The next layer must compose those two operations in one caller-owned PostgreSQL transaction.

This workflow records an execution that has already happened (manual entry or broker import). It is not an order, instruction, broker connection, cash transfer, or trade execution facility. No public trade API is authorized by this specification.

V1 scope is deliberately narrow: long-only, spot-style BUY and SELL fills, one quote currency per fill, one brokerage cash account, no FX conversion, no leverage, no short sales, and no tax-lot legal opinion.

## 2. Accounting vocabulary and required account mapping

The existing `TradeExecution.account_id` references an owner-scoped `FinancialAccountModel` of type `ASSET`. It identifies the brokerage/custody account associated with the fill; it must not silently be treated as both cash and the investment holding asset.

Before settlement can post journals, Aurelius needs an explicit owner-scoped mapping for each portfolio + brokerage cash account + currency:

- **Brokerage cash account:** existing open `ASSET` financial account; currency must equal the fill quote currency.
- **Portfolio investment control account:** a distinct open `ASSET` financial account in the same currency. This is the ledger control balance for the investment subledger represented by immutable lots.
- **Realized gain account:** open `INCOME` account in the same currency.
- **Realized loss account:** open `EXPENSE` account in the same currency.

The mapping must be unique for its portfolio/cash-account/currency scope, owner-scoped by database constraints, and validated before any writes. It must never infer accounts by display name or choose an arbitrary account. A dedicated mapping model/table is a prerequisite; it does not exist in the current schema.

A portfolio may have more than one brokerage cash account and currency. Each settlement is single-currency. Cross-currency settlement is rejected until a separate, explicit FX workflow exists.

## 3. Proposed v1 journal policy

Amounts below are in the fill's quote currency and are rounded to that currency's published minor-unit exponent under one documented policy. The rounding gate in section 7 must be resolved before code is enabled.

Let:

- (G = quantity \times unit\_price), rounded gross trade consideration.
- (F = fee), rounded execution fee.
- (B) = cost basis removed by the sale, derived from the selected lot allocations.
- (N = G - F), net sale proceeds.

### BUY

The current lot domain capitalizes the acquisition fee into the new lot's original cost. The ledger must agree:

| Account | Debit | Credit |
|---|---:|---:|
| Portfolio investment control (ASSET) | (G + F) | — |
| Brokerage cash (ASSET) | — | (G + F) |

No separate purchase-fee expense is posted in v1; doing so while also capitalizing the fee in lot basis would double count the cost.

A BUY with zero total consideration cannot create a positive-value journal under the current posting contract. The coordinator should reject it pending an explicit zero-cost asset policy.

### SELL

The lot domain allocates sale fees across disposal allocations and computes realized result as net proceeds less allocated cost basis. The journal must use the same aggregate:

| Account | Debit | Credit |
|---|---:|---:|
| Brokerage cash (ASSET) | (N) | — |
| Portfolio investment control (ASSET) | — | (B) |
| Realized gain (INCOME), when (N > B) | — | (N-B) |
| Realized loss (EXPENSE), when (B > N) | (B-N) | — |

Zero-value lines are omitted. The remaining positive lines must balance exactly. A fee reduces net proceeds and therefore realized gain/increases realized loss; it is not also posted as a second expense. A fill where (F > G) is rejected because it implies negative cash proceeds and the current model has no payable/receivable settlement leg.

The investment control account is credited at allocated historical cost basis, not current market value. Unrealized gains/losses and fair-value marks are outside this workflow.

## 4. Fees, taxes, settlement dates, partial fills

- **Fees:** one non-negative fee is currently present on each execution. BUY fees are capitalized into lot basis; SELL fees reduce net proceeds and realized result. Rebate/negative-fee semantics are not supported.
- **Taxes and withholding:** not represented on `TradeExecution`. Do not infer tax amounts or jurisdiction. Withholding, transaction taxes, VAT, and tax reporting require explicit typed inputs and a separate policy; no tax journal is fabricated in v1.
- **Settlement date:** the current execution model stores timezone-aware `executed_at` but no contractual or actual settlement date. V1 journal effective date is the local calendar date of `executed_at` (trade date), not an invented cash settlement date. This is a trade-date accounting assumption and must be visible in records. A later settlement-date model may introduce unsettled trade receivables/payables and a second settlement event.
- **Partial fills:** each fill is an independent immutable execution with its own stable execution UUID and idempotency identity. A parent order/aggregation model is not required for posting fills and is not created here. Two fills must never be collapsed by matching instrument, price, or timestamp.
- **Out-of-order fills:** preserve the existing fail-closed backdated-fill rule. A rebuild/correction workflow is required before late fills can be accepted.

## 5. Transaction, idempotency, and concurrency contract

The future coordinator must:

1. Require an active caller-owned PostgreSQL `Session`; it never opens, commits, rolls back, closes, or retries that session.
2. Validate owner, portfolio, brokerage cash account, instrument, quote currency, account mapping, and all mapped account types/statuses before committing anything.
3. Invoke the portfolio execution primitive and ledger posting primitive inside the same outer transaction.
4. Use a deterministic journal idempotency key derived from the immutable execution UUID and a versioned operation namespace. The portfolio execution UUID and journal idempotency identity must represent the same fill.
5. On same-ID/same-payload replay, return the prior settlement result without duplicating either lots or journal. Changed-payload reuse must fail closed.
6. Ensure a failure after either sub-operation causes the outer transaction to roll back both the portfolio facts and ledger journal, postings, audit, and idempotency record.
7. Acquire/lock accounts in deterministic UUID order and retain the portfolio service's execution/position locks. Define and test one lock order to avoid deadlocks.
8. Keep a single effective date and currency definition snapshot across the journal and settlement result.

The transaction-owning public/internal wrapper, if added later, must own one `session.begin()` boundary around the coordinator. It must not call the transaction-owning wrappers of either underlying service.

## 6. Cash sufficiency and negative balances

The current journal posting service validates account ownership, currency, status, and period but does not itself enforce a non-negative cash balance. V1 settlement must not claim to prevent overdrafts unless it implements that invariant.

Recommended v1 policy: reject a BUY if the brokerage cash account's available ledger balance is less than (G+F), after locking the cash account and calculating the balance in the same transaction. This requires confirming the account's normal-side balance calculation and serialization behavior under concurrent postings. SELL credits cash by (N). No margin, credit facility, short position, or negative-cash exception is implied.

If a brokerage feed reports a fill that would make cash negative, do not silently discard the fill or falsify the ledger. Record it only through a separately designed exception/unsettled-payable workflow; until that exists, fail closed and surface a reconciliation exception.

## 7. Money precision and rounding — blocking design gate

Portfolio quantities and unit prices use exact unscaled Decimal values, while ledger postings use integer minor units. These representations cannot be joined safely by ad hoc `int()`, float conversion, or independent rounding of each disposal row.

Before implementation, add one shared conversion policy that:

- Reads the immutable currency exponent from the execution's currency-definition snapshot.
- Rejects non-finite values and binary floats.
- Defines the gross consideration rounding point, fee rounding, and net proceeds calculation.
- Uses one explicit rounding mode (proposed: `ROUND_HALF_UP`) and converts only final currency amounts to integer minor units.
- Ensures the portfolio lot basis, sale allocation basis/proceeds, and journal postings reconcile to the same rounded totals.
- Allocates any unavoidable minor-unit residual deterministically (proposed: final disposal allocation ordered by stable lot UUID) and tests that allocations sum exactly to the journal totals.
- Rejects values outside the ledger's 38-digit minor-unit bound.

The current in-memory lot domain does not yet enforce this shared currency-scale quantization. The coordinator must not be implemented by merely rounding journal lines while leaving lot history economically inconsistent.

## 8. Worked examples (two-decimal currency)

**BUY:** 10 units × 12.34, fee 1.00.

- Gross = 123.40; cash outflow = 124.40.
- New lot cost basis = 124.40.
- Debit investment control 12,440 minor units; credit cash 12,440 minor units.

**SELL:** sell 4 units × 15.00, fee 0.60; allocated lot basis = 49.76.

- Gross = 60.00; net proceeds = 59.40.
- Realized gain = 59.40 − 49.76 = 9.64.
- Debit cash 5,940; credit investment control 4,976; credit realized gain 964.

**SELL at a loss:** net proceeds 45.00; allocated basis 49.76.

- Debit cash 4,500; debit realized loss 476; credit investment control 4,976.

These examples illustrate mechanics only; they are not tax treatment or investment advice.

## 9. Required tests before any API exposure

- BUY posts correct capitalized fee and cash outflow.
- SELL with gain and SELL with loss post the correct control-account basis and net proceeds.
- Multi-lot sale allocation and rounding residual reconcile exactly.
- Same execution replay creates one portfolio execution and one journal.
- Same execution ID with changed payload is rejected.
- Missing, closed, wrong-owner, wrong-type, or wrong-currency mapping fails before writes.
- Insufficient cash and concurrent BUY attempts cannot overspend the same cash account.
- Fee greater than gross proceeds, zero-value fills, unsupported currencies, and 38-digit overflow fail closed.
- Failure injection after portfolio writes, after journal writes, and before outer commit rolls back every related row.
- Concurrent duplicate execution and concurrent fills preserve deterministic idempotency and position/cash serialization.
- SELL oversell rejection leaves no journal or cash movement.
- Backdated/out-of-order fills remain rejected until a tested rebuild/correction path exists.
- No public route or broker integration is added as part of the coordinator foundation.

## 10. Explicit exclusions

No FX conversion, tax calculation/withholding, unsettled cash receivable/payable, corporate actions, dividends, interest, short sales, margin, options/futures settlement, broker order placement, live brokerage connection, automated cash movement, or user-facing trade endpoint is included.

**Implementation gate:** first add the account mapping and shared money/lot rounding contract; then implement the coordinator and PostgreSQL cross-domain tests. Only after those pass should read-only portfolio APIs be considered.
