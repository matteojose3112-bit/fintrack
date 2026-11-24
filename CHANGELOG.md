# Changelog\n\n## 0.4.7 — Internal transfer management\n- Added a Transfers screen with account selection, date, amount and description.\n- Created balanced paired ledger entries with shared transfer IDs and integrity validation.\n- Persisted transfer pairs locally and incorporated them into demo account balances.\n- Kept internal transfers out of income and expense totals.\n- Fixed recurring screen routing and date validation.\n\n# Changelog

## 0.4.5 — Import audit trail
- Added a local activity log for completed CSV reviews, including imported rows, explicit possible-match decisions, duplicates and invalid rows.
- Recorded review timestamps, source filenames, row numbers and outcomes.
- Added a completion action so users can finish a review even when every candidate is skipped.
- Persisted the audit log with the browser demo workspace and documented its local-only, non-tamper-proof boundary.
- Added automated tests for audit entry coverage and validation.

## 0.4.4 — Transaction reconciliation review
- Added conservative possible-match detection using matching date, amount, transaction type and currency plus normalized description similarity.
- Added per-row review decisions; possible matches default to Skip and can be explicitly imported as separate records.
- Kept exact duplicates excluded and protected existing transactions from automatic edits, merges or overwrites.
- Added tests for likely matches, financial-attribute mismatches and exact-duplicate precedence.

## 0.4.1 — Test corrections

- Corrected the cash-flow expectation to reflect income minus expenses.
- Verified recurring duplicate prevention against the advanced rule state returned after materialization.

## 0.4.3 — Reviewed transaction CSV import
- Added local CSV file selection with 5 MB and 5,000-row limits.
- Added automatic column suggestions and editable transaction-field mapping.
- Added row-level validation and duplicate detection against existing records and within the import.
- Added a review preview and explicit confirmation before imported rows are added.
- Added automated mapping, validation and duplicate-detection tests.

## 0.4.2 — Transaction CSV export
- Added CSV export from the Transactions screen for the full demo transaction collection.
- Added escaping for commas, quotes and embedded line breaks.
- Neutralized formula-like text cells to reduce spreadsheet formula-injection risk.
- Added automated serializer tests for escaping, formula protection and invalid input.


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
