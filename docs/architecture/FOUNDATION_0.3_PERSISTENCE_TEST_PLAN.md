# Foundation 0.3 — Persistence Verification Plan

This plan is a gate for the first implementation. Tests must use a disposable PostgreSQL instance and never production financial data.

## Unit tests (fast)
- Minor-unit parsing/formatting for exponent 0, 2, and 3.
- Reject floats, booleans, fractional minor units, negative/zero posting magnitudes, and values above 38 digits.
- Currency registry version lookup and immutable historical snapshots.
- Canonical request serialization and stable SHA-256 fingerprinting.
- Same idempotency key + same canonical payload is replay; changed payload is conflict.
- API schema rejects JSON number money fields.

## PostgreSQL integration tests
- Balanced journal commits; unbalanced journal fails at commit.
- Header, postings, and idempotency result commit or roll back as one unit.
- Same-key same-payload and same-key different-payload concurrent races.
- Competing reversal race.
- Account close versus concurrent posting.
- Owner isolation for all reads and writes.
- Append-only permissions / triggers reject update and delete.
- Open/closed period behavior and effective_date vs recorded_at.
- Maximum accepted amount and aggregate balance boundaries.

## Failure injection
Inject exceptions after idempotency claim, journal header insert, first posting insert, deferred validation, and before commit. Confirm no partial journal, orphan posting, or committed idempotency result remains after rollback.

Simulate a client timeout after database commit. Retrying the exact same request with the same key must return the original committed journal, not create another one.

## Acceptance criteria
- All unit and PostgreSQL integration tests pass.
- Concurrency tests use independent PostgreSQL connections.
- No test relies on SQLite for row-lock or transaction-isolation guarantees.
- Runtime DB role cannot update/delete posted financial history.
- Every API monetary field uses exact string representation.
- No production database, deployment, brokerage, or external money movement is involved.
