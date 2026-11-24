# FinTrack

**Personal finance, made clearer.**

A responsive personal finance dashboard concept for cash flow, transactions, budgets, savings goals, accounts and investment holdings.

## Demo

The public-facing dashboard uses illustrative sample data. No bank, brokerage or payment account is connected.

## Features
- Financial overview with balance, income, expenses and savings-rate cards.
- Cash-flow and spending visualizations.
- Searchable transaction list, add-transaction interaction, CSV import and export.
- Import column mapping, row validation preview, exact duplicate detection and explicit confirmation before adding transactions.
- Conservative reconciliation flags possible matches with the same date, amount, type and currency plus similar normalized descriptions. Each candidate is held for review; users can import it as a separate record or skip it. Existing records are never overwritten or merged.
- Local import activity log records imported rows, explicit possible-match decisions, exact duplicates and invalid rows with timestamps and source filenames.
- Spreadsheet-safe CSV serialization with quoted-field escaping.
- Budget categories and spending progress.
- Savings goals and contributions.
- Multi-account and investment holdings views.
- USD/COP display toggle for the demo workspace.
- Versioned browser-local persistence for demo workspace collections.
- Responsive desktop and mobile navigation.

## Run locally
```bash
npm install
npm run dev
npm test
npm run build
```

## Product boundaries
This frontend currently runs in demo mode with illustrative sample data persisted locally in the browser. It does not claim live bank balances, live market prices, authenticated account storage, brokerage connectivity or trade execution. API integration is a subsequent milestone.

## Financial domain layer
- `src/domain.js` defines validated account, category, income/expense transaction, transfer and recurring-rule records.
- Transfers are represented as paired entries sharing a transfer ID, with validation for matching amount, currency and date.
- Recurring rules support daily, weekly, biweekly, monthly and yearly schedules, including end-of-month date clamping.
- Account balances and cash-flow summaries are computed from integer minor-unit values; internal transfers are excluded from income/expense reporting.
- Domain behavior is covered by `tests/domain.test.js`.

## Financial domain utilities
- `src/money.js` provides exact-precision parsing, formatting, addition and subtraction using integer minor units.
- Supported currencies: USD, COP, CAD, EUR and GBP. COP is treated as zero-decimal; other listed currencies use two decimals.

## Technology
Vanilla JavaScript, HTML5, CSS3, Vite and Vitest.


## Data portability
- CSV imports are processed locally in the browser demo, limited to 5 MB / 5,000 rows, and require ISO dates and explicit income/expense types.
The Transactions screen can export the demo transaction collection as a CSV file. Text cells are escaped and spreadsheet formula prefixes are neutralized. The export contains illustrative workspace data only; it is not a bank statement or a verified financial record.

- CSV imports are processed locally in the browser demo, limited to 5 MB / 5,000 rows, and require ISO dates and explicit income/expense types.
