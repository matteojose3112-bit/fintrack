## 0.4.1 — Test corrections

- Corrected the cash-flow expectation to reflect income minus expenses.
- Verified recurring duplicate prevention against the advanced rule state returned after materialization.

# Changelog

## 0.4.0 — Financial domain foundation
- Added validated account, category, income/expense transaction and recurring-rule models.
- Added paired transfer entries and transfer integrity validation to avoid counting internal movement as income or spending.
- Added daily, weekly, biweekly, monthly and yearly recurrence scheduling with month-end clamping.
- Added account balance and date-/currency-filtered cash-flow reporting primitives.
- Added automated domain tests for validation, transfers, balances, recurrence and reporting.
- Hardened browser storage defaults for restricted storage environments.

## 0.3.0 — Persistent demo workspace and money primitives
- Added exact-precision money utilities using integer minor units, avoiding floating-point arithmetic drift.
- Added supported-currency handling for USD, COP, CAD, EUR and GBP with strict decimal precision validation.
- Added versioned browser-local persistence for transactions, budgets, savings goals, holdings and accounts.
- Added safe recovery for unavailable storage, malformed saved data and unknown schema versions.
- Added automated storage tests.

## 0.2.0 — FinTrack public dashboard
- Replaced the temporary CSV Studio entry screen with the FinTrack personal-finance dashboard.
- Added overview, transactions, budgets, savings goals, investments and accounts screens.
- Added responsive navigation and Aster-aligned dark styling.
- Added demo interactions for transaction creation, budgets and savings contributions.
- Added USD/COP display toggle and sample-data disclosures.
