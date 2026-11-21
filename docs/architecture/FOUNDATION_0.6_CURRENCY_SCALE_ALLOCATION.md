# Foundation 0.6 — currency-scale integration into portfolio lots

**Status:** Implemented behind an explicit accounting-policy version; CI run #495 passed. Additional historical replay and partial-disposal stress cases remain.

## Versioned compatibility

Trade executions carry an `accounting_precision_version`:

- **Version 1** preserves prior exact-Decimal lot calculations and is assigned to historical rows by migration default. Rebuilds retain that policy.
- **Version 2** is used for new executions. It receives the immutable minor-unit exponent from the currency-definition snapshot attached to the execution.

The version is persisted on the immutable execution row and included in audit metadata. It is not user-selectable.

## Version 2 rules

- Acquisition basis is `quantity × unit_price + fee`, rounded once to the snapshot currency scale using `ROUND_HALF_UP`.
- SELL gross consideration and sale fee are each rounded once to currency scale.
- A sale fee greater than rounded gross proceeds is rejected before lot mutation.
- Rounded gross proceeds and fees are apportioned across consumed lots by quantity weights.
- Total disposed cost basis is rounded once, then apportioned across consumed lots by positive planned basis weights.
- Allocation keys are stable lot UUID strings sorted lexically. Integer minor-unit residuals go to the final stable key.
- Net proceeds and realized gain/loss are derived from allocated minor-unit amounts, so aggregate allocations reconcile exactly to rounded execution totals.

## Compatibility and boundary

Version 1 executions rebuild with legacy exact-Decimal behavior. New version 2 executions use currency-scale amounts. This avoids retroactively changing historical lot facts when the code is upgraded.

No cash journal, settlement coordinator, brokerage cash sufficiency enforcement, trade API, broker connection, or cash movement is included. Before coordinator implementation, add broader PostgreSQL coverage for multi-lot partial-disposal stress cases and explicit historical v1 replay/rebuild stability.
