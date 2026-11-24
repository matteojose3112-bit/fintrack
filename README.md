# FinTrack

**Personal finance, made clearer.**

A responsive personal finance dashboard concept for cash flow, transactions, budgets, savings goals, accounts and investment holdings.

## Demo

The public-facing dashboard uses illustrative sample data. No bank, brokerage or payment account is connected.

## Features
- Financial overview with balance, income, expenses and savings-rate cards.
- Cash-flow and spending visualizations.
- Searchable transaction list and add-transaction interaction.
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
This frontend currently runs in demo mode with browser-memory sample data. It does not claim live bank balances, live market prices, authenticated account storage, brokerage connectivity or trade execution. API integration is a subsequent milestone.

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
